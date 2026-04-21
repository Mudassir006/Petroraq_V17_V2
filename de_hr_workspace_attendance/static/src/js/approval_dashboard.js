/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

class ApprovalDashboard extends Component {
    static template = "de_hr_workspace_attendance.ApprovalDashboard";

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
        const tiles = await this.orm.call("de.hr.approval.dashboard.service", "get_tiles", []);
        this.state.tiles = tiles.map((tile) => ({ ...tile, gradient: this.randomGradient() }));
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
        if (hour < 12) {
            return "Good Morning";
        }
        if (hour < 17) {
            return "Good Afternoon";
        }
        return "Good Evening";
    }

    get greetingText() {
        const name = (this.state.userName || "").trim();
        return name ? `${this.salutation}, Mr. ${name}` : this.salutation;
    }


    randomGradient() {
        const gradients = [
            ["#2F4858", "#122AA0"],
            ["#2C302E", "#474A48"],
            ["#07004D", "#2D82B7"],
            ["#1B4079", "#4D7C8A"],
            ["#122AA0", "#657153"],
            ["#5CC8FF", "#122AA0"],
            ["#1D2F6F", "#F88DAD"],
            ["#4D5057", "#4E6E5D"],
            ["#593C8F", "#171738"],
            ["#122AA0", "#2AB7CA"],
            ["#122AA0", "#AF7A6D"],
            ["#B33951", "#54494B"],
            ["#4C2A85", "#253C78"],
        ];
        const [fromColor, toColor] = gradients[Math.floor(Math.random() * gradients.length)];
        return `linear-gradient(135deg, ${fromColor}, ${toColor})`;
    }

    tileStyle(tile) {
        return tile.gradient ? `background: ${tile.gradient};` : "";
    }

    tileClass(tile) {
        return `de-dashboard-tile de-dashboard-tile-${tile.tone || "primary"}`;
    }
}

registry.category("actions").add("de_hr_workspace_attendance.approval_dashboard", ApprovalDashboard);