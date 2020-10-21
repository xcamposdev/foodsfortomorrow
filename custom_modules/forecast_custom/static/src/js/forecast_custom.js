odoo.define('forecast_custom.custom_javascript', function (require) {
'use strict';

    var ajax = require('web.ajax');
    var ActionManager = require('web.ActionManager');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var ListView = require('web.ListView');
    var session = require('web.session');
    var ListController = require("web.ListController");

    var IncludeListView = {
        renderButtons: function() {
            this._super.apply(this, arguments);
            if (this.modelName === "x_forecast_ventas") {
                
                if (this.$buttons) {
                    this.$buttons.find('.o_list_button_add').click(this.proxy('open_wizard'));
                }
            }
        },
        open_wizard: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var self = this;
            self.do_action(
                {
                    name: "Generación de datos mensual",
                    type: 'ir.actions.act_window',
                    res_model: 'x.forecast.ventas.wizard',
                    view_mode: 'form',
                    view_type: 'form',
                    target: 'new',
                    views: [[false, 'form']],
                    id: "forecast_open_wizard_act_window",
                },
            )
        },
    };
    ListController.include(IncludeListView);
});