# -*- coding: utf-8 -*-
# © 2015 ABF OSIELL <http://osiell.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp import models, fields



class AuditlogLogLine(models.Model):
    _inherit = 'auditlog.log.line'

    
    related_name = fields.Char(related='log_id.name', store=True, copy=False, string="Resource Name")
    related_model_id = fields.Many2one(
        'ir.model', related='log_id.model_id', store=True, copy=False, string=u"Model")
    related_res_id = fields.Integer(related='log_id.res_id', store=True, copy=False, string= u"Resource ID")
    related_user_id = fields.Many2one(
        'res.users', related='log_id.user_id', store=True, copy=False, string=u"User")
    related_method = fields.Char(related='log_id.method', store=True, copy=False, string=u"Method")
    related_http_session_id = fields.Many2one(
        'auditlog.http.session', related='log_id.http_session_id', store=True, copy=False, string=u"Session")
    related_http_request_id = fields.Many2one(
        'auditlog.http.request', related='log_id.http_request_id', store=True, copy=False, string=u"HTTP Request")
    related_log_type = fields.Selection(related='log_id.log_type', store=True, copy=False, string=u"Type")
#         [('full', u"Full log"),
#          ('fast', u"Fast log"),
#          ],
#         string=u"Type")
