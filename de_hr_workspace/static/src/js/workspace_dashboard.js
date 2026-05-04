/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

class WorkspaceDashboard extends Component {
    static template = "de_hr_workspace.WorkspaceDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            tiles: [],
            loading: true,
            userName: session.user_name || session.name || session.username || "",
        });

        onWillStart(async () => {
            await this.loadTiles();
        });
    }

    async loadTiles() {
        this.state.loading = true;
        this.state.tiles = await this.orm.call("de.hr.workspace.dashboard.service", "get_tiles", []);
        this.state.loading = false;
    }

    openTile(ev) {
        const actionId = Number(ev.currentTarget.dataset.actionId || 0);
        if (actionId) {
            this.action.doAction(actionId);
        }
    }

    async refresh() {
        await this.loadTiles();
    }

    get salutation() {
        const hour = new Date().getHours();
        if (hour < 12) return "Good Morning";
        if (hour < 17) return "Good Afternoon";
        return "Good Evening";
    }

    get greetingText() {
        const name = (this.state.userName || "").trim();
        return name ? `${this.salutation}, ${name}` : this.salutation;
    }

    iconBoxClass(tile) {
        return `de-dashboard-icon-box de-tone-${tile.tone || "primary"}`;
    }
}

registry.category("actions").add("de_hr_workspace.workspace_dashboard", WorkspaceDashboard);
