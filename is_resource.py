# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import time
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _

class is_resource_calendar_leaves(osv.osv):
    _inherit = "resource.calendar.leaves"
    
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Company'),
        'reason': fields.selection([('h_summer', 'Summer holiday'),
                                    ('h_winter', 'Winter holiday'),
                                    ('h_public', 'Public holiday'),
                                    ('others', 'Others')], 'Reason of close'),
    }
    
    def create(self, cr, uid, vals, context=None):
        if vals['date_from']:
            date = datetime.strptime(vals['date_from'], '%Y-%m-%d %H:%M:%S')
            date_from = date.strftime('%Y-%m-%d 05:00:00')
            vals.update({'date_from': date_from})
        
        if vals['date_to']:
            date = datetime.strptime(vals['date_to'], '%Y-%m-%d %H:%M:%S')
            date_to = date.strftime('%Y-%m-%d 05:00:00')
            vals.update({'date_to': date_to})
        
        return super(is_resource_calendar_leaves, self).create(cr, uid, vals, context=context)
    
is_resource_calendar_leaves()
    
class is_res_partner_calendar(osv.osv):
    _inherit = "res.partner"
    
    _columns = {
        'calendar_line': fields.one2many('resource.calendar.leaves', 'partner_id', 'Leaves'),
        'close_monday': fields.boolean('Monday'),
        'close_tuesday': fields.boolean('Tuesday'),
        'close_wednesday': fields.boolean('Wednesday'),
        'close_thursday': fields.boolean('Thursday'),
        'close_friday': fields.boolean('Friday'),
        'close_saturday': fields.boolean('Saturday'),
        'close_sunday': fields.boolean('Sunday'),
    }
    
    _defaults = {
        'close_saturday': True,
        'close_sunday': True,
    }
    
is_res_partner_calendar()