/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
export class ShortageRequestListController extends ListController {
   setup() {
       super.setup();
   }
   OnRequestClick() {
       this.actionService.doAction({
          type: 'ir.actions.act_url',
          url: 'http://localhost:11771/shortage_request',
          target: 'new',
      });
   }
}
registry.category("views").add("shortage_request_button_in_tree", {
   ...listView,
   Controller: ShortageRequestListController,
   buttonTemplate: "button_shortage_request.ListView.Buttons",
});