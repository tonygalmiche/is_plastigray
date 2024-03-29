
//Doc : https://www.odoo.com/documentation/8.0/howtos/web.html
//Doc : https://www.odoo.com/documentation/8.0/reference/javascript.html#openerp.Model.query


//Cette page est appellée au démarrage d'Odoo


//Cette fonction est appellée au démarrage d'Odoo car elle a le même nom que le module
openerp.is_plastigray = function(instance, local) {


    //** Permet de coloriser l'interface ***************************************
    var _t = instance.web._t,
        _lt = instance.web._lt,
        QWeb = instance.web.qweb;
    instance.session.on('module_loaded', this, function () {
        var self = this;
        var dataset = new instance.web.DataSetSearch(self, 'res.company', {}, [['id', '=', instance.session.company_id]]);
        dataset.read_slice([],0).then(function(result){
            if(result.length){
                var $topbar = window.$('#oe_main_menu_navbar');
                if(result[0].text_color && result[0].bg_color && $topbar.length)
                    $topbar.find('a').css('color', result[0].text_color);
                    $topbar.css('background-color', result[0].bg_color);
            }
        })
    });
    //**************************************************************************


    //Cette fonction est appellée en cliqant sur le menu
    local.AnalyseCBN = instance.Widget.extend({
        template: "AnalyseCBN",     // Permet de préciser le template QWeb à utiliser
        events: {
            "click a"     : "click_a",
            "click button": "click_button",
        },
        init: function(parent) {
            this._super(parent);
        },
        start: function() {
            d={};
            load_data(instance)
        },
        click_a: function(e) {
            d.obj=e.currentTarget;
            type=$(d.obj).attr("type");

            if(type=='stock-valorise'){
                attachment_id=$(d.obj).attr("attachment_id");
                this.do_action({
                    type: 'ir.actions.act_url',
                    url: '/web/binary/saveas?model=ir.attachment&field=datas&id='+attachment_id+'&filename_field=name',
                    target: 'new',
                });
            }

            if(type=='FL' || type=='FS' || type=='SA' || type=='CF' || type=='CP' || type=='SF') {
                model='mrp.prevision';
                if (type=='FL') {
                    model='mrp.production';
                }
                if (type=='CF' || type=='CP') {
                    model='sale.order';
                }
                if (type=='SF') {
                    model='purchase.order';
                }
                docid=$(d.obj).attr("docid");
                docid = docid.split(","); 
                nb=docid.length;
                if (nb==1) {
                    docid=docid[0]/1;
                    if (docid>0) {
                        //if(type=='FL' || type=='FS' || type=='SA') {
                            this.do_action({
                                type: 'ir.actions.act_window',
                                res_model: model,
                                res_id: docid,
                                views: [[false, 'form']],
                                flags: {
                                    form: {
                                        action_buttons: true, 
                                        options: {
                                            mode: 'edit'
                                        }
                                    }
                                },
                            });
                        /*
                        } else {
                            this.do_action({
                                type: 'ir.actions.act_window',
                                res_model: model,
                                res_id: docid,
                                views: [[false, 'form']],
                            });
                        }
                        */
                    }
                } else {
                    ids=new Array();
                    $.each(docid, function(k, v) {
                        ids.push(v/1);
                    });
                    this.do_action({
                        type: 'ir.actions.act_window',
                        res_model: model,
                        views: [[false, 'list'], [false, 'form']],
                        domain: [['id', 'in', ids]],
                    });
                }
            }
        },
        click_button: function(e) {
            $("#validation").val('ok');
            load_data(instance)
        },
    });
    //Cette ligne permet de déclarer la fonction précédente  et de faire le lien avec l'action Odoo
    instance.web.client_actions.add('is_plastigray.is_analyse_cbn_tag', 'instance.is_plastigray.AnalyseCBN');














    //Cette fonction est appellée en cliqant sur le menu
    local.AnalyseCBN2 = instance.Widget.extend({
        template: "AnalyseCBN2",     // Permet de préciser le template QWeb à utiliser
        events: {
            "click a"      : "click_a",
            "click button" : "click_button",
            "click img"    : "click_img",
            "keydown input": "keydown_input",
            //"change input": "change_input",
            //"change select": "change_select",
        },


        // events: {
        //     'keydown input': function (e) {
        //         switch (e.which) {
        //         case $.ui.keyCode.UP:
        //         case $.ui.keyCode.DOWN:
        //             e.stopPropagation();
        //         }
        //     },
        // },
    


        init: function(parent) {
            this._super(parent);
        },
        start: function() {
            d={};
            load_data2(instance)
        },
        click_a: function(e) {
            d.obj=e.currentTarget;
            type=$(d.obj).attr("type");

            if(type=='stock-valorise'){
                attachment_id=$(d.obj).attr("attachment_id");
                this.do_action({
                    type: 'ir.actions.act_url',
                    url: '/web/binary/saveas?model=ir.attachment&field=datas&id='+attachment_id+'&filename_field=name',
                    target: 'new',
                });
            }

            if(type=='FL' || type=='FS' || type=='SA' || type=='CF' || type=='CP' || type=='SF') {
                model='mrp.prevision';
                if (type=='FL') {
                    model='mrp.production';
                }
                if (type=='CF' || type=='CP') {
                    model='sale.order';
                }
                if (type=='SF') {
                    model='purchase.order';
                }
                docid=$(d.obj).attr("docid");
                docid = docid.split(","); 
                nb=docid.length;
                if (nb==1) {
                    docid=docid[0]/1;
                    if (docid>0) {
                        //if(type=='FL' || type=='FS' || type=='SA') {
                            this.do_action({
                                type: 'ir.actions.act_window',
                                res_model: model,
                                res_id: docid,
                                views: [[false, 'form']],
                                flags: {
                                    form: {
                                        action_buttons: true, 
                                        options: {
                                            mode: 'edit'
                                        }
                                    }
                                },
                            });
                    }
                } else {
                    ids=new Array();
                    $.each(docid, function(k, v) {
                        ids.push(v/1);
                    });
                    this.do_action({
                        type: 'ir.actions.act_window',
                        res_model: model,
                        views: [[false, 'list'], [false, 'form']],
                        domain: [['id', 'in', ids]],
                    });
                }
            }
        },
        click_button: function(e) {
            $("#validation").val('ok');
            load_data2(instance)
        },
        keydown_input: function(e) {
            //console.log(e);
            //console.log(e.keyCode);
            if (e.keyCode==13){
                $("#validation").val('ok');
                load_data2(instance);
            }
        },
        // change_input: function(e) {
        //     $("#validation").val('ok');
        //     load_data2(instance)
        // },
        // change_select: function(e) {
        //     $("#validation").val('ok');
        //     load_data2(instance)
        // },


        click_img: function(e) {
            obj=e.currentTarget;
            productid=$(obj).attr("productid");
            td=$(obj).parent().parent();
            tr=td.parent();
            trcolor = $(tr).attr("trcolor");
            trid=$(tr).attr("id");
            lig=parseInt(td.attr("rowspan"));
            for (j = 0; j < lig; ++j) {
                tr.hide();
                if (tr.next().length==1) {
                    tr=tr.next();
                }
            }
            load_tr(instance,productid,tr,trcolor,trid);
        },


    });
    //Cette ligne permet de déclarer la fonction précédente  et de faire le lien avec l'action Odoo
    instance.web.client_actions.add('is_plastigray.is_analyse_cbn2_tag', 'instance.is_plastigray.AnalyseCBN2');


}



