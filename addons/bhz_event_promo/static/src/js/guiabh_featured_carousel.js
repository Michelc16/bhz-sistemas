/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

/**
 * Featured Carousel (GuiaBH)
 *
 * Goals:
 * - Never run inside website editor iframe (prevents Owl DOM patch crashes).
 * - Fetch slides/indicators via JSON-RPC and inject HTML (server renders QWeb).
 * - Start Bootstrap Carousel autoplay reliably.
 *
 * This is intentionally NOT an Owl component to avoid template loading issues
 * and editor lifecycle conflicts.
 */

function toInt(value, fallback) {
    const n = parseInt(value, 10);
    return Number.isNaN(n) ? fallback : n;
}

function isInWebsiteEditor() {
    // Editor iframe URLs
    const path = window.location.pathname || "";
    if (path.startsWith("/website/iframe") || path.startsWith("/website/iframefallback")) {
        return true;
    }
    // Body classes usually present when editing
    const body = document.body;
    if (!body) return false;
    if (body.classList.contains("editor_enable") || body.classList.contains("o_is_editing")) {
        return true;
    }
    // Builder assets often add this
    if (document.querySelector(".o_we_website_top_actions, .o_we_website_editor, .o_we_toolbar")) {
        return true;
    }
    return false;
}

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",

    start() {
        // Call parent start synchronously first (important in Odoo legacy widgets)
        const superPromise = this._super.apply(this, arguments);

        this._carouselEl = this.el;
        this._innerEl = this.el.querySelector(".js-bhz-featured-inner");
        this._indicatorsEl = this.el.querySelector(".js-bhz-featured-indicators");
        this._emptyEl = this.el.closest("section")?.querySelector(".js-bhz-featured-empty");

        // Read options
        const section = this.el.closest("section");
        const dataset = section ? section.dataset : {};
        this._limit = toInt(dataset.limit, 12);
        this._refreshMs = toInt(dataset.bhzRefreshMs, 60000);
        this._autoplay = (dataset.bhzAutoplay || "true") !== "false";

        // Bootstrap interval: prefer data-bs-interval on carousel, fallback to data-interval on section
        const bsInterval = this.el.getAttribute("data-bs-interval");
        const sectionInterval = dataset.interval;
        this._interval = toInt(bsInterval || sectionInterval, 5000);

        this._isEditor = isInWebsiteEditor();
        if (this._isEditor) {
            // Do NOT fetch/inject or init bootstrap in editor to avoid Owl crashes.
            return superPromise;
        }

        // Initial load + optional refresh
        this._loadAndRender();
        if (this._refreshMs > 0) {
            this._refreshTimer = setInterval(() => this._loadAndRender(), this._refreshMs);
        }

        return superPromise;
    },

    destroy() {
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
        this._disposeBootstrap();
        return this._super.apply(this, arguments);
    },

    async _loadAndRender() {
        if (!this._innerEl || !this._indicatorsEl) return;

        const carouselId = this._carouselEl.getAttribute("id");
        try {
            const payload = await rpc("/_bhz_event_promo/featured", {
                limit: this._limit,
                carousel_id: carouselId,
            });

            const itemsHtml = (payload && payload.items_html) || "";
            const indicatorsHtml = (payload && payload.indicators_html) || "";

            // Inject HTML from server-rendered QWeb template
            this._innerEl.innerHTML = itemsHtml;
            this._indicatorsEl.innerHTML = indicatorsHtml;

            const hasItems = !!this._innerEl.querySelector(".carousel-item");

            // Toggle empty message + controls
            this._toggleVisibility(hasItems);

            // (Re)start bootstrap carousel autoplay
            if (hasItems) {
                this._restartBootstrap();
            } else {
                this._disposeBootstrap();
            }
        } catch (err) {
            // Fail safe: show empty state, don't break page/editor
            this._toggleVisibility(false);
            this._disposeBootstrap();
            // eslint-disable-next-line no-console
            console.warn("BHZ Featured Carousel: failed to fetch/render", err);
        }
    },

    _toggleVisibility(hasItems) {
        const section = this.el.closest("section");

        // controls and indicators are marked o_not_editable + d-none initially
        const prevBtn = section?.querySelector(".carousel-control-prev");
        const nextBtn = section?.querySelector(".carousel-control-next");

        if (prevBtn) prevBtn.classList.toggle("d-none", !hasItems);
        if (nextBtn) nextBtn.classList.toggle("d-none", !hasItems);
        if (this._indicatorsEl) this._indicatorsEl.classList.toggle("d-none", !hasItems);
        if (this._emptyEl) this._emptyEl.classList.toggle("d-none", hasItems);
    },

    _disposeBootstrap() {
        if (this._bsInstance) {
            try {
                this._bsInstance.dispose();
            } catch (_) {
                // ignore
            }
            this._bsInstance = null;
        }
    },

    _restartBootstrap() {
        // Bootstrap is loaded in website frontend; guard anyway.
        const Bootstrap = window.bootstrap;
        if (!Bootstrap || !Bootstrap.Carousel) {
            return;
        }
        this._disposeBootstrap();

        // Ensure required attributes for autoplay
        this._carouselEl.setAttribute("data-bs-ride", this._autoplay ? "carousel" : "false");
        this._carouselEl.setAttribute("data-bs-interval", String(this._interval));

        // Create instance
        this._bsInstance = new Bootstrap.Carousel(this._carouselEl, {
            interval: this._autoplay ? this._interval : false,
            ride: this._autoplay ? "carousel" : false,
            pause: "hover",
            touch: true,
        });

        if (this._autoplay) {
            try {
                this._bsInstance.cycle();
            } catch (_) {
                // ignore
            }
        }
    },
});
