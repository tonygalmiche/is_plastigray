
/*
openerp.is_plastigray = function(instance) {
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
};
*/
