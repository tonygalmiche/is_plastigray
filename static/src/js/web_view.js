//  @@@ is_treeview2csv custom JS @@@
//#############################################################################
//    
//    Copyright (C) 2012 Therp BV (<>)
//
//    This program is free software: you can redistribute it and/or modify
//    it under the terms of the GNU Affero General Public License as published
//    by the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.
//
//    This program is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU Affero General Public License for more details.
//
//    You should have received a copy of the GNU Affero General Public License
//    along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
//#############################################################################
openerp.is_plastigray = function (instance) {

    var _t = instance.web._t, QWeb = instance.web.qweb;
    var has_action_id = false;

    function launch_wizard(self, view, user_type, invite) {
        var action = view.getParent().action;
        var context = new instance.web.CompoundContext(view.dataset.get_context() || []);
        var selected_id = [];
        if (view.fields_view.type == 'form') {
            selected_id.push(view.datarecord.id);
        }
        else if (view.fields_view.type == 'tree') {
            view.$el.find('th.oe_list_record_selector input:checked')
                .closest('tr').each(function () {
                selected_id.push($(this).data('id'));
            });
        }
        context.add({
            active_id: selected_id,
            active_ids: selected_id,
            active_model: view.dataset.model,
        });
        var Share = new instance.web.DataSet(self, 'audit.log.wizard', context);
        var domain = new instance.web.CompoundDomain(view.dataset.domain);
        rec_name = '';
        instance.web.pyeval.eval_domains_and_contexts({
            domains: [domain],
            contexts: [Share.get_context()]
        }).done(function (result) {
            Share.create({
                name: action.name,
                record_name: rec_name,
                domain: result.domain,
                action_id: action.id,
            }).done(function(share_id) {
                var step1 = Share.call('do_click_audit', [[share_id], Share.get_context()]).done(function(result) {
                    var active1 = 18
                    var action = result;
                    self.do_action(action);
                });
            });
        });
    }
    
    instance.web.Sidebar = instance.web.Sidebar.extend({
        start: function() {
            var self = this;
            this._super(this);
            self.add_items('other', [
                        { label: _t('Audit Log'),
                          callback: self.on_click_audit_log,
                          classname: 'oe_share' },
                        ]);
        },
        on_click_audit_log:function (item) {
	       var view = this.getParent()
	       var selected_id = [];
           if (view.fields_view.type == 'form') {
                selected_id.push(view.datarecord.id);
           }
           else if (view.fields_view.type == 'tree') {
                view.$el.find('th.oe_list_record_selector input:checked')
                    .closest('tr').each(function () {
                    selected_id.push($(this).data('id'));
                });
           }
           this.do_action({
                name: _t("Logs"),
                res_model : 'auditlog.log.line',
                domain : [['related_res_id', 'in', selected_id], ['related_model_id.model', '=', view.dataset.model]],
                views: [[false, 'list'], [false, 'form']],
                type : 'ir.actions.act_window',
                view_type : "list",
                view_mode : "list"
           });
           //launch_wizard(this, view, 'emails', false);
	    },

    });

};
