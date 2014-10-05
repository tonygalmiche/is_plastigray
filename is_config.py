# -*- coding: utf-8 -*-

import logging
from operator import attrgetter
import re

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import ustr
from openerp.tools.translate import _
from openerp import exceptions
from lxml import etree

_logger = logging.getLogger(__name__)

# Default sale setting       
class is_sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'
 
    def execute_sale_setting(self, cr, uid, context=None):
        if context is None:
            context = {}
 
        context = dict(context, active_test=False)
        if uid != SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager'):
            raise openerp.exceptions.AccessError(_("Only administrators can change the settings"))
 
        ir_values = self.pool['ir.values']
        ir_module = self.pool['ir.module.module']
        res_groups = self.pool['res.groups']
 
        classified = self._get_classified_fields(cr, uid, context=context)
 
        values = {
            'group_invoice_deli_orders': True,
            'group_sale_pricelist': True,
            'group_uom': True}
 
        config_id = self.create(cr, uid, values, context)
        config = self.browse(cr, uid, config_id, context)
 
        # default values fields
        for name, model, field in classified['default']:
            ir_values.set_default(cr, SUPERUSER_ID, model, field, config[name])
 
        # group fields: modify group / implied groups
        for name, groups, implied_group in classified['group']:
            gids = map(int, groups)
            if config[name]:
                res_groups.write(cr, uid, gids, {'implied_ids': [(4, implied_group.id)]}, context=context)
            else:
                res_groups.write(cr, uid, gids, {'implied_ids': [(3, implied_group.id)]}, context=context)
                uids = set()
                for group in groups:
                    uids.update(map(int, group.users))
                implied_group.write({'users': [(3, u) for u in uids]})
 
        # other fields: execute all methods that start with 'set_'
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)(cr, uid, [config_id], context)
 
        # module fields: install/uninstall the selected modules
        to_install = []
        to_uninstall_ids = []
        lm = len('module_')
        for name, module in classified['module']:
            if config[name]:
                to_install.append((name[lm:], module))
            else:
                if module and module.state in ('installed', 'to upgrade'):
                    to_uninstall_ids.append(module.id)
 
        if to_uninstall_ids:
            ir_module.button_immediate_uninstall(cr, uid, to_uninstall_ids, context=context)
 
        action = self._install_modules(cr, uid, to_install, context=context)
        if action:
            return action
  
        #=======================================================================
        # After the uninstall/install calls, the self.pool is no longer valid.
        # So we reach into the RegistryManager directly.
        #=======================================================================
        res_config = openerp.modules.registry.RegistryManager.get(cr.dbname)['res.config']
        config = res_config.next(cr, uid, [], context=context) or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config
  
        #force client-side reload (update user menu and current view)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
 
is_sale_configuration()
 
# Default purchase setting
class is_purchase_configuration(osv.osv_memory):
    _inherit = 'purchase.config.settings'
 
    def execute_purchase_setting(self, cr, uid, context=None):
        if context is None:
            context = {}
 
        context = dict(context, active_test=False)
        if uid != SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager'):
            raise openerp.exceptions.AccessError(_("Only administrators can change the settings"))
 
        ir_values = self.pool['ir.values']
        ir_module = self.pool['ir.module.module']
        res_groups = self.pool['res.groups']
 
        classified = self._get_classified_fields(cr, uid, context=context)
 
        values = {
            'default_invoice_method': 'picking',
            'group_purchase_pricelist': True,
            'group_uom': True,
            'group_analytic_account_for_purchases': True}
 
        config_id = self.create(cr, uid, values, context)
        config = self.browse(cr, uid, config_id, context)
 
        # default values fields
        for name, model, field in classified['default']:
            ir_values.set_default(cr, SUPERUSER_ID, model, field, config[name])
 
        # group fields: modify group / implied groups
        for name, groups, implied_group in classified['group']:
            gids = map(int, groups)
            if config[name]:
                res_groups.write(cr, uid, gids, {'implied_ids': [(4, implied_group.id)]}, context=context)
            else:
                res_groups.write(cr, uid, gids, {'implied_ids': [(3, implied_group.id)]}, context=context)
                uids = set()
                for group in groups:
                    uids.update(map(int, group.users))
                implied_group.write({'users': [(3, u) for u in uids]})
 
        # other fields: execute all methods that start with 'set_'
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)(cr, uid, [config_id], context)
 
        # module fields: install/uninstall the selected modules
        to_install = []
        to_uninstall_ids = []
        lm = len('module_')
        for name, module in classified['module']:
            if config[name]:
                to_install.append((name[lm:], module))
            else:
                if module and module.state in ('installed', 'to upgrade'):
                    to_uninstall_ids.append(module.id)
 
        if to_uninstall_ids:
            ir_module.button_immediate_uninstall(cr, uid, to_uninstall_ids, context=context)
 
        action = self._install_modules(cr, uid, to_install, context=context)
        if action:
            return action
  
        #=======================================================================
        # After the uninstall/install calls, the self.pool is no longer valid.
        # So we reach into the RegistryManager directly.
        #=======================================================================
        res_config = openerp.modules.registry.RegistryManager.get(cr.dbname)['res.config']
        config = res_config.next(cr, uid, [], context=context) or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config
  
        #force client-side reload (update user menu and current view)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
 
