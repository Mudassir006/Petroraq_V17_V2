/** @odoo-module */
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { TimeOffEmpCard, EmpDepartmentCard, SimpleLeaveSummaryCard } from "./time_off_emp_card";

export class LeaveManagementDashboardAction extends Component {
    setup() {
        this.orm = useService("orm");
        this.currentEmployee = useState({ data: {} });
        this.currentAbsentees = useState({ data: [] });
        this.currentShift = useState({ data: false });
        this.upcomingHolidays = useState({ data: [] });

        onWillStart(async () => {
            const context = {
                ...(this.props.action?.context || {}),
                show_all_leave_dashboard: true,
            };
            this.currentEmployee.data = await this.orm.call("hr.leave", "get_current_employee", [], { context });
            this.currentAbsentees.data = await this.orm.call("hr.leave", "get_absentees", [], { context });
            this.currentShift.data = await this.orm.call("hr.leave", "get_current_shift", [], { context });
            this.upcomingHolidays.data = await this.orm.call("hr.leave", "get_upcoming_holidays", [], { context });
        });
    }
}

LeaveManagementDashboardAction.template = "de_hr_workspace_leave_management.LeaveManagementDashboardAction";
LeaveManagementDashboardAction.components = { TimeOffEmpCard, EmpDepartmentCard, SimpleLeaveSummaryCard };

registry.category("actions").add("de_hr_workspace_leave_management.leave_dashboard", LeaveManagementDashboardAction);