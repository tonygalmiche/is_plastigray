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
        "hr",                     # RH
        "is_mold",                # Moules et Projets pour l'injection plastique
        "is_pg_product",          # Fiche article
        "account_cancel",         # Permet d'autoriser l'annulation des factures 
        "auditlog",
        "web",
        "web_widget_color",
#        "is_pg_2019",
    ], 
    "data" : [
        "security/res.groups.xml",
        "security/ir.model.access.csv",
        "security/ir.model.access.xml", 
        "security/ir.model.access.is.demande.achat.xml",
        "security/ir.model.access.is.liste.servir.xml",
        "security/res.groups.csv",
        "res_country_view.xml",
        "res_partner_view.xml",
        "assets.xml",
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
        "log_view.xml",
        "purchase_workflow.xml",
        "is_gabarit_controle_view.xml",
        "is_plaquette_etalon_view.xml",
        "is_instrument_mesure_view.xml",
        "is_historique_controle_view.xml",
        "is_presse_view.xml",
        "is_prechauffeur_view.xml",
        "is_commande_externe_view.xml",
        "is_demande_achat_view.xml",
        "is_demande_achat_serie_view.xml",
        "is_demande_achat_fg_view.xml",
        "is_demande_achat_invest_view.xml",
        "is_demande_achat_moule_view.xml",
        "email_template.xml",
        "is_facture_pk_view.xml",
        "is_moyen_fabrication_view.xml",
        "is_moyen_fabrication_autre_view.xml",
        "is_piece_montabilite_view.xml",
        "is_instruction_particuliere_view.xml",
        "is_consigne_journaliere_view.xml",
        "is_demande_transport_view.xml",
        "is_bl_manuel_view.xml",
        "is_taux_rotation_stock_view.xml",
        "is_export_edi_view.xml",
        "is_deb_view.xml",
        "hr_view.xml",
        "is_pointage_view.xml",
        "is_reach_view.xml",
        "is_rgpd_view.xml",
        "is_mini_delta_dore_view.xml",
        "is_export_cegid_view.xml",
        "is_galia_base_view.xml",
        "is_article_view.xml",
        "calendar_view.xml",
        "wizard/is_gestion_lot_view.xml",
        "wizard/is_stock_mise_rebut_view.xml",
        "wizard/is_liste_servir_wizard_view.xml",
        "wizard/generate_previsions_view.xml",
        "wizard/mrp_product_produce_view.xml",
        "wizard/is_export_seriem_view.xml",
        "wizard/stock_transfer_details.xml",
        "wizard/audit_log_wizard.xml",
        "wizard/is_cas_emploi_wizard.xml",
        "wizard/is_cas_emploi_wizard_new.xml",
        "wizard/set_sheduler_cout_article.xml",
        "wizard/assistent_report_view.xml",
        "wizard/is_change_emplacement_wizard_view.xml",
        "views/web_view.xml",
        "views/layouts.xml",
        "views/report_mrpbomstructure.xml",
        "views/webclient_templates.xml",
        "views/report_paperformat.xml",
        "views/report_liste_servir.xml",
        "views/report_inventaire.xml",
        "views/report_inventaire_ecart.xml",
        "views/report_stockpicking.xml",
        "views/report_invoice.xml",
        "views/report_cde_ouverte_fournisseur.xml",
        "views/report_relance_fournisseur.xml",
        "views/report_cde_ferme_cadencee.xml",
        "views/report_appel_de_livraison.xml",
        "views/report_document_fabrication.xml",
        "views/report_plan_de_charge.xml",
        "views/report_bon_transfert.xml",
        "views/report_purchaseorder.xml",
        "views/report_devis_commande.xml",
        "views/report_ar_commande.xml",
        "views/report_liste_article.xml",
        "views/report_is_cout.xml",
        "views/report_pricelist_version.xml",
        "views/report_stockdetails_tree.xml",
        "views/report_stockmovement_tree.xml",
        "views/report_feuilles_inventaire.xml",
        "views/report_is_instrument_mesure.xml",
        "views/report_is_gabarit_controle.xml",
        "views/report_is_plaquette_etalon.xml",
        "views/report_is_demande_achat.xml",
        "views/report_is_facture_pk.xml",
        "views/report_is_consigne_journaliere.xml",
        "views/report_is_inventaire_line_tree.xml",
        "views/report_is_bl_manuel.xml",
        "views/report_proforma.xml",
        "views/report_is_facture_pk_line_tree.xml",
        "views/report_emballage.xml",
        "views/report_ligne_reception_tree.xml",
        'views/report_is_reach.xml',
        'views/report_is_livraison_gefbox_tree.xml',
        'views/report_galia_base.xml',
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
        "report/is_mrp_production_workcenter_line.xml",
        "report/is_livraison_gefco.xml",
        "report/is_certifications_qualite_suivi.xml",
        "report/is_anomalie_declar_prod.xml",
        "report/is_comparatif_cout_pk_tarif.xml",
        "menu.xml",
    ], 
    "qweb": [
        "static/src/xml/*.xml"
    ],
    "installable": True,
    "active": False,
    #"auto_install": True,
}

