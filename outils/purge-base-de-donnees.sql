
-- Stocks --
delete from stock_move;
delete from stock_quant;
delete from stock_production_lot;
delete from stock_inventory;
delete from is_inventaire;


-- Gestion des étuves 
delete from is_etuve_of;
delete from is_etuve_saisie;
delete from is_etuve;

-- CBN et Ordres de fabrications
delete from mrp_prevision;
delete from mrp_production;
delete from is_pdc;


-- Factures --
delete from is_facturation_fournisseur;
delete from account_invoice;


-- Livraisons --
delete from stock_pack_operation;
delete from stock_picking;


-- Compta --
delete from account_voucher;
delete from account_move;
delete from account_move_line;


-- Commandes Client --
delete from is_bon_transfert;
delete from is_liste_servir;
delete from is_liste_servir_message;
delete from is_edi_cde_cli;

-- delete from sale_order_line where state!='draft';
-- delete from sale_order      where state!='draft';
delete from sale_order;


-- Commandes Fournisseur --
delete from is_cde_ouverte_fournisseur;
delete from is_cde_ferme_cadencee_order;
delete from purchase_order;

-- Tarif Cial
delete from is_tarif_cial;


-- Cout Article => Prix forcés à conserver --
delete from is_cout_calcul;
delete from is_cout;



---- Odoo0 : Conserver dans Odoo0, les clients, les moules, projets et postes de charges.

---- Nomenclatures
--delete from mrp_bom;
--delete from mrp_production_product_line;

---- Gammes
--delete from mrp_routing;

---- Commandes et PIC à 3 ans
--delete from procurement_order;
--delete from is_pic_3ans;
--delete from is_pic_3ans_saisie;
--delete from is_cde_ferme_cadencee;

---- Inventaire
--delete from is_inventaire_ecart;
--delete from is_inventaire_line_tmp;

---- Articles
--delete from product_product;
--delete from product_template;


---- Liste de prix
--delete from product_pricelist;


-- -- Odoo3 : Supprimer moules projet, postes de charges 

---- Projets et moules
--delete from is_mold_project;
--delete from is_mold;
--delete from is_dossierf;

---- Postes de charge
--delete from mrp_workcenter;


----delete from is_mem_var;
----delete from res_partner where id>50;
----delete from mail_message;
----delete from ir_attachment;




