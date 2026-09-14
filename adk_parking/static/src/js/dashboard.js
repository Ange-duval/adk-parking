/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { formatMonetary } from "@web/views/fields/formatters";
import { Component, onWillStart, onMounted, useRef, useState } from "@odoo/owl";

export class AdkParkingDashboard extends Component {
    static template = "adk_parking.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.chartRef = useRef("chartCanvas");
        this.state = useState({
            parkingCount: 0,
            occupationRate: 0,
            availableToday: 0,
            amountDue: 0,
            revenueTotal: 0,
            currencySymbol: "",
            free: 0,
            employee: 0,
            client: 0,
            loading: true,
        });

        onWillStart(async () => {
            await Promise.all([
                loadJS("/web/static/lib/Chart/Chart.js"),
                this.loadData(),
            ]);
        });

        onMounted(() => {
            this.renderChart();
        });
    }

    async loadData() {
        const parkings = await this.orm.searchRead(
            "adk.parking",
            [],
            ["name", "total_places", "reserved_places", "available_places",
             "reserved_employee", "reserved_client", "amount_due", "revenue_total", "currency_id"]
        );

        const totalPlaces = parkings.reduce((s, p) => s + p.total_places, 0);
        const totalReserved = parkings.reduce((s, p) => s + p.reserved_places, 0);
        const totalAvailable = parkings.reduce((s, p) => s + p.available_places, 0);
        const totalEmployee = parkings.reduce((s, p) => s + p.reserved_employee, 0);
        const totalClient = parkings.reduce((s, p) => s + p.reserved_client, 0);
        const totalDue = parkings.reduce((s, p) => s + p.amount_due, 0);
        const totalRevenue = parkings.reduce((s, p) => s + p.revenue_total, 0);

        this.state.parkingCount = parkings.length;
        this.state.occupationRate = totalPlaces ? Math.round((totalReserved / totalPlaces) * 1000) / 10 : 0;
        this.state.availableToday = totalAvailable;
        this.state.amountDue = totalDue;
        this.state.revenueTotal = totalRevenue;
        this.state.free = totalAvailable;
        this.state.employee = totalEmployee;
        this.state.client = totalClient;
        this.state.loading = false;
    }

    formatAmount(value) {
        return formatMonetary(value || 0, {});
    }

    renderChart() {
        if (!this.chartRef.el || typeof Chart === "undefined") {
            return;
        }
        const ctx = this.chartRef.el.getContext("2d");
        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Libres", "Réservées Personnel", "Réservées Clients"],
                datasets: [{
                    data: [this.state.free, this.state.employee, this.state.client],
                    backgroundColor: ["#93E9BE", "#8AB4F8", "#F9A8A8"],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                },
                cutout: "65%",
            },
        });
    }

    openReservations() {
        this.action.doAction("adk_parking.action_adk_parking_reservation");
    }

    openParkings() {
        this.action.doAction("adk_parking.action_adk_parking");
    }

    openUnpaid() {
        this.action.doAction("adk_parking.action_adk_parking_reservation_unpaid");
    }
}

registry.category("actions").add("adk_parking_dashboard", AdkParkingDashboard);
