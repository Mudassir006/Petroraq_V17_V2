/** @odoo-module **/

import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { jsonrpc as rpc } from "@web/core/network/rpc_service";

class CustomLeaveDashboard extends Component {
    setup() {
        this.state = useState({
            summary: [],
            LeavesHistory: [],
            pendingApprovals: [],
            chartData: null,
        });

        this.orm = useService("orm");
        this.chartRef = useRef("leaveChart");
        this._fetchDashboardData();

        onMounted(async () => {
            await this.render_graphs();
        });
    }

    async _fetchDashboardData() {
        var rpc = this.env.services.rpc
        var custom_data = {}
        console.log(rpc,"rpc")
        var data = await rpc('/get_dashboard_data', {
            model: 'hr.leave',
            method: 'get_dashboard_data',
            args:[],
        }).then(res =>{
            custom_data = res;
        });
        console.log(custom_data, "DATA")
        this.state.summary = (custom_data.summary || []).filter(Boolean);
        this.state.LeavesHistory = (custom_data.all_leaves || []).filter(Boolean);
        this.state.pendingApprovals = (custom_data.pending || []).filter(Boolean);
        this.state.chartData = custom_data.chart;
    }

    render_graphs(){
        this.get_taken_leaves();
    }

    get_taken_leaves(){
        this.orm.call("hr.leave", "get_taken_leaves", []).
        then((result) => {
            console.log(result,"result chart")
            var ctx = this.chartRef.el;
            var name = Object.keys(result);
            var count = Object.values(result);
            console.log(name,"name")
            console.log(count,"count")
            var myChart = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: name,
                    datasets: [
                        {
                            label: "Taken Leaves",
                            data: count,
                            backgroundColor: "#007bff",
                            borderRadius: 5,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                        },
                    },
                },
            });
        });
    }

//    renderChart(data) {
//        const ctx = this.el.querySelector("#leaveChart");
//        console.log(ctx, "ctx")
//        if (!ctx) return;
//        new Chart(ctx, {
//            type: "bar",
//            data: {
//                labels: data.labels,
//                datasets: [
//                    {
//                        label: "Leave Requests",
//                        data: data.values,
//                        backgroundColor: "#007bff",
//                        borderRadius: 5,
//                    },
//                ],
//            },
//            options: {
//                responsive: true,
//                scales: {
//                    y: {
//                        beginAtZero: true,
//                    },
//                },
//            },
//        });
//    }
}

CustomLeaveDashboard.template = 'de_hr_workspace_timeoff.CustomLeaveDashboard';
registry.category('actions').add('de_hr_workspace_timeoff.CustomLeaveDashboard', CustomLeaveDashboard);
