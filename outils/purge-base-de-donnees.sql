
-- Stocks --
delete from stock_move;
delete from stock_quant;
delete from stock_production_lot;
delete from stock_inventory;
delete from is_inventaire;


-- CBN et Ordres de fabrications
delete from mrp_prevision;
delete from mrp_production;
delete from is_pdc;


-- Factures --
delete from account_invoice;


-- Livraisons --
delete from stock_pack_operation;
delete from stock_picking;


-- Compta --
delete from account_voucher;
delete from account_move;
delete from account_move_line;


-- Commandes Client --
delete from is_liste_servir;
delete from is_edi_cde_cli;

delete from sale_order_line where state!='draft';
delete from sale_order      where state!='draft';

-- Commandes Fournisseur --
delete from purchase_order;

-- Cout Article --
delete from is_cout_calcul;
delete from is_cout;
