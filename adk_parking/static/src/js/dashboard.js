/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const PLACES_COLORS = { free: "#9ccfb4", employee: "#8ec1e6", client: "#f2c48c" };
const STATE_COLORS = { draft: "#c9bfd6", confirmed: "#8ec1e6", done: "#9ccfb4", cancelled: "#ee9a9a" };
const PAY_COLORS = { paid: "#9ccfb4", not_paid: "#f2c48c", na: "#c9bfd6" };

export class AdkParkingDashboard extends Component {
    static template = "adk_parking.Dashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, parking: 0, period: "all", data: null });
        this.periods = [
            { key: "30", label: "30 jours" },
            { key: "90", label: "3 mois" },
            { key: "365", label: "12 mois" },
            { key: "all", label: "Tout" },
        ];
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("adk.parking.dashboard", "get_data", [], {
            parking_id: this.state.parking,
            period: this.state.period,
        });
        this.state.loading = false;
    }
    async setParking(id) { this.state.parking = id; await this.load(); }
    async setPeriod(key) { this.state.period = key; await this.load(); }

    // ---------- Formats ----------
    money(v) {
        const c = this.state.data.currency;
        const n = new Intl.NumberFormat("fr-FR", {
            minimumFractionDigits: c.decimals, maximumFractionDigits: c.decimals,
        }).format(v || 0);
        return c.position === "after" ? `${n} ${c.symbol}` : `${c.symbol} ${n}`;
    }
    short(v) {
        v = v || 0;
        if (Math.abs(v) >= 1e6) return (Math.round(v / 1e5) / 10).toString().replace(".", ",") + " M";
        if (Math.abs(v) >= 1e3) return Math.round(v / 1e3) + " k";
        return String(Math.round(v));
    }
    initials(name) {
        return (name || "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
    }
    barColor(rate) {
        if (rate >= 85) return "#ee9a9a";   // presque plein
        if (rate >= 50) return "#f2c48c";
        return "#9ccfb4";
    }

    // ---------- Graphiques ----------
    donut(items, colors) {
        const r = 54, C = 2 * Math.PI * r;
        const total = items.reduce((s, i) => s + i.value, 0);
        let acc = 0;
        return items.map((i) => {
            const len = total ? (i.value / total) * C : 0;
            const seg = {
                ...i, color: colors[i.key],
                dash: `${Math.max(len - 2, 0)} ${C - Math.max(len - 2, 0)}`, offset: -acc,
            };
            acc += len;
            return seg;
        });
    }
    get placesDonut() { return this.donut(this.state.data.places_split, PLACES_COLORS); }
    get stateDonut() { return this.donut(this.state.data.res_state, STATE_COLORS); }
    get payDonut() { return this.donut(this.state.data.payment, PAY_COLORS); }
    sum(items) { return items.reduce((s, i) => s + i.value, 0); }

    get ringDash() {
        const C = 2 * Math.PI * 54;
        const v = Math.min(Math.max(this.state.data.kpis.occupation, 0), 100);
        return `${(v / 100) * C} ${C}`;
    }

    get chart() {
        const W = 640, H = 230, padL = 20, padR = 16, padT = 34, padB = 34;
        const months = this.state.data.monthly;
        const maxB = Math.max(...months.map((m) => m.bar), 1);
        const maxL = Math.max(...months.map((m) => m.line), 1);
        const step = (W - padL - padR) / months.length;
        const bw = Math.min(step * 0.5, 46);
        const ph = H - padT - padB;
        const bars = months.map((m, i) => {
            const h = (m.bar / maxB) * ph * 0.36;
            const x = padL + step * i + (step - bw) / 2;
            return { x, y: H - padB - h, w: bw, h, label: m.label, value: m.bar, cx: x + bw / 2 };
        });
        const pts = months.map((m, i) => ({
            x: padL + step * i + step / 2,
            y: padT + ph - (0.52 + 0.46 * (m.line / maxL)) * ph,
            label: this.short(m.line), has: m.line > 0,
        }));
        const drawn = pts.filter((p) => p.has);
        return {
            W, H, bars, drawn, line: drawn.map((p) => `${p.x},${p.y}`).join(" "),
            base: H - padB,
        };
    }

    // ---------- Navigation ----------
    _domain(extra = []) {
        const d = [...extra];
        if (this.state.parking) d.push(["parking_id", "=", this.state.parking]);
        return d;
    }
    openRes(name, domain = []) {
        this.action.doAction({
            type: "ir.actions.act_window", name, res_model: "adk.parking.reservation",
            views: [[false, "list"], [false, "form"]], domain: this._domain(domain),
        });
    }
    openRecord(model, id) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: model, res_id: id, views: [[false, "form"]],
        });
    }
    openParkings() { this.action.doAction("adk_parking.action_adk_parking"); }
    openUnpaid() { this.openRes("Paiements en attente", [["user_type", "=", "client"], ["payment_status", "=", "not_paid"], ["state", "!=", "cancelled"]]); }
}

registry.category("actions").add("adk_parking_dashboard", AdkParkingDashboard);
