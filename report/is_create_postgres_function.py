# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_create_postgres_function(models.Model):
    _name='is.create.postgres.function'
    _auto = False


    def init(self, cr):
        cr.execute("""

            CREATE OR REPLACE FUNCTION get_property_account_receivable(partner_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select substring(value_reference, 17)::int account_receivable_id
                    from ir_property ip 
                    where ip.name='property_account_receivable' and res_id=concat('res.partner,',partner_id)
                    limit 1
                );
            END;
            $$ LANGUAGE plpgsql;


            CREATE OR REPLACE FUNCTION get_property_account_payable(partner_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select substring(value_reference, 17)::int account_payable_id
                    from ir_property ip 
                    where ip.name='property_account_payable' and res_id=concat('res.partner,',partner_id)
                    limit 1
                );
            END;
            $$ LANGUAGE plpgsql;


            CREATE OR REPLACE FUNCTION get_property_account_position(partner_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select substring(value_reference, 25)::int account_position_id
                    from ir_property ip 
                    where ip.name='property_account_position' and res_id=concat('res.partner,',partner_id)
                    limit 1
                );
            END;
            $$ LANGUAGE plpgsql;


            CREATE OR REPLACE FUNCTION get_property_payment_term(partner_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select substring(value_reference, 22)::int payment_term_id
                    from ir_property ip 
                    where ip.name='property_payment_term' and res_id=concat('res.partner,',partner_id)
                    limit 1
                );
            END;
            $$ LANGUAGE plpgsql;


            CREATE OR REPLACE FUNCTION get_property_supplier_payment_term(partner_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select substring(value_reference, 22)::int payment_term_id
                    from ir_property ip 
                    where ip.name='property_supplier_payment_term' and res_id=concat('res.partner,',partner_id)
                    limit 1
                );
            END;
            $$ LANGUAGE plpgsql;


        """)





