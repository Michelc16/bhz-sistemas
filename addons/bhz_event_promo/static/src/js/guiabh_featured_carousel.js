/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

function _toInt(value, fallback) {
    const n = parseInt(value, 10);
    return Number.isNaN(n) ? fallback : n;
}

function _toBool(value, fallback) {
    if (value === true || value === false) return value;
    if (value === undefined || value === null || value === "") return fallback;
    const s = String(value).toLowerCase().trim();
    if (["1", "true", "yes", "y", "on"].includes(s)) return true;
    if (["0", "false", "no", "n", "off"].includes(s)) return false;
    return fallback;
}

/**
 * Detects Website Builder / Edit mode robustly.
 * We must NOT touch the DOM inside the editable iframe, otherwise Owl may crash
 * with: "removeChild: The node to be removed is not a child of this node."
 */
function isWebsiteEditor() {
    const loc = window.location;
    if (loc && loc.search && loc.search.includes("enable_editor=1")) return true;
    const body = document.body;
    const html = document.documentElement;
    const has = (el, cls) => !!el && el.classList && el.classList.contains(cls);

    // Common markers
    const markers = [
        "o_is_editing",
        "o_we_editing",
        "o_website_edit_mode",
        "editor_enable",
        "o_is_editable",
        "o_editable",
    ];
    if (markers.some((c) => has(body, c) || has(html, c))) return true;

    // Website builder UI elements
    if (document.querySelector(".o_we_toolbar, .o_we_sidebar, .o_website_editor, .o_we_customize_panel")) {
        return true;
    }

    // When inside iframe, parent often holds the toolbar
    try {
        if (window.top && window.top !== window) {
            const pdoc = window.top.document;
            if (pdoc && pdoc.querySelector(".o_we_toolbar, .o_we_sidebar, .o_website_editor, .o_we_customize_panel")) {
                return true;
            }
        }
    } catch (e) {
        // cross-origin? ignore
    }

    // Fallback: editor iframe endpoints
    if (loc && typeof loc.pathname === "string") {
        if (loc.pathname.startsWith("/website/")) return true;
    }

    return false;
}

function ensureActiveSlide(innerEl) {
    if (!innerEl) return;
    const items = innerEl.querySelectorAll(".carousel-item");
    if (!items.length) return;
    if ([...items].some((el) => el.classList.contains("active"))) return;
    items[0].classList.add("active");
}

function setVisibility({ hasEvents, hasMultiple, prevBtn, nextBtn, indicatorsEl, emptyEl }) {
    if (emptyEl) emptyEl.classList.toggle("d-none", !!hasEvents);
    if (prevBtn) prevBtn.classList.toggle("d-none", !(hasEvents && hasMultiple));
    if (nextBtn) nextBtn.classList.toggle("d-none", !(hasEvents && hasMultiple));
    if (indicatorsEl) indicatorsEl.classList.toggle("d-none", !(hasEvents && hasMultiple));
}

/**
 * Bootstrap carousel init + safe fallback if bootstrap is not present.
 */
