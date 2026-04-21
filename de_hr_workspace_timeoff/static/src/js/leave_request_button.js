/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
export class LeaveRequestListController extends ListController {
   setup() {
       super.setup();
   }
   async OnRequestClick() {
       let base_url;
       console.log(base_url, "Base URL Before")
       await this.orm.call("hr.leave", "get_our_base_url", []).then((result) => {
           base_url = result;
           console.log(base_url, "Base URL")
        });
       this.actionService.doAction({
          type: 'ir.actions.act_url',
//          url: 'http://localhost:11771/leave_request',
//          url: 'https://uat1.odoo.com/leave_request',
          url: `${base_url}/leave_request`,
          target: 'new',
      });
   }
}
registry.category("views").add("leave_request_button_in_tree", {
   ...listView,
   Controller: LeaveRequestListController,
   buttonTemplate: "button_leave_request.ListView.Buttons",
});