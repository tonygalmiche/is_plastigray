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


            CREATE OR REPLACE FUNCTION get_cout_act_matiere_st(pp_id  integer) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select ic.cout_act_matiere+ic.cout_act_st 
                            from is_cout ic
                            where ic.name=pp_id limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;


           CREATE OR REPLACE FUNCTION fsens(t text) RETURNS integer AS $$
            BEGIN
                RETURN (
                    SELECT
                    CASE
                    WHEN t::text = ANY (ARRAY['out_refund'::character varying::text, 'in_refund'::character varying::text])
                        THEN -1::int
                        ELSE 1::int
                    END
                );
            END;
            $$ LANGUAGE plpgsql;




            CREATE OR REPLACE FUNCTION get_amortissement_moule(code_client char, pt_id  integer) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select itc.amortissement_moule 
                            from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
                            where itc.product_id=pt_id and rp.is_code=code_client and itc.indice_prix=999
                            order by itc.amortissement_moule desc limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;


            CREATE OR REPLACE FUNCTION get_amortissement_moule_a_date(code_client char, pt_id  integer, date_tarif date) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select itc.amortissement_moule 
                            from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
                            where 
                                itc.product_id=pt_id and rp.is_code=code_client and 
                                (itc.date_fin   is null or itc.date_fin   >= date_tarif) and
                                (itc.date_debut is null or itc.date_debut <= date_tarif) 
                            order by itc.indice_prix desc limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;


            CREATE OR REPLACE FUNCTION get_amt_interne_a_date(code_client char, pt_id  integer, date_tarif date) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select itc.amt_interne 
                            from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
                            where 
                                itc.product_id=pt_id and rp.is_code=code_client and 
                                (itc.date_fin   is null or itc.date_fin   >= date_tarif) and
                                (itc.date_debut is null or itc.date_debut <= date_tarif) 
                            order by itc.indice_prix desc limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;


            CREATE OR REPLACE FUNCTION get_cagnotage_a_date(code_client char, pt_id  integer, date_tarif date) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select itc.cagnotage 
                            from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
                            where 
                                itc.product_id=pt_id and rp.is_code=code_client and 
                                (itc.date_fin   is null or itc.date_fin   >= date_tarif) and
                                (itc.date_debut is null or itc.date_debut <= date_tarif) 
                            order by itc.indice_prix desc limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;



        """)