function startAutoplay({ carouselEl, intervalMs, hasMultiple }) {
    if (!carouselEl || !hasMultiple) return { stop() {} };

    // Prefer bootstrap if available
    const bs = window.bootstrap;
    if (bs && bs.Carousel) {
        // Force correct attributes even if saved as "false" in HTML
        carouselEl.setAttribute("data-bs-ride", "carousel");
        carouselEl.setAttribute("data-bs-interval", String(intervalMs));

        let inst = bs.Carousel.getInstance(carouselEl);
        if (!inst) {
            inst = new bs.Carousel(carouselEl, {
                interval: intervalMs,
                ride: "carousel",
                pause: false,
                touch: true,
                wrap: true,
            });
        } else {
            // update interval if possible
            try {
                inst._config.interval = intervalMs;
            } catch (e) {}
        }
        try {
            inst.cycle();
        } catch (e) {}
        return {
            stop() {
                try { inst.pause(); } catch (e) {}
            },
        };
    }

    // Fallback: manual slider
    let timer = window.setInterval(() => {
        const items = carouselEl.querySelectorAll(".carousel-item");
        if (!items.length) return;
        let activeIdx = -1;
        items.forEach((el, idx) => {
            if (el.classList.contains("active")) activeIdx = idx;
        });
        const nextIdx = activeIdx === -1 ? 0 : (activeIdx + 1) % items.length;

        if (activeIdx >= 0) items[activeIdx].classList.remove("active");
        items[nextIdx].classList.add("active");

        // indicators
        const indicators = carouselEl.querySelectorAll(".carousel-indicators [data-bs-slide-to], .carousel-indicators button");
        if (indicators.length) {
            indicators.forEach((b) => b.classList.remove("active"));
            if (indicators[nextIdx]) indicators[nextIdx].classList.add("active");
        }
    }, intervalMs);

    return { stop() { window.clearInterval(timer); } };
}

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".s_guiabh_featured_carousel",
    // This is the key to stop running inside the website editor
    disabledInEditableMode: true,

    start() {
        this._superStart = this._super.bind(this);
        this._refreshTimer = null;
        this._autoplayHandle = { stop() {} };

        // Always call super synchronously
        const superRes = this._superStart();

        // Extra safety: do not run in editor at all
        if (isWebsiteEditor()) {
            return superRes;
        }

        this._setup();
        return superRes;
    },

    destroy() {
        try { this._clearTimers(); } catch (e) {}
        this._super.apply(this, arguments);
    },

    _clearTimers() {
        if (this._refreshTimer) {
            window.clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
        if (this._autoplayHandle) {
            try { this._autoplayHandle.stop(); } catch (e) {}
            this._autoplayHandle = { stop() {} };
        }
    },

    async _setup() {
        const sectionEl = this.el;
        const carouselEl = sectionEl.querySelector(".js-bhz-featured-carousel");
        const innerEl = sectionEl.querySelector(".js-bhz-featured-inner");
        const indicatorsEl = sectionEl.querySelector(".js-bhz-featured-indicators");
        const emptyEl = sectionEl.querySelector(".js-bhz-featured-empty");
        const prevBtn = sectionEl.querySelector(".carousel-control-prev");
        const nextBtn = sectionEl.querySelector(".carousel-control-next");

        if (!carouselEl || !innerEl) return;

        const limit = _toInt(sectionEl.dataset.limit, 12);
        const intervalMs = _toInt(sectionEl.dataset.interval, 5000);
        const refreshMs = _toInt(sectionEl.dataset.bhzRefreshMs, 60000);
        const autoplay = _toBool(sectionEl.dataset.bhzAutoplay, true);

        // Store for later
        this._dom = { sectionEl, carouselEl, innerEl, indicatorsEl, emptyEl, prevBtn, nextBtn };
        this._cfg = { limit, intervalMs, refreshMs, autoplay };

        await this._refresh();

        // Auto refresh
        if (refreshMs && refreshMs > 0) {
            this._refreshTimer = window.setInterval(() => {
                this._refresh();
            }, refreshMs);
        }

        // Autoplay
        if (autoplay) {
            this._autoplayHandle = startAutoplay({
                carouselEl,
                intervalMs,
                hasMultiple: !!this._hasMultiple,
            });
        }
    },

    async _refresh() {
        // Do not refresh in editor / in case someone toggled
        if (isWebsiteEditor()) return;

        const { sectionEl, carouselEl, innerEl, indicatorsEl, emptyEl, prevBtn, nextBtn } = this._dom || {};
        const { limit, intervalMs, autoplay } = this._cfg || {};
        if (!carouselEl || !innerEl) return;

        let payload;
        try {
            payload = await rpc("/_bhz_event_promo/featured", {
                limit: limit || 12,
                carousel_id: carouselEl.getAttribute("id") || null,
            });
        } catch (e) {
            // On failure, show empty
            innerEl.innerHTML = "";
            if (indicatorsEl) indicatorsEl.innerHTML = "";
            setVisibility({ hasEvents: false, hasMultiple: false, prevBtn, nextBtn, indicatorsEl, emptyEl });
            return;
        }

        const itemsHtml = payload?.items_html || payload?.slides || "";
        const indicatorsHtml = payload?.indicators_html || payload?.indicators || "";
        const hasEvents = !!payload?.has_events;
        const hasMultiple = !!payload?.has_multiple;

        // IMPORTANT: Only mutate DOM in public mode (we're in public here)
        innerEl.innerHTML = itemsHtml || "";
        if (indicatorsEl) indicatorsEl.innerHTML = indicatorsHtml || "";

        ensureActiveSlide(innerEl);
        setVisibility({ hasEvents, hasMultiple, prevBtn, nextBtn, indicatorsEl, emptyEl });

        this._hasMultiple = hasMultiple;

        // Restart autoplay instance to ensure it cycles with new slides
        this._autoplayHandle?.stop?.();
        if (autoplay) {
            this._autoplayHandle = startAutoplay({
                carouselEl,
                intervalMs: intervalMs || 5000,
                hasMultiple,
            });
        }
    },
});
