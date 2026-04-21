/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { TimeOffDashboard } from '@hr_holidays/dashboard/time_off_dashboard';
import { TimeOffCard } from '@hr_holidays/dashboard/time_off_card';
import { TimeOffEmpCard } from './time_off_emp_card';
import { TimeOffEmpOrgChart } from './emp_org_chart';
import { EmpDepartmentCard } from './time_off_emp_card';
import { ApprovalStatusCard } from './time_off_emp_card';
import { PeriodAbsenteesCard } from './time_off_emp_card';
import { LeaveCategoryCard } from './time_off_emp_card';
import { LeaveTypeMetricsCard } from './time_off_emp_card';
import { LeaveAvailabilityCard } from './time_off_emp_card';
import { CurrentLeaveBalanceCard } from './time_off_emp_card';
import { SimpleLeaveSummaryCard } from './time_off_emp_card';
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

//The code is a patch that modifies the loadDashboardData method of the TimeOffDashboard class.
patch(TimeOffDashboard.prototype,{

    setup() {
        super.setup();
         this.userService = useService('user');
        this.currentEmployee = useState({
            data: {}

        })
         this.currentAbsentees = useState({
            data: {}

        })
        this.currentShift = useState({
            data: {}

        })
        this.upcoming_holidays = useState({
            data: {}

        })

        onWillStart(async() => {
            await this.userService.hasGroup('hr_holidays.group_hr_holidays_manager').then(hasGroup => {
                this.manager = hasGroup;
            })
            const dashboardContext = {
                employee_id: this.props.employeeId,
                show_all_leave_dashboard: true,
            };
            this.currentEmployee.data = await this.orm.call(
            'hr.leave',
            'get_current_employee',
            [],
            {
                context: dashboardContext,
            }
        );
         this.currentAbsentees.data = await this.orm.call(
            'hr.leave',
            'get_absentees',
            [],
            {
                context: dashboardContext,
            }

        );
         this.currentShift.data = await this.orm.call(
            'hr.leave',
            'get_current_shift',
            [],
            {
                context: dashboardContext,
            }
        );
         this.upcoming_holidays.data = await this.orm.call(
            'hr.leave',
            'get_upcoming_holidays',
            [],
            {
                context: dashboardContext,
            }
        );
         this.approval_status_count = await this.orm.call(
            'hr.leave',
            'get_approval_status_count',
            [this.currentEmployee.data.id],
            {
                context: dashboardContext,
            }
        );
          this.all_validated_leaves = await this.orm.call(
            'hr.leave',
            'get_all_validated_leaves',
            [],
            {
                context: dashboardContext,
            }
        );
        if (this.props.employeeId == null) {
            this.props.employeeId = this.currentEmployee.data.id;
        }

        })
    },
});
TimeOffDashboard.components = { ...TimeOffDashboard.components, TimeOffCard, TimeOffEmpCard ,TimeOffEmpOrgChart, EmpDepartmentCard, ApprovalStatusCard, PeriodAbsenteesCard, LeaveCategoryCard, LeaveTypeMetricsCard, LeaveAvailabilityCard, CurrentLeaveBalanceCard, SimpleLeaveSummaryCard};