function _get_filter(){
    height=window.innerHeight-190; // Recupere l'espace disponilbe dans le navigateur
    width=window.innerWidth-250;   // Recupere l'espace disponilbe dans le navigateur
    var filter = {
        code_pg_debut     : $("#code_pg_debut").val(),
        gest              : $("#gest").val(),
        cat               : $("#cat").val(),
        moule             : $("#moule").val(),
        projet            : $("#projet").val(),
        client            : $("#client").val(),
        fournisseur       : $("#fournisseur").val(),
        nb_semaines       : $("#nb_semaines").val(),
        type_commande     : $("#type_commande").val(),
        type_rapport      : $("#type_rapport").val(),
        calage            : $("#calage").val(),
        valorisation      : $("#valorisation").is(':checked'),
        validation        : $("#validation").val(),
        height            : height,
        width             : width,
    }; 
    return filter;
}


function load_tr(instance,productid,tr,trcolor,trid){
    var mrp_prevision_model   = new instance.web.Model("mrp.prevision");
    var product_model         = new instance.web.Model("product.product");


    var Products = new openerp.Model('product.product');


    filter=_get_filter();
    filter.product_id=productid;


    Products.call('load_tr',[filter,trcolor,trid],{}).then(function (data) {
        html=data['html'];
        tr.before(html);
    });
}



