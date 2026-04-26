/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class PayrollBatchXlsxReport extends Component {
    static template = "pr_hr_payroll.PayrollBatchXlsxReport";
    static props = {
        record: Object,
        readonly: { type: Boolean, optional: true },
        // allow unknown props without crashing
        "*": true,
    };

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            loading: true,
            error: null,
            slips: [],
            linesBySlipId: new Map(),
            columns: [],     // [{code, name, hidden}]
            rows: [],        // [{emp_code, emp_name, dept, valsByCode}]
            totals: new Map(),// code -> sum
            sortField: "emp_code",
            sortAsc: true,
        });

        onWillStart(async () => {
            try {
                await this._load();
            } catch (e) {
                this.state.error = (e && e.message) ? e.message : String(e);
            } finally {
                this.state.loading = false;
            }
        });
    }

    // ===== CONFIG: same as your XLSX =====
    get RULE_NAME_ORDER() {
        return [
            "Basic Salary",
            "Accommodation",
            "Transportation",
            "Food",
            "Fixed Overtime",
            "Overtime",
            "Annual Time Off DED",
            "Sick Time Off DED",
            "Annual Time Off",
            "Sick Time Off",
            "Absence",
            "Late In",
            "Unpaid Leave",
            "Early Checkout",
            "Gross",
            "Advance Allowances",
            "Net Salary",
        ];
    }

    get EXTRA_COLS() {
        return [
            { code: "GOSI_COMP_ADD", name: "GOSI Company Contribution" },
            { code: "GOSI_EMP", name: "GOSI Employee Deduction" },
            { code: "GOSI_COMP_DED", name: "GOSI Company Deduction" },
        ];
    }

    get HIDE_CODES() {
        return new Set(["GOSI", "GOSI_COMP_ADD", "GOSI_EMP", "GOSI_COMP_DED"]);
    }

    // Header info from batch record
    get batch() {
        return this.props.record.data;
    }

    get companyName() {
        // many2one in form renderer is usually [id, display_name]
        const c = this.batch.company_id;
        if (Array.isArray(c)) return c[1];
        return "";
    }

    formatDateLong(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "long",
        year: "numeric",
    });
}

formatMonthYear(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-GB", {
        month: "long",
        year: "numeric",
    });
}

    get dateStart() {
    return this.formatDateLong(this.batch.date_start);
}

