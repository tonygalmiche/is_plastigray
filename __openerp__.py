# -*- coding: utf-8 -*-
{
    "name" : "InfoSaône - Module Odoo pour Plastigray",
    "version" : "0.2",
    "author" : "InfoSaône",
    "category" : "InfoSaône\Plastigray",
    "description": """
InfoSaône - Module Odoo pour Plastigray
===================================================
Module principal du projet Plastigray
    """,
    "maintainer": 'InfoSaône',
    "website": 'http://www.infosaone.com',
    "depends" : [
        "base",
        "mail",
        "document",
        "crm",                    # CRM
        "account_voucher",        # eFacturation & Règlements
        "account_accountant",     # Comptabilité et finance
        "sale",                   # Gestion des ventes
        "stock",                  # Stock
        "sale_stock",
        "mrp",                    # MRP
        "mrp_operations",         # Gammes
        "purchase",               # Gestion des achats
        "is_mold",                # Moules et Projets pour l'injection plastique
        "is_pg_product",          # Fiche article
        "account_cancel",         # Permet d'autoriser l'annulation des factures 
    ], 
    "data" : [
        "security/res.groups.xml",
        "security/ir.model.access.csv", # Permet de définir rapidement les accès de base en CSV
        "security/ir.model.access.xml", # Permet de définit plus précisement les accès complèmenaires en XML pour mettre des commentaires
        "security/res.groups.csv",

        "res_partner_view.xml",  # Vue partenaire modifiée
        "assets.xml",            # Permet d'ajouter des css et des js
        "sale_view.xml",
        "account_invoice_view.xml",
        "sale_picking_view.xml",
        "mrp_view.xml",
        "stock_view.xml",
        "product_view.xml",
        "product_pricelist_view.xml",
        "is_pdc_view.xml",
        "is_liste_servir_sequence.xml",
        "is_liste_servir_view.xml",
        "is_edi_cde_cli_view.xml",
        "is_inventaire_view.xml",
        "is_inventaire_sequence.xml",
        "is_mem_var_view.xml",
        "is_cout_view.xml",
        "res_company_view.xml",
        "is_tarif_cial_view.xml",
        "mrp_prevision_view.xml",
        "mrp_prevision_sequence.xml",
        "is_resource_view.xml",
        "is_cde_ouverte_fournisseur_view.xml",
        "mrp_production_view.xml",
        "account_invoice_sequence.xml",
        "is_facturation_fournisseur_view.xml",
        "is_bon_transfert_view.xml",
        "purchase_view.xml",
        "res_users_view.xml",
        "is_etuve_view.xml",
        "is_cde_ferme_cadencee_view.xml",
        "is_pic_3ans.xml",
        "is_copy_other_database_view.xml",
        "wizard/is_gestion_lot_view.xml",
        "wizard/is_stock_mise_rebut_view.xml",
        "wizard/is_liste_servir_wizard_view.xml",
        "wizard/generate_previsions_view.xml",
        "wizard/mrp_product_produce_view.xml",
        "wizard/is_export_seriem_view.xml",
        "wizard/stock_transfer_details.xml",
        "wizard/audit_log_wizard.xml",
        "views/web_view.xml",
        "views/layouts.xml",
        "views/report_mrpbomstructure.xml",
        "views/webclient_templates.xml",
        "views/report_paperformat.xml",
        "views/report_liste_servir.xml",
        "views/report_inventaire.xml",
        "views/report_stockpicking.xml",
        "views/report_invoice.xml",
        "views/report_cde_ouverte_fournisseur.xml",
        "views/report_cde_ferme_cadencee.xml",
        "views/report_appel_de_livraison.xml",
        "views/report_document_fabrication.xml",
        "views/report_plan_de_charge.xml",
        "views/report_bon_transfert.xml",
        "views/report_purchaseorder.xml",
        "views/report_ar_commande.xml",
        "views/report_liste_article.xml",
        "views/report_is_cout.xml",
        "views/report_pricelist_version.xml",
        "views/report_stockdetails_tree.xml",
        "views/report_stockmovement_tree.xml",
        "views/report.xml",
        "report/stock_bloquer_lot.xml",
        "report/stock_debloquer_lot.xml",
        "report/stock_change_location_lot.xml",
        "report/stock_rebut_lot.xml",
        "report/is_pic_3mois.xml",
        "report/is_comparatif_gamme_standard_generique.xml",
        "report/is_comparatif_tps_article_gamme.xml",
        "report/is_comparatif_tarif_cial_vente.xml",
        "report/is_comparatif_tarif_facture.xml",
        "report/is_comparatif_tarif_commande.xml",
        "report/is_comparatif_uc_lot.xml",
        "report/is_comparatif_uc_lot_mini.xml",
        "report/is_comparatif_lot_prix.xml",
        "report/is_article_sans_nomenclature.xml",
        "report/is_article_sans_fournisseur.xml",
        "report/is_pricelist_item.xml",
        "report/is_cas_emplois.xml",
        "report/is_nomenclature_sans_gamme.xml",
        "report/is_stock_valorise.xml",
        "report/is_mouvement_stock.xml",
        "report/is_ligne_reception.xml",
        "report/is_ligne_livraison.xml",
        "report/is_users_groups.xml",
        "report/is_model_groups.xml",
        "report/is_stock_move.xml",
        "report/is_stock_quant.xml",
        "report/is_purchase_order_line.xml",
        "report/is_comparatif_tarif_reception.xml",
        "report/is_comparatif_livraison_facture.xml",
        "report/is_comparatif_cde_draft_done.xml",
        "report/is_account_invoice_line.xml",
        "report/is_marge_contributive.xml",
        "report/is_suivi_budget_analytique.xml",
        "report/is_comparatif_lot_appro_prix.xml",
        "report/is_comparatif_article_tarif_cial.xml",
        "report/is_res_partner.xml",
        "report/is_article_sans_cde_ouverte_fou.xml",
        "report/is_anomalie_position_fiscale.xml",
        "report/is_sale_order_line.xml",
        "report/is_product_packaging.xml",
        "menu.xml",
    ], 
    "installable": True,
    "active": False
}




