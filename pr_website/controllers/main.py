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

        applicant = request.env['hr.applicant'].sudo().create({
            'name': post.get('name') or post.get('partner_name') or 'Website Candidate',
            'partner_name': post.get('partner_name'),
            'email_from': post.get('email_from'),
            'partner_phone': post.get('partner_phone'),
            'partner_mobile': post.get('partner_mobile'),
            'job_id': job.id,
            'description': '\n'.join(filter(None, [
                'CNIC: %s' % (post.get('cnic') or ''),
                'Last Employer: %s' % (post.get('last_employer') or ''),
                'Years of Experience: %s' % (post.get('experience') or ''),
                'Gender: %s' % (post.get('gender') or ''),
                'Location: %s' % (post.get('location') or ''),
                'Area: %s' % (post.get('area') or ''),
                'Skills: %s' % (post.get('skills') or ''),
                'Work from Home: %s' % (post.get('work_from_home') or ''),
                'Address: %s' % (post.get('address') or ''),
            ])),
        })

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