function load_data2(instance){
    date = new Date(); t1=date.getTime();
    var mrp_prevision_model   = new instance.web.Model("mrp.prevision");
    var product_model         = new instance.web.Model("product.product");
    var html;

    var id = document.getElementById("table_body");
    filter=_get_filter();

    var Products = new openerp.Model('product.product');

    Products.call('analyse_cbn2',[filter],{}).then(function (data) {
        $("#titre").html(data['titre']);
        $('#code_pg_debut').val(data['code_pg_debut']);
        $('#moule').val(data['moule']);
        $('#cat').val(data['cat']);
        $('#projet').val(data['projet']);
        $('#client').val(data['client']);
        $('#valorisation').val(data['valorisation']);

        //select gest
        $("#gest").empty();
        $.each(data['select_gest'], function(k,v) {
            $('#gest').append($("<option></option>").attr("value",v).text(v));
        });
        $('#gest').val(data['gest']);

        //select fournisseur
        $("#fournisseur").empty();
        $.each(data['select_fournisseur'], function(k,v) {
            $('#fournisseur').append($("<option></option>").attr("value",v).text(v));
        });
        $('#fournisseur').val(data['fournisseur']);

        //select nb_semaines
        $("#nb_semaines").empty();
        $.each(data['select_nb_semaines'], function(k,v) {
            $('#nb_semaines').append($("<option></option>").attr("value",v).text(v));
        });
        $('#nb_semaines').val(data['nb_semaines']);

        //select type_commande
        $("#type_commande").empty();
        $.each(data['select_type_commande'], function(k,v) {
            $('#type_commande').append($("<option></option>").attr("value",v).text(v));
        });
        $('#type_commande').val(data['type_commande']);

        //select type_rapport
        $("#type_rapport").empty();
        $.each(data['select_type_rapport'], function(k,v) {
            $('#type_rapport').append($("<option></option>").attr("value",v).text(v));
        });
        $('#type_rapport').val(data['type_rapport']);

        //select calage
        $("#calage").empty();
        $.each(data['select_calage'], function(k,v) {
            $('#calage').append($("<option></option>").attr("value",v).text(v));
        });
        $('#calage').val(data['calage']);

        //Affichage des résultats
        html=data['html'];
        $("#analysecbn").html(html);
        $("#table_body").height(height);
    });
}














function load_data(instance){
    date = new Date(); t1=date.getTime();
    var mrp_prevision_model   = new instance.web.Model("mrp.prevision");
    var product_model         = new instance.web.Model("product.product");
    var html;

    var id = document.getElementById("table_body");

    height=window.innerHeight-190; // Recupere l'espace disponilbe dans le navigateur
    width=window.innerWidth-250;   // Recupere l'espace disponilbe dans le navigateur

    var filter = {
        code_pg_debut     : $("#code_pg_debut").val(),
        gest              : $("#gest").val(),
        cat               : $("#cat").val(),
        moule             : $("#moule").val(),
        projet            : $("#projet").val(),
        client            : $("#client").val(),
        fournisseur       : $("#fournisseur").val(),
        nb_semaines       : $("#nb_semaines").val(),
        type_commande     : $("#type_commande").val(),
        type_rapport      : $("#type_rapport").val(),
        calage            : $("#calage").val(),
        valorisation      : $("#valorisation").is(':checked'),
        validation        : $("#validation").val(),
        height            : height,
        width             : width,
    }; 


    var Products = new openerp.Model('product.product');

    Products.call('analyse_cbn',[filter],{}).then(function (data) {
        $("#titre").html(data['titre']);
        $('#code_pg_debut').val(data['code_pg_debut']);
        $('#moule').val(data['moule']);
        $('#cat').val(data['cat']);
        $('#projet').val(data['projet']);
        $('#client').val(data['client']);
        $('#valorisation').val(data['valorisation']);

        //select gest
        $("#gest").empty();
        $.each(data['select_gest'], function(k,v) {
            $('#gest').append($("<option></option>").attr("value",v).text(v));
        });
        $('#gest').val(data['gest']);

        //select fournisseur
        $("#fournisseur").empty();
        $.each(data['select_fournisseur'], function(k,v) {
            $('#fournisseur').append($("<option></option>").attr("value",v).text(v));
        });
        $('#fournisseur').val(data['fournisseur']);

        //select nb_semaines
        $("#nb_semaines").empty();
        $.each(data['select_nb_semaines'], function(k,v) {
            $('#nb_semaines').append($("<option></option>").attr("value",v).text(v));
        });
        $('#nb_semaines').val(data['nb_semaines']);

        //select type_commande
        $("#type_commande").empty();
        $.each(data['select_type_commande'], function(k,v) {
            $('#type_commande').append($("<option></option>").attr("value",v).text(v));
        });
        $('#type_commande').val(data['type_commande']);

        //select type_rapport
        $("#type_rapport").empty();
        $.each(data['select_type_rapport'], function(k,v) {
            $('#type_rapport').append($("<option></option>").attr("value",v).text(v));
        });
        $('#type_rapport').val(data['type_rapport']);

        //select calage
        $("#calage").empty();
        $.each(data['select_calage'], function(k,v) {
            $('#calage').append($("<option></option>").attr("value",v).text(v));
        });
        $('#calage').val(data['calage']);

        //Affichage des résultats
        html=data['html'];
        $("#analysecbn").html(html);
        $("#table_body").height(height);
    });
}




















function clicktr(i,c,z)
{
    var a = document.getElementById(''+i+'');
    if (z == '2')
    {
        if (a.style.backgroundColor == "rgb(204, 255, 204)") 
        { 
            a.style.backgroundColor = "#FFFF00";
        }
        else 
        {
            a.style.backgroundColor = "#CCFFCC";
        }
    }
    else if (z == '1')
    {
        if (a.style.backgroundColor != "rgb(204, 255, 204)") {
            if (a.style.backgroundColor == "rgb(255, 255, 0)") { a.style.backgroundColor = '#'+c; }
            else { a.style.backgroundColor = "#FFFF00"; }
        }
    }
}