is_purchase_configuration()
 
# Default stock setting
class is_stock_configuration(osv.osv_memory):
    _inherit = 'stock.config.settings'
 
    def execute_stock_setting(self, cr, uid, context=None):
        if context is None:
            context = {}
 
        context = dict(context, active_test=False)
        if uid != SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager'):
            raise openerp.exceptions.AccessError(_("Only administrators can change the settings"))
 
        ir_values = self.pool['ir.values']
        ir_module = self.pool['ir.module.module']
        res_groups = self.pool['res.groups']
 
        classified = self._get_classified_fields(cr, uid, context=context)
 
        values = {
            'group_stock_production_lot': True,
            'group_stock_tracking_lot': True,
            'group_stock_multiple_locations': True,
            'group_stock_packaging': True,
            'group_uom': True}
 
        config_id = self.create(cr, uid, values, context)
        config = self.browse(cr, uid, config_id, context)
 
        # default values fields
        for name, model, field in classified['default']:
            ir_values.set_default(cr, SUPERUSER_ID, model, field, config[name])
 
        # group fields: modify group / implied groups
        for name, groups, implied_group in classified['group']:
            gids = map(int, groups)
            if config[name]:
                res_groups.write(cr, uid, gids, {'implied_ids': [(4, implied_group.id)]}, context=context)
            else:
                res_groups.write(cr, uid, gids, {'implied_ids': [(3, implied_group.id)]}, context=context)
                uids = set()
                for group in groups:
                    uids.update(map(int, group.users))
                implied_group.write({'users': [(3, u) for u in uids]})
 
        # other fields: execute all methods that start with 'set_'
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)(cr, uid, [config_id], context)
 
        # module fields: install/uninstall the selected modules
        to_install = []
        to_uninstall_ids = []
        lm = len('module_')
        for name, module in classified['module']:
            if config[name]:
                to_install.append((name[lm:], module))
            else:
                if module and module.state in ('installed', 'to upgrade'):
                    to_uninstall_ids.append(module.id)
 
        if to_uninstall_ids:
            ir_module.button_immediate_uninstall(cr, uid, to_uninstall_ids, context=context)
 
        action = self._install_modules(cr, uid, to_install, context=context)
        if action:
            return action
  
        #=======================================================================
        # After the uninstall/install calls, the self.pool is no longer valid.
        # So we reach into the RegistryManager directly.
        #=======================================================================
        res_config = openerp.modules.registry.RegistryManager.get(cr.dbname)['res.config']
        config = res_config.next(cr, uid, [], context=context) or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config
  
        #force client-side reload (update user menu and current view)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
 
is_stock_configuration()
 
# Default MRP setting
class is_mrp_configuration(osv.osv_memory):
    _inherit = 'mrp.config.settings'
 
    def execute_mrp_setting(self, cr, uid, context=None):
        if context is None:
            context = {}
 
        context = dict(context, active_test=False)
        if uid != SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager'):
            raise openerp.exceptions.AccessError(_("Only administrators can change the settings"))
 
        ir_values = self.pool['ir.values']
        ir_module = self.pool['ir.module.module']
        res_groups = self.pool['res.groups']
 
        classified = self._get_classified_fields(cr, uid, context=context)
 
        values = {
            'group_mrp_routings': True,
            'group_mrp_properties': True}
 
        config_id = self.create(cr, uid, values, context)
        config = self.browse(cr, uid, config_id, context)
 
        # default values fields
        for name, model, field in classified['default']:
            ir_values.set_default(cr, SUPERUSER_ID, model, field, config[name])
 
        # group fields: modify group / implied groups
        for name, groups, implied_group in classified['group']:
            gids = map(int, groups)
            if config[name]:
                res_groups.write(cr, uid, gids, {'implied_ids': [(4, implied_group.id)]}, context=context)
            else:
                res_groups.write(cr, uid, gids, {'implied_ids': [(3, implied_group.id)]}, context=context)
                uids = set()
                for group in groups:
                    uids.update(map(int, group.users))
                implied_group.write({'users': [(3, u) for u in uids]})
 
        # other fields: execute all methods that start with 'set_'
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)(cr, uid, [config_id], context)
 
        # module fields: install/uninstall the selected modules
        to_install = []
        to_uninstall_ids = []
        lm = len('module_')
        for name, module in classified['module']:
            if config[name]:
                to_install.append((name[lm:], module))
            else:
                if module and module.state in ('installed', 'to upgrade'):
                    to_uninstall_ids.append(module.id)
 
        if to_uninstall_ids:
            ir_module.button_immediate_uninstall(cr, uid, to_uninstall_ids, context=context)
 
        action = self._install_modules(cr, uid, to_install, context=context)
        if action:
            return action
  
        #=======================================================================
        # After the uninstall/install calls, the self.pool is no longer valid.
        # So we reach into the RegistryManager directly.
        #=======================================================================
        res_config = openerp.modules.registry.RegistryManager.get(cr.dbname)['res.config']
        config = res_config.next(cr, uid, [], context=context) or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config
  
        #force client-side reload (update user menu and current view)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
 
is_mrp_configuration()
