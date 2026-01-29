/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

function _toInt(value, fallback) {
    const n = parseInt(value, 10);
    return Number.isNaN(n) ? fallback : n;
}

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",

    start() {
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel") || this.el;
        this.carouselId = this.el.getAttribute("id") || null;

        // Disable only in *real* edit mode (avoid false positives like oe_structure).
        if (this._isEditMode()) {
            // In some website editor contexts the legacy widget may be mounted without _super.
            // Avoid breaking the whole editor.
            return this._super ? this._super.apply(this, arguments) : Promise.resolve();
        }

        this._applyAutoplayConfig();
        this._initCarousel();

        const refreshMs = this._getRefreshMs();
        if (refreshMs > 0) {
            this._refreshTimer = setInterval(() => this._refreshContent(), refreshMs);
        }

        return this._super ? this._super.apply(this, arguments) : Promise.resolve();
    },

    destroy() {
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
        this._disposeCarousel();
        return this._super ? this._super.apply(this, arguments) : undefined;
    },

    // -------------------------------------------------------------------------
    // Config
    // -------------------------------------------------------------------------

    _isEditMode() {
        const b = document.body;
        const docEl = document.documentElement;

        const hasMarker = (body) =>
            !!body &&
            (
                body.classList.contains("editor_enable") ||
                body.classList.contains("o_is_editing") ||
                body.classList.contains("o_we_editing") ||
                body.classList.contains("o_website_edit_mode") ||
                body.classList.contains("o_we_website_editor")
            );

        // Markers in current document
        if (hasMarker(b)) return true;
        if (docEl?.classList?.contains("o_we_preview")) return true;

        // Markers in parent (website editor runs in an iframe, same-origin)
        try {
            const topBody = window.top?.document?.body;
            if (topBody && topBody !== b && hasMarker(topBody)) return true;
        } catch {
            // ignore
        }

        return false;
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

        const inst = window.bootstrap.Carousel.getOrCreateInstance(this.el, {
            interval: autoplay ? interval : false,
            ride: false, // we control cycling explicitly
            pause: false, // guarantee autoplay even with overlays
            touch: true,
            keyboard: true,
            wrap: true,
        });

        // Bootstrap only auto-starts in some cases depending on attributes.
        // Force cycle when enabled.
        try {
            if (autoplay) {
                inst?.cycle?.();
            } else {
                inst?.pause?.();
            }
        } catch {
            // ignore
        }
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
