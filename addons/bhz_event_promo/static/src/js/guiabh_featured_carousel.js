/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

function _toInt(value, fallback) {
    const n = parseInt(value, 10);
    return Number.isNaN(n) ? fallback : n;
}

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",

    // NOTE: In Odoo 19, `publicWidget`'s super call (`this._super`) can break
    // when overriding methods are declared with ES6 shorthand (`start() {}`),
    // yielding `this._super is not a function` in web.assets_frontend_lazy.
    // Use the classic function syntax to keep proper super wrapping.
    start: function () {
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel") || this.el;
        this.carouselId = this.el.getAttribute("id") || null;

        // Disable only in *real* edit mode (avoid false positives like oe_structure).
        if (this._isEditMode()) {
            // Don't run carousel/init/refresh in the editor to avoid OWL patch
            // errors ("removeChild ... not a child...").
            return this._super.apply(this, arguments);
        }

        // The website editor can be injected after widgets start. If that
        // happens while we are running timers and mutating DOM, OWL may crash
        // with `removeChild ... not a child of this node`. Watch for the editor
        // UI and disable ourselves as soon as it appears.
        this._editorObserver = new MutationObserver(() => {
            if (!this._editorObserver) {
                return;
            }
            if (this._isEditMode()) {
                try {
                    if (this._refreshTimer) {
                        clearInterval(this._refreshTimer);
                        this._refreshTimer = null;
                    }
                    this._disposeCarousel();
                } finally {
                    this._editorObserver.disconnect();
                    this._editorObserver = null;
                }
            }
        });
        this._editorObserver.observe(document.documentElement, { subtree: true, childList: true });

        this._applyAutoplayConfig();
        this._initCarousel();

        const refreshMs = this._getRefreshMs();
        if (refreshMs > 0) {
            this._refreshTimer = setInterval(() => this._refreshContent(), refreshMs);
        }

        return this._super.apply(this, arguments);
    },

    destroy: function () {
        if (this._editorObserver) {
            this._editorObserver.disconnect();
            this._editorObserver = null;
        }
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
        this._disposeCarousel();
        return this._super.apply(this, arguments);
    },

    // -------------------------------------------------------------------------
    // Config
    // -------------------------------------------------------------------------

    _isEditMode: function () {
        const b = document.body;
        if (!b) return false;

        // Markers used by Odoo website editor across versions
        if (
            b.classList.contains("editor_enable") ||
            b.classList.contains("o_is_editing") ||
            b.classList.contains("o_we_editing") ||
            b.classList.contains("o_website_edit_mode")
        ) {
            return true;
        }

        // URL flags used by the website editor / preview.
        try {
            const params = new URLSearchParams(window.location.search || "");
            if (
                params.get("enable_editor") === "1" ||
                params.get("editor") === "1" ||
                params.get("edit") === "1"
            ) {
                return true;
            }
        } catch (e) {
            // ignore
        }

        // Extra DOM markers seen in the editor UI; more reliable than body
        // classes on some builds/asset bundles.
        return !!document.querySelector(
            ".o_we_toolbar, .o_we_website_top_actions, #oe_snippets, .o_website_builder"
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
