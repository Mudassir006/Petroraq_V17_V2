/* @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
export class TimeOffEmpCard extends Component {}
TimeOffEmpCard.template = 'de_hr_workspace_leave_management.TimeOffEmpCard';
TimeOffEmpCard.props = ['name', 'id', 'department_id', 'job_position',
'children', 'image_1920', 'work_email', 'work_phone', 'company', 'resource_calendar_id', 'employee_code', 'joining_date'];
//Exports a class TimeOffEmpOrgChart that extends the Component class.
//It is a custom component used for managing an employee organization
//chart in the context of time off and holidays.
export class TimeOffEmpOrgChart extends Component {
    setup() {
         super.setup();
        this.props;
        this.userService = useService('user');
          onWillStart(async () => {
            this.manager = await this.userService.hasGroup("hr_holidays.group_hr_holidays_manager");
        });

    }
}
TimeOffEmpOrgChart.template = 'de_hr_workspace_leave_management.hr_org_chart';
TimeOffEmpOrgChart.props = ['name', 'id', 'department_id', 'job_position', 'children'];
export class EmpDepartmentCard extends Component {}
EmpDepartmentCard.template = 'de_hr_workspace_leave_management.EmpDepartmentCard';
EmpDepartmentCard.props = ['name', 'id', 'department_id', 'child_all_count',
'children', 'absentees', 'current_shift', 'upcoming_holidays'];
//Exports a class ApprovalStatusCard that extends the Component class.
//It is a custom component used for managing the approval status of
//a card, possibly related to HR leave requests.
export class ApprovalStatusCard extends Component {
        setup() {
         super.setup();
          this.userService = useService('user');
        this.props;

         onWillStart(async () => {
            await this.userService.hasGroup('hr_holidays.group_hr_holidays_manager').then(hasGroup => {
                this.manager = hasGroup;
            })
    });
}
}
ApprovalStatusCard.template = 'de_hr_workspace_leave_management.ApprovalStatusCard';
ApprovalStatusCard.props = ['id','name','approval_status_count','child_ids',
'children', 'all_validated_leaves'];

export class PeriodAbsenteesCard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.state = useState({
            duration: 'this_month',
            rows: [],
        });
        onWillStart(async () => {
            await this.loadRows();
        });
    }

    async loadRows() {
        const rows = await this.orm.call(
            'hr.leave',
            'get_period_absentees',
            [this.state.duration],
            {
                context: {
                    employee_id: this.props.id,
                    show_all_leave_dashboard: true,
                },
            }
        );
        this.state.rows = rows.map((row, index) => ({ ...row, row_key: `${row.employee_id || 0}-${index}` }));
    }

    async onChangeDuration(ev) {
        this.state.duration = ev.target.value;
        await this.loadRows();
    }

    exportPdf() {
        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "de_hr_workspace_leave_management.period_absentees_pdf",
            report_file: "de_hr_workspace_leave_management.period_absentees_pdf",
            data: {
                duration: this.state.duration,
            },
        });
    }

    exportXlsx() {
        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "xlsx",
            report_name: "de_hr_workspace_leave_management.period_absentees_xlsx",
            report_file: "period_absentees",
            data: {
                duration: this.state.duration,
            },
        });
    }
}
PeriodAbsenteesCard.template = 'de_hr_workspace_leave_management.PeriodAbsenteesCard';
PeriodAbsenteesCard.props = ['id'];

export class LeaveCategoryCard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.state = useState({
            duration: 'this_month',
            rows: [],
        });
        onWillStart(async () => {
            await this.loadRows();
        });
    }

    async loadRows() {
        const rows = await this.orm.call('hr.leave', 'get_period_leaves', [this.state.duration, this.props.category], {
            context: { employee_id: this.props.id, show_all_leave_dashboard: true },
        });
        this.state.rows = rows.map((row, index) => ({ ...row, row_key: `${row.employee_id || 0}-${index}` }));
    }

    async onChangeDuration(ev) {
        this.state.duration = ev.target.value;
        await this.loadRows();
    }

    exportPdf() {
        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "de_hr_workspace_leave_management.period_absentees_pdf",
            report_file: "de_hr_workspace_leave_management.period_absentees_pdf",
            data: { duration: this.state.duration },
        });
    }

    exportXlsx() {
        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "xlsx",
            report_name: "de_hr_workspace_leave_management.period_absentees_xlsx",
            report_file: "period_absentees",
            data: { duration: this.state.duration },
        });
    }
}
LeaveCategoryCard.template = 'de_hr_workspace_leave_management.LeaveCategoryCard';
LeaveCategoryCard.props = ['id', 'category', 'title'];

export class LeaveTypeMetricsCard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.state = useState({
            duration: 'this_month',
            rows: [],
        });
        onWillStart(async () => {
            await this.loadRows();
        });
    }

    async loadRows() {
        this.state.rows = await this.orm.call('hr.leave', 'get_period_leave_type_metrics', [this.state.duration], {
            context: { employee_id: this.props.id, show_all_leave_dashboard: true },
        });
    }

    async onChangeDuration(ev) {
        this.state.duration = ev.target.value;
        await this.loadRows();
    }

    openExportWizard() {
        return this.actionService.doAction('de_hr_workspace_leave_management.action_dashboard_export_wizard');
    }
}
LeaveTypeMetricsCard.template = 'de_hr_workspace_leave_management.LeaveTypeMetricsCard';
LeaveTypeMetricsCard.props = ['id'];

export class LeaveAvailabilityCard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useState({ rows: [] });
        onWillStart(async () => {
            this.state.rows = await this.orm.call('hr.leave', 'get_leave_availability_summary', [], {
                context: { employee_id: this.props.id, show_all_leave_dashboard: true },
            });
        });
    }
}
LeaveAvailabilityCard.template = 'de_hr_workspace_leave_management.LeaveAvailabilityCard';
LeaveAvailabilityCard.props = ['id'];

export class CurrentLeaveBalanceCard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useState({ rows: [] });
        onWillStart(async () => {
            this.state.rows = await this.orm.call('hr.leave', 'get_current_employee_leave_breakdown', [], {
                context: { employee_id: this.props.id, show_all_leave_dashboard: true },
            });
        });
    }
}
CurrentLeaveBalanceCard.template = 'de_hr_workspace_leave_management.CurrentLeaveBalanceCard';
CurrentLeaveBalanceCard.props = ['id'];

export class LeaveRequestCountCard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useState({
            duration: 'this_month',
            employee_id: '',
            employee_search: '',
            leave_type_id: '',
            date_from: '',
            date_to: '',
            employees: [],
            leave_types: [],
            total_requests: 0,
            total_days: 0,
        });
        onWillStart(async () => {
            const options = await this.orm.call('hr.leave', 'get_leave_request_filter_options', [], {
                context: { show_all_leave_dashboard: true },
            });
            this.state.employees = options.employees || [];
            this.state.leave_types = options.leave_types || [];
            await this.loadMetrics();
        });
    }

    employeeLabel(employee) {
        const code = employee?.code || employee?.employee_code || '';
        return code ? `${code} - ${employee.name}` : (employee?.name || '');
    }

    async loadMetrics() {
        const result = await this.orm.call(
            'hr.leave',
            'get_leave_request_count_by_filters',
            [
                this.state.duration,
                this.state.employee_id || false,
                this.state.leave_type_id || false,
                this.state.date_from || false,
                this.state.date_to || false,
            ],
            { context: { show_all_leave_dashboard: true } }
        );
        this.state.total_requests = result.total_requests || 0;
        this.state.total_days = result.total_days || 0;
    }

    async onDurationChange(ev) {
        this.state.duration = ev.target.value;
        await this.loadMetrics();
    }

    async onEmployeeChange(ev) {
        this.state.employee_id = ev.target.value;
        await this.loadMetrics();
    }

    async onEmployeeSearchInput(ev) {
        const value = (ev.target.value || '').trim();
        this.state.employee_search = value;
        if (!value) {
            this.state.employee_id = '';
            await this.loadMetrics();
            return;
        }
        const normalized = value.toLowerCase();
        const matchedEmployee = this.state.employees.find((employee) => {
            const code = (employee.code || '').toLowerCase();
            return this.employeeLabel(employee).toLowerCase() === normalized || code === normalized;
        });
        if (matchedEmployee) {
            this.state.employee_id = matchedEmployee.id;
            await this.loadMetrics();
        }
    }

    async onLeaveTypeChange(ev) {
        this.state.leave_type_id = ev.target.value;
        await this.loadMetrics();
    }

    async onDateFromChange(ev) {
        this.state.date_from = ev.target.value;
        await this.loadMetrics();
    }

    async onDateToChange(ev) {
        this.state.date_to = ev.target.value;
        await this.loadMetrics();
    }
}
LeaveRequestCountCard.template = 'de_hr_workspace_leave_management.LeaveRequestCountCard';
LeaveRequestCountCard.props = ['id'];

export class SimpleLeaveSummaryCard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.state = useState({
            employee_id: this.props.id,
            employee_search: '',
            duration: 'current_contract',
            date_from: '',
            date_to: '',
            lines: [],
            employee_name: '',
            employee_profile: {},
        });
        onWillStart(async () => {
            const selected = this.employeeOptions.find((employee) => employee.id === this.state.employee_id);
            if (selected) {
                this.state.employee_search = this.employeeLabel(selected);
            }
            await this.loadSummary();
        });
    }

    get employeeOptions() {
        return this.props.employees || [];
    }

    employeeLabel(employee) {
        const code = employee?.code || employee?.employee_code || '';
        return code ? `${code} - ${employee.name}` : (employee?.name || '');
    }

    async loadSummary() {
        if (!this.state.employee_id && this.employeeOptions.length) {
            this.state.employee_id = this.employeeOptions[0].id;
        }
        if (!this.state.employee_id) {
            this.state.lines = [];
            this.state.employee_name = '';
            this.state.employee_profile = {};
            return;
        }
        const result = await this.orm.call(
            'hr.leave',
            'get_employee_leave_simple_summary',
            [
                this.state.employee_id,
                this.state.duration,
                this.state.date_from || false,
                this.state.date_to || false,
            ],
            { context: { show_all_leave_dashboard: true } }
        );
        this.state.lines = result.lines || [];
        this.state.employee_name = result.employee_name || '';
        this.state.employee_profile = result.employee_profile || {};
    }

    async onEmployeeChange(ev) {
        this.state.employee_id = parseInt(ev.target.value, 10);
        await this.loadSummary();
    }

    async onDurationChange(ev) {
        this.state.duration = ev.target.value;
        if (this.state.duration !== 'custom') {
            this.state.date_from = '';
            this.state.date_to = '';
        }
        await this.loadSummary();
    }

    async onDateFromChange(ev) {
        this.state.date_from = ev.target.value;
        await this.loadSummary();
    }

    async onDateToChange(ev) {
        this.state.date_to = ev.target.value;
        await this.loadSummary();
    }

    async onEmployeeSearchInput(ev) {
        const value = (ev.target.value || '').trim();
        this.state.employee_search = value;
        if (!value) {
            this.state.employee_id = false;
            this.state.lines = [];
            this.state.employee_name = '';
            this.state.employee_profile = {};
            return;
        }
        const normalized = value.toLowerCase();
        const matchedEmployee = this.employeeOptions.find((employee) => {
            const code = (employee.code || '').toLowerCase();
            return this.employeeLabel(employee).toLowerCase() === normalized || code === normalized;
        });
        if (matchedEmployee && matchedEmployee.id !== this.state.employee_id) {
            this.state.employee_id = matchedEmployee.id;
            await this.loadSummary();
        }
    }

    _todayISO() {
        return new Date().toISOString().slice(0, 10);
    }

    _computeSummaryRange() {
        const today = this._todayISO();
        let start = null;
        let end = today;

        if (this.state.duration === "custom" && this.state.date_from && this.state.date_to) {
            start = this.state.date_from;
            end = this.state.date_to;
        } else if (this.state.duration === "this_year") {
            const year = new Date().getFullYear();
            start = `${year}-01-01`;
        } else if (this.state.duration === "this_month") {
            const now = new Date();
            const month = `${now.getMonth() + 1}`.padStart(2, "0");
            start = `${now.getFullYear()}-${month}-01`;
        } else {
            start = this.state.employee_profile.current_contract_start_date || `${new Date().getFullYear()}-01-01`;
        }

        return { start, end };
    }

    openLeaveRequests(line) {
        if (!this.state.employee_id || !line?.leave_type_id) {
            return;
        }
        const { start, end } = this._computeSummaryRange();
        const domain = [
            ["employee_id", "=", this.state.employee_id],
            ["holiday_status_id", "=", line.leave_type_id],
        ];
        if (start && end) {
            domain.push(["request_date_from", "<=", end]);
            domain.push(["request_date_to", ">=", start]);
        }
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `${line.leave_type} Leave Requests`,
            res_model: "hr.leave",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            target: "current",
            domain,
            context: {
                search_default_employee_id: this.state.employee_id,
                default_employee_id: this.state.employee_id,
                default_holiday_status_id: line.leave_type_id,
            },
        });
    }

}
SimpleLeaveSummaryCard.template = 'de_hr_workspace_leave_management.SimpleLeaveSummaryCard';
SimpleLeaveSummaryCard.props = ['id', 'employees'];