/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

/**
 * Add bottom pager support to ListRenderer (Odoo 17 syntax)
 */
patch(ListRenderer.prototype, {
    patchName: "pr_account_bottom_pager",

    getBottomPagerProps() {
        const list = this.props.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: this.onBottomPagerUpdate.bind(this),
            withAccessKey: false,
        };
    },

    async onBottomPagerUpdate({ offset, limit }) {
        await this.props.list.load({ limit, offset });
        this.render(true);
    },
});
