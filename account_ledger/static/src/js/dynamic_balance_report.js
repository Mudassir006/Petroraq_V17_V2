/** @odoo-module */
const { Component } = owl;
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
const actionRegistry = registry.category("actions");
import { uiService } from "@web/core/ui/ui_service";
//  Extending components for adding purchase report class
//class PurchaseReport extends Component {
class DynamicBalanceReport extends Component {
   async setup() {
       super.setup(...arguments);
       this.uiService = useService('ui');
       this.initial_render = true;
       this.orm = useService('orm');
       this.action = useService('action');
       this.start_date = useRef('date_from');
       this.end_date = useRef('date_to');
       this.main_head = useRef('main_head');
       this.department_id = useRef('department_id');
       this.section_id = useRef('section_id');
       this.project_id = useRef('project_id');
       this.account_id = useRef('account_id');
       this.state = useState({
           department_ids: [],
           section_ids: [],
           project_ids: [],
           account_ids: [],
           balance_report_line: [],
           data: null,
           wizard_id : []
       });
       this.load_filters_data();
       this.load_data();
       }

    // Load Filters Data

        async load_filters_data() {

            this.state.department_ids = await this.orm.searchRead("account.analytic.account", [["analytic_plan_type", "=", "department"]], ["id", "name"]);
            this.state.section_ids = await this.orm.searchRead("account.analytic.account", [["analytic_plan_type", "=", "section"]], ["id", "name"]);
            this.state.project_ids = await this.orm.searchRead("account.analytic.account", [["analytic_plan_type", "=", "project"]], ["id", "name"]);
            this.state.account_ids = await this.orm.searchRead("account.account", [["main_head", "!=", false]], ["id", "name"]);

        }

       async load_data(wizard_id = null) {
       /**
        * Loads the data for the purchase report.
        */
       let move_lines = ''
       try {
           if(wizard_id == null){
               this.state.wizard_id = await this.orm.create("dynamic.balance.report",[{}]);
               }
           this.state.data = await this.orm.call("dynamic.balance.report", "balance_report", [this.state.wizard_id]);
           $.each(this.state.data, function (index, value) {
               move_lines = value
           })
           this.state.balance_report_line = move_lines
       }
       catch (el) {
           window.location.href
       }
   }
   async applyFilter(ev) {
       let filter_data = {}
       filter_data.date_from = this.start_date.el.value
       filter_data.date_to = this.end_date.el.value
       filter_data.main_head = this.main_head.el.value
       filter_data.department_id = this.department_id.el.value
       filter_data.section_id = this.section_id.el.value
       filter_data.project_id = this.project_id.el.value
       filter_data.account_id = this.account_id.el.value
       let data = await this.orm.write("dynamic.balance.report",this.state.wizard_id, filter_data);
       this.load_data(this.state.wizard_id)
   }
//   viewPurchaseOrder(ev){
//   return this.action.doAction({
//           type: "ir.actions.act_window",
//           res_model: 'purchase.order',
//           res_id: parseInt(ev.target.id),
//           views: [[false, "form"]],
//           target: "current",
//       });
//   }
     async print_xlsx() {
       /**
        * Generates and downloads an XLSX report for the purchase orders.
        */
       var data = this.state.data
       var action = {
               'data': {
                  'model': 'dynamic.balance.report',
                  'options': JSON.stringify(data['orders']),
                  'output_format': 'xlsx',
                  'report_data': JSON.stringify(data['report_lines']),
                  'report_name': `${data.main_head} Report`,
                  'dfr_data': JSON.stringify(data),
               },
            };
       this.uiService.block();
       await download({
           url: '/dynamic_balance_xlsx_reports',
           data: action.data,
           complete: this.uiService.unblock(),
           error: (error) => this.call('crash_manager', 'rpc_error', error),
         });
       }
   }
DynamicBalanceReport.template = 'BalanceReport';
actionRegistry.add("balance_report", DynamicBalanceReport);
