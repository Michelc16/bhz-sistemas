/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

function _toInt(value, fallback) {
    const n = parseInt(value, 10);
    return Number.isNaN(n) ? fallback : n;
}

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",

    async start() {
        // IMPORTANT (Odoo legacy Class + async):
        // this._super is only available during the synchronous part of the call.
        // If we await before calling it, it may be reset and become undefined.
        const superStart = this._super?.bind(this);

        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel") || this.el;
        this.carouselId = this.el.getAttribute("id") || null;

        // Disable only in *real* edit mode (avoid false positives like oe_structure).
        if (this._isEditMode()) {
            return superStart ? superStart(...arguments) : undefined;
        }

        // Call parent start early (before any await) to avoid "this._super is not a function".
        const parentResult = superStart ? superStart(...arguments) : undefined;

        this._applyAutoplayConfig();

        // Always fetch the latest featured events once on load.
        // This prevents stale slides remaining on the homepage after a featured
        // flag is toggled (the website page HTML is persisted).
        await this._refreshContent();

        // Ensure a carousel instance exists even when refresh returns nothing.
        this._initCarousel();

        const refreshMs = this._getRefreshMs();
        if (refreshMs > 0) {
            this._refreshTimer = setInterval(() => this._refreshContent(), refreshMs);
        }

        return parentResult;
    },

    destroy() {
        const superDestroy = this._super?.bind(this);
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
        this._disposeCarousel();
        return superDestroy ? superDestroy(...arguments) : undefined;
    },

    // -------------------------------------------------------------------------
    // Config
    // -------------------------------------------------------------------------

    _isEditMode() {
        // We must be VERY conservative here: mutating the snippet DOM while the
        // website editor (Owl) is active can crash the editor with:
        //   "removeChild ... node is not a child of this node".
        const b = document.body;
        const h = document.documentElement;

        const classMarkers = [
            "editor_enable",
            "o_is_editing",
            "o_we_editing",
            "o_website_edit_mode",
            "o_we_preview", // sometimes used during builder transitions
        ];

        const hasMarker = (el) =>
            !!el && classMarkers.some((c) => el.classList && el.classList.contains(c));

        if (hasMarker(b) || hasMarker(h)) return true;

        // Fallback: detect builder UI nodes (covers cases where classes are not yet applied).
        return !!document.querySelector(
            ".o_we_toolbar, .o_we_sidebar, .o_website_editor, .o_we_customize_panel, .o_we_dialog"
        );
    },

    _getInterval() {
        const raw =
            this.el.dataset.bsInterval ||
            this.el.dataset.interval ||
            this.sectionEl?.dataset?.interval ||
            this.sectionEl?.getAttribute?.("data-interval") ||
            "5000";
        const val = _toInt(raw, 5000);
        return Math.min(Math.max(val, 1000), 20000);
    },

    _getRefreshMs() {
        const raw =
            this.sectionEl?.dataset?.bhzRefreshMs ||
            this.sectionEl?.getAttribute?.("data-bhz-refresh-ms") ||
            "0";
        const val = _toInt(raw, 0);
        return Math.min(Math.max(val, 0), 600000);
    },

    _getAutoplay() {
        const raw =
            this.sectionEl?.dataset?.bhzAutoplay ??
            this.sectionEl?.getAttribute?.("data-bhz-autoplay");
        if (raw === undefined || raw === null || raw === "") return true;
        return String(raw).toLowerCase() !== "false";
    },

    _applyAutoplayConfig() {
        const autoplay = this._getAutoplay();
        const interval = this._getInterval();

        // Normalize attributes for Bootstrap
        this.el.dataset.bsInterval = String(interval);
        this.el.dataset.interval = String(interval);

        // Some templates/editor may force data-bs-ride="false".
        // We override it to guarantee autoplay when enabled.
        this.el.setAttribute("data-bs-ride", autoplay ? "carousel" : "false");
    },

    // -------------------------------------------------------------------------
    // Bootstrap Carousel
    // -------------------------------------------------------------------------

    _disposeCarousel() {
        try {
            const inst = window.bootstrap?.Carousel?.getInstance?.(this.el);
            inst?.dispose?.();
        } catch {
            // ignore
        }
    },

    _initCarousel() {
        if (!window.bootstrap?.Carousel) return;

        this._disposeCarousel();

        const autoplay = this._getAutoplay();
        const interval = this._getInterval();

        window.bootstrap.Carousel.getOrCreateInstance(this.el, {
            interval: autoplay ? interval : false,
            ride: autoplay ? "carousel" : false,
            pause: "hover",
            touch: true,
            keyboard: true,
        });
    },

    // -------------------------------------------------------------------------
    // Auto refresh (remove/add featured events automatically)
    // -------------------------------------------------------------------------

    async _refreshContent() {
        // Avoid Owl DOM patch issues in editor
        if (this._isEditMode()) return;

        const limit = _toInt(
            this.sectionEl?.dataset?.limit || this.sectionEl?.getAttribute?.("data-limit") || "12",
            12
        );

        let payload;
        try {
            payload = await rpc("/_bhz_event_promo/featured", {
                limit,
                carousel_id: this.carouselId,
            });
        } catch {
            return;
        }
        if (!payload) return;

        const inner = this.el.querySelector(".js-bhz-featured-inner");
        const indicators = this.el.querySelector(".js-bhz-featured-indicators");
        const empty = this.sectionEl?.querySelector(".js-bhz-featured-empty");

        const itemsHtml = payload.items_html || payload.slides || "";
        const indicatorsHtml = payload.indicators_html || payload.indicators || "";

        if (inner) inner.innerHTML = itemsHtml;
        if (indicators) indicators.innerHTML = indicatorsHtml;

        const hasEvents = !!payload.has_events;
        if (empty) empty.classList.toggle("d-none", hasEvents);

        const hasMultiple = !!payload.has_multiple;
        const prevBtn = this.el.querySelector(".carousel-control-prev");
        const nextBtn = this.el.querySelector(".carousel-control-next");
        prevBtn?.classList.toggle("d-none", !hasMultiple);
        nextBtn?.classList.toggle("d-none", !hasMultiple);
        indicators?.classList.toggle("d-none", !hasMultiple);

        // Re-init after DOM replacement
        this._applyAutoplayConfig();
        this._initCarousel();
    },
});
