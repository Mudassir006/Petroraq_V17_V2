import base64

from odoo import http
from odoo.http import request


class CareersController(http.Controller):
    @http.route('/jobs', type='http', auth='public', website=True, sitemap=True)
    def jobs(self, **kwargs):
        jobs = request.env['hr.job'].sudo().search([('website_published', '=', True)], order='create_date desc')
        return request.render('pr_website.careers_jobs', {'jobs': jobs})

    @http.route('/job/<int:job_id>', type='http', auth='public', website=True, sitemap=True)
    def job_detail(self, job_id, **kwargs):
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or not job.website_published:
            return request.not_found()
        return request.render('pr_website.careers_job_detail', {'job': job})

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
            'description': (
                f"Experience (years): {post.get('experience') or ''}\n"
                f"Highest Qualification: {post.get('qualification') or ''}"
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

        return request.redirect('/jobs?applied=1')
