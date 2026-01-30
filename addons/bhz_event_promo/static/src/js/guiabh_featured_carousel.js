/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

/**
 * GuiaBH - Featured Carousel
 *
 * Requirements:
 * - Autoplay: slides must advance automatically (Bootstrap Carousel)
 * - Editor-safe: do nothing in edit mode (prevents Owl patch/removeChild issues)
 *
 * NOTE: This widget intentionally does NOT auto-refresh/remove slides.
 * Removing a featured event will reflect after a normal page reload.
 */
publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",
    disabledInEditableMode: true,

    async start() {
        // In some builds `_super` can be missing; guard it to avoid runtime errors.
        if (typeof this._super === "function") {
            await this._super(...arguments);
        }

        // Load slides (server-rendered list) and then init autoplay.
        await this._loadSlides();
        this._initAutoplay();
    },

    _getSection() {
        return this.el.closest("section.s_guiabh_featured_carousel") || this.el;
    },

    _getBool(dataValue, fallback = false) {
        if (dataValue === undefined || dataValue === null || dataValue === "") {
            return fallback;
        }
        return String(dataValue).toLowerCase() === "true";
    },

    _getInt(dataValue, fallback) {
        const n = parseInt(dataValue, 10);
        return Number.isFinite(n) ? n : fallback;
    },

    _readConfig() {
        const section = this._getSection();
        const ds = section.dataset || {};

        return {
            limit: this._getInt(ds.limit, 12),
            interval_ms: this._getInt(ds.interval, this._getInt(ds.bsInterval, 5000)),
            autoplay: this._getBool(ds.bhzAutoplay, true),
        };
    },

    async _loadSlides() {
        const section = this._getSection();
        const cfg = this._readConfig();

        // Fetch slides HTML from server.
        const res = await jsonrpc("/bhz_event_promo/snippet/featured_events", {
            limit: cfg.limit,
        });

        const inner = section.querySelector(".js-bhz-featured-inner");
        const indicators = section.querySelector(".js-bhz-featured-indicators");
        const prev = section.querySelector(".carousel-control-prev");
        const next = section.querySelector(".carousel-control-next");
        const empty = section.querySelector(".js-bhz-featured-empty");

        if (!inner) {
            return;
        }

        if (!res || res.count === 0) {
            inner.innerHTML = "";
            indicators && indicators.classList.add("d-none");
            prev && prev.classList.add("d-none");
            next && next.classList.add("d-none");
            empty && empty.classList.remove("d-none");
            return;
        }

        // Replace DOM (safe because we don't run in editor).
        inner.innerHTML = res.html || "";
        if (indicators) {
            indicators.outerHTML = res.indicators_html || indicators.outerHTML;
        }

        // Show controls only if multiple items.
        const showControls = res.count > 1;
        prev && prev.classList.toggle("d-none", !showControls);
        next && next.classList.toggle("d-none", !showControls);
        empty && empty.classList.add("d-none");
    },

    _initAutoplay() {
        const section = this._getSection();
        const cfg = this._readConfig();

        // Bootstrap Carousel instance (Bootstrap is global in website).
        const Carousel = window.bootstrap && window.bootstrap.Carousel;
        if (!Carousel) {
            return;
        }

        // If there is 0/1 item, autoplay is irrelevant.
        const items = section.querySelectorAll(".carousel-item");
        if (!items || items.length < 2) {
            return;
        }

        const instance = Carousel.getOrCreateInstance(this.el, {
            interval: cfg.autoplay ? cfg.interval_ms : false,
            ride: cfg.autoplay ? "carousel" : false,
            pause: "hover",
            wrap: true,
            touch: true,
        });

        if (cfg.autoplay && typeof instance.cycle === "function") {
            instance.cycle();
        }
    },
});
