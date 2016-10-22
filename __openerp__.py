# -*- coding: utf-8 -*-
{
    "name" : "InfoSaône - Module Odoo pour Plastigray",
    "version" : "0.2",
    "author" : "InfoSaône",
    "category" : "InfoSaône\Plastigray",
    'description': """
    InfoSaône - Module Odoo pour Plastigray 
    ===================================================
    Ce module sert uniquement à installer les dépendances du projet Plastigray et à configurer les menus
    """,
    'maintainer': 'InfoSaône',
    'website': 'http://www.infosaone.com',
    "depends" : [
        "base",
        "mail",
        "crm",                    # CRM
        "account_voucher",        # eFacturation & Règlements
        "account_accountant",     # Comptabilité et finance
        "sale",                   # Gestion des ventes
        "stock",                  # Stock
        "mrp",                    # MRP
        "mrp_operations",         # Gammes
        "purchase",               # Gestion des achats
        "is_inventory",           # Modifications Inventaires
        "is_mold",                # Moules et Projets pour l'injection plastique
        "is_pg_product",          # Fiche article
        "is_gestion_lot",         # Gestion des lots pour le contrôle qualité
    ], 
    "data" : [
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
        "wizard/is_liste_servir_wizard_view.xml",
        "wizard/generate_previsions_view.xml",
        "views/layouts.xml",
        "views/report_mrpbomstructure.xml",
        "views/webclient_templates.xml",
        "views/report_liste_servir.xml",
        "views/report_inventaire.xml",
        "views/report_paperformat.xml",
        "views/report_stockpicking.xml",
        "views/report_invoice.xml",
        "views/report.xml",
        "report/is_pic_3mois.xml",
        "report/is_comparatif_gamme_standard_generique.xml",
        "report/is_article_sans_nomenclature.xml",
        "report/is_article_sans_fournisseur.xml",
        "report/is_pricelist_item.xml",
        "report/is_cas_emplois.xml",
        "menu.xml",  
        "security/res.groups.xml",
        "security/ir.model.access.csv",
    ], 
    "installable": True,
    "active": False
}