get dateEnd() {
    return this.formatDateLong(this.batch.date_end);
}
get payrollMonth() {
    return this.formatMonthYear(this.batch.date_end);
}


    // ===== Loader =====
    async _load() {
        const batchId = this.props.record.resId;
        if (!batchId) {
            throw new Error("Batch not saved yet (no id). Save the batch first.");
        }

        // 1) Load payslips in this batch
        const slips = await this.orm.searchRead(
            "hr.payslip",
            [["payslip_run_id", "=", batchId]],
            ["id", "employee_id", "struct_id", "date_from", "date_to"]
        );

        const slipIds = slips.map(s => s.id);
        if (!slipIds.length) {
            this.state.slips = [];
            this.state.columns = this._buildColumns([], new Map());
            this.state.rows = [];
            this.state.totals = new Map();
            return;
        }

        // 2) Load all lines for those slips (one RPC, fast)
        const lines = await this.orm.searchRead(
            "hr.payslip.line",
            [["slip_id", "in", slipIds]],
            ["id", "slip_id", "name", "code", "amount", "total"]
        );

        // Build linesBySlipId
        const linesBySlipId = new Map();
        for (const l of lines) {
            const sid = Array.isArray(l.slip_id) ? l.slip_id[0] : l.slip_id;
            if (!linesBySlipId.has(sid)) linesBySlipId.set(sid, []);
            linesBySlipId.get(sid).push(l);
        }

        // 3) Build columns (same rule ordering as XLSX)
        const columns = await this._buildColumns(slips);

        // 4) Build rows (matrix)
        const rows = [];
        const totals = new Map();

        for (const slip of slips) {
            const emp = slip.employee_id; // [id, name]
            const empId = Array.isArray(emp) ? emp[0] : null;

            // Load employee code + department in one go (per slip) is heavy.
            // Better: batch read all employees once.
            // We'll do it optimized:
            // collect all employee ids then one searchRead.
        }

        // ---- Optimize employee fetch ----
        const employeeIds = [...new Set(slips.map(s => (Array.isArray(s.employee_id) ? s.employee_id[0] : null)).filter(Boolean))];
        const employees = await this.orm.searchRead(
            "hr.employee",
            [["id", "in", employeeIds]],
            ["id", "name", "code", "department_id"]
        );
        const empMap = new Map(employees.map(e => [e.id, e]));

        // Now build each row values by code
        for (const slip of slips) {
            const sid = slip.id;
            const emp = Array.isArray(slip.employee_id) ? slip.employee_id : [null, ""];
            const empRec = empMap.get(emp[0]) || {};
            const dept = Array.isArray(empRec.department_id) ? empRec.department_id[1] : "";

            const valsByCode = new Map();
            const slipLines = linesBySlipId.get(sid) || [];

            // Your XLSX used l.amount; keep same. (If you want total instead, swap to l.total)
            for (const ln of slipLines) {
                const code = ln.code || "";
                const v = Number(ln.amount || 0);
                valsByCode.set(code, (valsByCode.get(code) || 0) + v);
            }

            // Ensure all columns exist even if missing
            for (const col of columns) {
                if (!valsByCode.has(col.code)) valsByCode.set(col.code, 0);
            }

            this._recomputeGrossAndNet(valsByCode, columns);

            // Accumulate totals
            for (const col of columns) {
                const v = valsByCode.get(col.code) || 0;
                totals.set(col.code, (totals.get(col.code) || 0) + v);
            }

            rows.push({
                emp_id: emp[0] || 0,
                emp_code: empRec.code || "",
                emp_name: empRec.name || emp[1] || "",
                dept: dept || "",
                valsByCode,
            });
        }

        this._sortRows(rows);

        this.state.slips = slips;
        this.state.linesBySlipId = linesBySlipId;
        this.state.columns = columns;
        this.state.rows = rows;
        this.state.totals = totals;
    }

    _compareEmployeeCode(a, b, direction) {
        const aCode = (a.emp_code || "").toString().trim();
        const bCode = (b.emp_code || "").toString().trim();

        const aNum = Number(aCode);
        const bNum = Number(bCode);
        const aIsNum = !Number.isNaN(aNum) && aCode !== "";
        const bIsNum = !Number.isNaN(bNum) && bCode !== "";

        if (aIsNum && bIsNum) {
            if (aNum === bNum) return 0;
            return aNum > bNum ? direction : -direction;
        }

        return aCode.localeCompare(bCode, undefined, { numeric: true }) * direction;
    }

    _sortRows(rows) {
        const direction = this.state.sortAsc ? 1 : -1;
        const sortField = this.state.sortField;
        rows.sort((a, b) => {
            if (sortField === "emp_code") {
                return this._compareEmployeeCode(a, b, direction);
            }

            const aVal = Number(a.valsByCode.get(sortField) || 0);
            const bVal = Number(b.valsByCode.get(sortField) || 0);
            if (aVal === bVal) {
                return this._compareEmployeeCode(a, b, 1);
            }
            return aVal > bVal ? direction : -direction;
        });
    }

    _recomputeGrossAndNet(valsByCode, columns) {
        const codeByName = new Map(columns.map(c => [c.name, c.code]));
        const val = (name) => Number(valsByCode.get(codeByName.get(name)) || 0);

        const gosiCompanyAdd = Math.abs(Number(valsByCode.get("GOSI_COMP_ADD") || 0));
        const gosiCompanyDed = Math.abs(Number(valsByCode.get("GOSI_COMP_DED") || 0));
        const gosiEmployeePortion = Math.abs(Number(valsByCode.get("GOSI_EMP") || 0));
        const gosiCompanyPortion = gosiCompanyAdd + gosiCompanyDed;

        const computedGross =
            val("Basic Salary") +
            val("Accommodation") +
            val("Transportation") +
            val("Food") +
            val("Fixed Overtime") +
            val("Overtime") +
            val("Annual Time Off DED") +
            val("Sick Time Off DED") +
            val("Annual Time Off") +
            val("Sick Time Off") +
            val("Absence") +
            val("Late In") +
            val("Unpaid Leave") +
            val("Early Checkout") +
            gosiCompanyPortion;

        const grossCode = codeByName.get("Gross");
        if (grossCode) valsByCode.set(grossCode, computedGross);

        const computedNet =
            computedGross -
            Math.abs(val("Advance Allowances")) -
            (gosiCompanyPortion + gosiEmployeePortion);

        const netCode = codeByName.get("Net Salary");
        if (netCode) valsByCode.set(netCode, computedNet);
    }

    toggleSort(field) {
        if (this.state.sortField === field) {
            this.state.sortAsc = !this.state.sortAsc;
        } else {
            this.state.sortField = field;
            this.state.sortAsc = true;
        }
        this._sortRows(this.state.rows);
    }

    getSortIcon(field) {
        if (this.state.sortField !== field) {
            return "↓";
        }
        return this.state.sortAsc ? "↑" : "↓";
    }

async _buildColumns(slips) {
    // Get salary rule codes by NAME (stable)
    const rules = await this.orm.searchRead(
        "hr.salary.rule",
        [["name", "in", this.RULE_NAME_ORDER]],
        ["name", "code"]
    );
    const nameToCode = new Map(rules.map(r => [r.name, r.code]));

    const cols = [];
    for (const ruleName of this.RULE_NAME_ORDER) {
        const code = nameToCode.get(ruleName);
        // if not found, keep a safe fallback but mark it obvious for debugging
        cols.push({
            code: code || `__MISSING__${ruleName}`,
            name: ruleName,
            hidden: this.HIDE_CODES.has(code),
        });
    }

    for (const ex of this.EXTRA_COLS) {
        cols.push({
            code: ex.code,
            name: ex.name,
            hidden: this.HIDE_CODES.has(ex.code),
        });
    }

    return cols;
}

    money(v) {
        const n = Number(v || 0);
        return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    cellClass(v) {
        const n = Number(v || 0);
        return n < 0 ? "pr_money_neg" : "pr_money_pos";
    }
}

registry.category("view_widgets").add("payroll_batch_xlsx_report", {
    component: PayrollBatchXlsxReport,
});