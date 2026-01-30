/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import {
    Component,
    mount,
    useState,
    onWillStart,
    onMounted,
    onPatched,
    onWillUnmount,
} from "@odoo/owl";

function _toInt(value, fallback) {
    const n = parseInt(value, 10);
    return Number.isNaN(n) ? fallback : n;
}

function isEditMode() {
    const b = document.body;
    const h = document.documentElement;

    const classMarkers = ["editor_enable", "o_is_editing", "o_we_editing", "o_website_edit_mode"];
    const hasMarker = (el) =>
        !!el && classMarkers.some((c) => el.classList && el.classList.contains(c));

    if (hasMarker(b) || hasMarker(h)) return true;

    return !!document.querySelector(
        ".o_we_toolbar, .o_we_sidebar, .o_website_editor, .o_we_customize_panel, .o_we_dialog"
    );
}

class GuiabhFeaturedCarouselRoot extends Component {
    static template = "bhz_event_promo.GuiabhFeaturedCarouselOwl";
    static props = [
        "carouselEl",
        "sectionEl",
        "innerEl",
        "indicatorsEl",
        "emptyEl",
        "prevBtn",
        "nextBtn",
        "carouselTarget",
    ];

    setup() {
        this.state = useState({
            events: [],
            has_events: false,
            has_multiple: false,
        });

        this._timer = null;

        onWillStart(async () => {
            await this._refresh();
        });

        onMounted(() => {
            this._ensureCarousel();
            this._applyVisibility();
            this._setupAutoRefresh();
        });

        onPatched(() => {
            // When Owl patches the carousel items, re-init bootstrap safely.
            this._ensureCarousel();
            this._applyVisibility();
        });

        onWillUnmount(() => {
            if (this._timer) clearInterval(this._timer);
            this._timer = null;
            this._disposeCarousel();
        });
    }

    _getInterval() {
        const el = this.props.carouselEl;
        const sectionEl = this.props.sectionEl;
        const raw =
            el?.dataset?.bsInterval ||
            el?.dataset?.interval ||
            sectionEl?.dataset?.interval ||
            sectionEl?.getAttribute?.("data-interval") ||
            "5000";
        const val = _toInt(raw, 5000);
        return Math.min(Math.max(val, 1000), 20000);
    }

    _getRefreshMs() {
        const sectionEl = this.props.sectionEl;
        const raw =
            sectionEl?.dataset?.bhzRefreshMs ||
            sectionEl?.getAttribute?.("data-bhz-refresh-ms") ||
            "0";
        const val = _toInt(raw, 0);
        return Math.min(Math.max(val, 0), 600000);
    }

    _getAutoplay() {
        const sectionEl = this.props.sectionEl;
        const raw = sectionEl?.dataset?.bhzAutoplay ?? sectionEl?.getAttribute?.("data-bhz-autoplay");
        if (raw === undefined || raw === null || raw === "") return true;
        return String(raw).toLowerCase() !== "false";
    }

    _applyAutoplayAttrs() {
        const el = this.props.carouselEl;
        if (!el) return;

        const autoplay = this._getAutoplay() && !isEditMode();
        const interval = this._getInterval();

        el.dataset.bsInterval = String(interval);
        el.dataset.interval = String(interval);
        el.setAttribute("data-bs-ride", autoplay ? "carousel" : "false");
    }

    _disposeCarousel() {
        const el = this.props.carouselEl;
        try {
            const inst = window.bootstrap?.Carousel?.getInstance?.(el);
            inst?.dispose?.();
        } catch {
            // ignore
        }
    }

    _ensureCarousel() {
        const el = this.props.carouselEl;
        if (!el || !window.bootstrap?.Carousel) return;

        this._applyAutoplayAttrs();

        const autoplay = this._getAutoplay() && !isEditMode();
        const interval = this._getInterval();

        // Reset instance to ensure interval changes apply.
        this._disposeCarousel();
        window.bootstrap.Carousel.getOrCreateInstance(el, {
            interval: autoplay ? interval : false,
            ride: autoplay ? "carousel" : false,
            pause: "hover",
            touch: true,
            keyboard: true,
        });
    }

    _applyVisibility() {
        const { emptyEl, prevBtn, nextBtn,
                carouselTarget: this.el?.getAttribute("id") ? ("#" + this.el.getAttribute("id")) : "", indicatorsEl } = this.props;

        if (emptyEl) emptyEl.classList.toggle("d-none", !!this.state.has_events);

        const showNav = !!this.state.has_multiple;
        prevBtn?.classList.toggle("d-none", !showNav);
        nextBtn?.classList.toggle("d-none", !showNav);
        indicatorsEl?.classList.toggle("d-none", !showNav);
    }

    _setupAutoRefresh() {
        const refreshMs = this._getRefreshMs();
        if (refreshMs <= 0) return;

        // Never auto-refresh while editing
        if (isEditMode()) return;

        this._timer = setInterval(() => this._refresh(), refreshMs);
    }

    async _refresh() {
        const { carouselEl, sectionEl } = this.props;

        const limit = _toInt(
            sectionEl?.dataset?.limit || sectionEl?.getAttribute?.("data-limit") || "12",
            12
        );

        let payload;
        try {
            payload = await rpc("/_bhz_event_promo/featured", {
                limit,
                carousel_id: carouselEl?.getAttribute("id") || null,
            });
        } catch {
            return;
        }
        if (!payload) return;

        this.state.events = Array.isArray(payload.events) ? payload.events : [];
        
        this.state.has_events = this.state.events.length > 0;
        this.state.has_multiple = this.state.events.length > 1;
    }
}

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",

    async start() {
        const superStart = this._super?.bind(this);
        const parentResult = superStart ? superStart(...arguments) : undefined;

        const sectionEl = this.el.closest(".s_guiabh_featured_carousel") || this.el;
        const innerEl = this.el.querySelector(".js-bhz-featured-inner");
        const indicatorsEl = this.el.querySelector(".js-bhz-featured-indicators");
        const emptyEl = sectionEl.querySelector(".js-bhz-featured-empty");
        const prevBtn = this.el.querySelector(".carousel-control-prev");
        const nextBtn = this.el.querySelector(".carousel-control-next");

        // Mount a tiny Owl app (no DOM manual changes => avoids Owl removeChild crash).
        const mountPoint = document.createElement("div");
        mountPoint.className = "d-none";
        this.el.appendChild(mountPoint);

        this._owlApp = await mount(GuiabhFeaturedCarouselRoot, mountPoint, {
            props: {
                carouselEl: this.el,
                sectionEl,
                innerEl,
                indicatorsEl,
                emptyEl,
                prevBtn,
                nextBtn,
                carouselTarget: this.el?.getAttribute("id") ? ("#" + this.el.getAttribute("id")) : "",
            },
        });

        return parentResult;
    },

    destroy() {
        const superDestroy = this._super?.bind(this);
        try {
            this._owlApp?.destroy?.();
        } catch {
            // ignore
        }
        this._owlApp = null;
        return superDestroy ? superDestroy(...arguments) : undefined;
    },
});
