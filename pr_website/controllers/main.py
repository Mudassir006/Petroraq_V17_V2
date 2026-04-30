import logging
import base64
import json
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
        return request.render('pr_website.careers_job_detail', {'job': job, 'degrees': degrees})

    @http.route('/job/<int:job_id>/apply', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def job_apply(self, job_id, **post):
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or not job.website_published:
            return request.not_found()

        applicant_vals = {
            'name': post.get('name') or post.get('partner_name') or 'Website Candidate',
            'partner_name': post.get('partner_name'),
            'email_from': post.get('email_from'),
            'partner_phone': post.get('partner_phone'),
            'partner_mobile': post.get('partner_mobile'),
            'job_id': job.id,
            'linkedin_profile': post.get('linkedin_profile'),
            'partner_location': post.get('partner_location'),
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
