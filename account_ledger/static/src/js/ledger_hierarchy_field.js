/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class LedgerHierarchyField extends Component {
    static template = "account_ledger.LedgerHierarchyField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            loaded: false,
            error: null,
            rows: [],
            expanded: {},  // lineId -> bool
            byId: new Map(),
        });

        onWillStart(async () => {
            await this._loadRows();
        });
    }

    // --------------------------
    // Data loading
    // --------------------------
    async _loadRows() {
        // ✅ correct way to get current record id in Odoo 17 widgets
        const resId = this.props.record && this.props.record.resId;

        try {
            this.state.loaded = false;
            this.state.error = null;
            this.state.rows = [];
            this.state.byId = new Map();

            if (!resId) {
                // no record yet (unsaved transient etc.)
                return;
            }

            // We read a superset of fields.
            // If your model doesn't have some of them, server will error.
            // So we first try with hierarchy fields, then fallback to flat fields.
            let fields = [
                "id",
                "result_id",
                "label",
                "initial_debit",
                "initial_credit",
                "period_debit",
                "period_credit",
                "ending_debit",
                "ending_credit",
                "balance",
                "balance_type",
                // hierarchy fields (optional; add them in python to enable)
                "parent_id",
                "level",
                "is_heading",
                "sequence",
            ];

            let rows;
            try {
                rows = await this.orm.searchRead(
                    "custom.dynamic.ledger.result.line",
                    [["result_id", "=", resId]],
                    fields,
                    { order: "sequence,id" }
                );
            } catch (e) {
                // fallback: your python model might not yet have hierarchy fields
                console.warn("Hierarchy fields missing, falling back to flat read.", e);
                fields = [
                    "id",
                    "result_id",
                    "label",
                    "initial_debit",
                    "initial_credit",
                    "period_debit",
                    "period_credit",
                    "ending_debit",
                    "ending_credit",
                    "balance",
                    "balance_type",
                ];
                rows = await this.orm.searchRead(
                    "custom.dynamic.ledger.result.line",
                    [["result_id", "=", resId]],
                    fields,
                    { order: "id" }
                );
            }

            // Normalize hierarchy data if missing
            for (const r of rows) {
                if (r.level === undefined || r.level === null) r.level = 0;
                if (r.is_heading === undefined || r.is_heading === null) r.is_heading = false;
                if (r.sequence === undefined || r.sequence === null) r.sequence = 10;
                r._children = [];
            }

            // Build byId map + children lists (if parent_id is available)
            const byId = new Map(rows.map((r) => [r.id, r]));
            for (const r of rows) {
                const pid = r.parent_id && r.parent_id[0];
                if (pid && byId.has(pid)) {
                    byId.get(pid)._children.push(r.id);
                }
            }

            // Default expand headings that have children
            const expanded = {};
            for (const r of rows) {
                if (r.is_heading && r._children.length) {
                    expanded[r.id] = true;
                }
            }

            this.state.rows = rows;
            this.state.byId = byId;
            this.state.expanded = expanded;
        } catch (e) {
            console.error("LedgerHierarchyField load failed:", e);
            this.state.error = (e && (e.message || e.toString())) || "Unknown error";
        } finally {
            // ✅ prevents infinite "Loading..."
            this.state.loaded = true;
        }
    }

    // --------------------------
    // UI helpers
    // --------------------------
    toggle(row) {
        if (!row._children || !row._children.length) return;
        this.state.expanded[row.id] = !this.state.expanded[row.id];
    }

    isVisible(row) {
        // If no parent_id field in data, show everything
        if (!("parent_id" in row)) return true;

        const pid = row.parent_id && row.parent_id[0];
        if (!pid) return true;

        // All ancestors must be expanded
        let cur = pid;
        while (cur) {
            if (!this.state.expanded[cur]) return false;
            const parent = this.state.byId.get(cur);
            cur = parent && parent.parent_id ? parent.parent_id[0] : null;
        }
        return true;
    }

    indentStyle(row) {
        const lvl = row.level || 0;
        return `padding-left:${lvl * 18}px;`;
    }

    fmt(value) {
        // Simple formatter; you can switch to formatMonetary later
        const v = value || 0;
        return typeof v === "number" ? v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : v;
    }
}

registry.category("fields").add("ledger_hierarchy", {
    component: LedgerHierarchyField,
});
