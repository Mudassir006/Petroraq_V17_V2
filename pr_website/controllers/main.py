import logging
import base64
import json
import re
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class CareersController(http.Controller):
    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def homepage(self, **kwargs):
        return request.render('pr_website.petroraq_homepage_custom')

    @http.route('/jobs', type='http', auth='public', website=True, sitemap=True)
    def jobs(self, **kwargs):
        jobs = request.env['hr.job'].sudo().search([('website_published', '=', True)], order='create_date desc')
        return request.render('pr_website.careers_jobs', {'jobs': jobs})

    @http.route('/job/<int:job_id>', type='http', auth='public', website=True, sitemap=True)
    def job_detail(self, job_id, **kwargs):
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or not job.website_published:
            return request.not_found()
        degrees = request.env['hr.recruitment.degree'].sudo().search([], order='name')
        error_message = kwargs.get('error')
        return request.render('pr_website.careers_job_detail', {'job': job, 'degrees': degrees, 'error_message': error_message})

    def _validate_application_payload(self, post):
        validators = [
            ('partner_name', r"^[A-Za-z][A-Za-z\s'\.-]{1,79}$", 'Please enter a valid full name.'),
            ('email_from', r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', 'Please enter a valid email address.'),
            ('partner_phone', r'^\+?[0-9][0-9\s().-]{7,19}$', 'Please enter a valid phone number.'),
            ('partner_location', r"^[A-Za-z0-9][A-Za-z0-9,\s'\.-]{1,99}$", 'Please enter a valid location.'),
            ('linkedin_profile', r'^(https?://)?([a-z]{2,3}\.)?linkedin\.com/.*$', 'Please enter a valid LinkedIn URL.'),
        ]

        for field_name, pattern, message in validators:
            value = (post.get(field_name) or '').strip()
            if not re.fullmatch(pattern, value):
                return message

        numeric_fields = [('experience', 0, 60), ('salary_expected', 1, 100000000), ('notice_period', 0, 3650)]
        for field_name, min_v, max_v in numeric_fields:
            value = (post.get(field_name) or '').strip()
            if not value.isdigit():
                return f'Please enter a valid numeric value for {field_name.replace("_", " ")}.'
            num = int(value)
            if num < min_v or num > max_v:
                return f'{field_name.replace("_", " ").title()} must be between {min_v} and {max_v}.'

        if (post.get('will_relocate') or '') not in {'yes', 'no'}:
            return 'Please select a valid answer for relocation.'
        if (post.get('legally_required') or '') not in {'yes', 'no'}:
            return 'Please select a valid legal authorization option.'

        return None

    @http.route('/job/<int:job_id>/apply', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def job_apply(self, job_id, **post):
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or not job.website_published:
            return request.not_found()

        validation_error = self._validate_application_payload(post)
        if validation_error:
            return request.redirect(f'/job/{job_id}?error={quote_plus(validation_error)}')

        existing = request.env['hr.applicant'].sudo().search_count([
            ('job_id', '=', job.id),
            ('email_from', '=', (post.get('email_from') or '').strip()),
            ('partner_phone', '=', (post.get('partner_phone') or '').strip()),
        ])
        if existing:
            return request.redirect(f'/job/{job_id}?error={quote_plus("Duplicate application detected: you have already applied to this job with the same email and phone number.")}')

        applicant_vals = {
            'name': post.get('name') or post.get('partner_name') or 'Website Candidate',
            'partner_name': (post.get('partner_name') or '').strip(),
            'email_from': (post.get('email_from') or '').strip(),
            'partner_phone': (post.get('partner_phone') or '').strip(),
            'partner_mobile': post.get('partner_mobile'),
            'job_id': job.id,
            'linkedin_profile': (post.get('linkedin_profile') or '').strip(),
            'partner_location': (post.get('partner_location') or '').strip(),
            'will_relocate': post.get('will_relocate'),
            'notice_period': post.get('notice_period'),
            'legally_required': post.get('legally_required'),
            'salary_expected': post.get('salary_expected'),
            'type_id': int(post['type_id']) if post.get('type_id') and post.get('type_id').isdigit() else False,
            'description': (
                f"Experience (years): {post.get('experience') or ''}\n"
                f"Highest Qualification ID: {post.get('type_id') or ''}"
            ),
        }

        applicant = request.env['hr.applicant'].sudo().create(applicant_vals)

        resume = post.get('resume')
        if resume and getattr(resume, 'filename', False):
            content = resume.read()
            request.env['ir.attachment'].sudo().create({
                'name': resume.filename,
                'datas': base64.b64encode(content).decode('ascii'),
                'res_model': 'hr.applicant',
                'res_id': applicant.id,
                'mimetype': resume.content_type,
                'type': 'binary',
            })

        return request.redirect('/jobs/thank-you')

    @http.route('/jobs/thank-you', type='http', auth='public', website=True, sitemap=False)
    def job_thank_you(self, **kwargs):
        return request.render('pr_website.careers_thank_you')

    @http.route('/jobs/location_suggest', type='json', auth='public', website=True, methods=['POST'], csrf=False)
    def location_suggest(self, term=None, **kwargs):
        query = (term or '').strip()
        if len(query) < 2:
            return []

        endpoint = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={quote_plus(query)}&count=8&language=en&format=json"
        )
        req = Request(endpoint, headers={'User-Agent': 'Petroraq-Odoo/1.0 (careers autocomplete)'})
        try:
            with urlopen(req, timeout=4) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            _logger.warning('Location suggestion lookup failed: %s', exc)
            return []

        suggestions = []
        for item in payload.get('results', []):
            name = item.get('name')
            admin = item.get('admin1')
            country = item.get('country')
            parts = [part for part in [name, admin, country] if part]
            if parts:
                suggestions.append(', '.join(parts))
        return suggestions