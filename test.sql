
-- Requête pour importer le CBN dans le PDC

select  mrw.workcenter_id                   as workcenter_id,
        pt.is_mold_id                       as mold_id, 
        pt.is_couleur                       as matiere,
        sum(mp.quantity)                    as quantite,
        sum(mp.quantity*mrw.is_nb_secondes) as temps_s

from mrp_prevision mp inner join product_product  pp on mp.product_id=pp.id
                      inner join product_template pt on pp.product_tmpl_id=pt.id
                      inner join mrp_bom          mb on pt.id=mb.product_tmpl_id and mb.sequence=0
                      inner join mrp_routing_workcenter mrw on mb.routing_id=mrw.routing_id
where mp.type='fs'
group by mrw.workcenter_id, pt.is_mold_id, pt.is_couleur
order by mrw.workcenter_id;



