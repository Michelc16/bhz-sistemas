/** @odoo-module **/

// Server-side renders slides/indicators; this widget refreshes the feed
// on page load and (re)initializes Bootstrap Carousel safely.
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",
    disabledInEditableMode: false,

    async start() {
        await this._super(...arguments);
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel");
        this.interval = this._readInterval();
        this.autoplay = this._readAutoplay();
        this.prevButton = this.el.querySelector(".carousel-control-prev");
        this.nextButton = this.el.querySelector(".carousel-control-next");
        this._boundPrev = (ev) => this._onPrevClick(ev);
        this._boundNext = (ev) => this._onNextClick(ev);
        await this._refreshContent();
        this._bindNav();
        this._ensureActives();
        this._initCarousel();
        this._scheduleRefresh();
        return this;
    },

    async _refreshContent() {
        // Pull latest featured events to avoid stale slides persisted in the page arch.
        if (!this.el || !this.sectionEl || !this.el.isConnected) {
            return;
        }
        if (this._isEditor()) {
            return;
        }
        const limit = this._readLimit();
        const carouselId = this.el.id || this.sectionEl.id || undefined;
        const inner = this.el.querySelector(".js-bhz-featured-inner");
        const indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
        const emptyEl = this.sectionEl.querySelector(
            ".js-bhz-featured-empty, .js-guiabh-featured-empty"
        );

        try {
            const payload = await rpc("/_bhz_event_promo/featured", {
                limit,
                carousel_id: carouselId,
            });

            if (this.isDestroyed || !payload) {
                return;
            }

            if (payload.config) {
                this.autoplay = payload.config.autoplay;
                this.interval = payload.config.interval_ms || this.interval;
                this.sectionEl.dataset.interval = this.interval;
                this.sectionEl.dataset.bhzAutoplay = String(this.autoplay);
                this.sectionEl.dataset.bhzRefreshMs = payload.config.refresh_ms || this.sectionEl.dataset.bhzRefreshMs;
                this._scheduleRefresh();
            }

            const signature = JSON.stringify({
                items: payload.items_html,
                indicators: payload.indicators_html,
                has_events: payload.has_events,
                autoplay: this.autoplay,
                interval: this.interval,
                refresh: this._readRefreshMs(),
            });
            const unchanged = signature === this._lastPayloadSignature;
            this._lastPayloadSignature = signature;

            if (unchanged) {
                // No DOM mutation needed; make sure carousel stays alive.
                this._ensureActives();
                this._initCarousel();
                return;
            }

            // Dispose before DOM mutations to avoid dangling bootstrap instances.
            this._disposeCarousel();

            if (inner && typeof payload.items_html === "string") {
                inner.innerHTML = payload.items_html;
            }
            if (indicatorsWrapper) {
                if (payload.has_multiple && typeof payload.indicators_html === "string") {
                    indicatorsWrapper.innerHTML = payload.indicators_html;
                    indicatorsWrapper.classList.toggle("d-none", false);
                } else {
                    indicatorsWrapper.innerHTML = "";
                    indicatorsWrapper.classList.add("d-none");
                }
            }
            if (emptyEl) {
                emptyEl.classList.toggle("d-none", !!payload.has_events);
            }
        } catch (_err) {
            // Fail silently on public pages; fallback DOM remains visible.
        }
        this._ensureActives();
        this._initCarousel();
    },

    _disposeCarousel() {
        const existing = window.bootstrap?.Carousel?.getInstance?.(this.el);
        if (existing) {
            existing.dispose();
        }
        this._bootstrapCarousel = null;
    },

    _ensureActives() {
        const items = this.el.querySelectorAll(".carousel-item");
        if (items.length && !this.el.querySelector(".carousel-item.active")) {
            items[0].classList.add("active");
        }
        const indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
        const indicators = indicatorsWrapper ? indicatorsWrapper.querySelectorAll("button[data-bs-slide-to]") : [];
        if (indicatorsWrapper && indicators.length && !indicatorsWrapper.querySelector(".active")) {
            const first = indicatorsWrapper.querySelector('button[data-bs-slide-to="0"]') || indicators[0];
            first.classList.add("active");
            first.setAttribute("aria-current", "true");
        }
    },

    _initCarousel() {
        // In edit mode we still initialize the carousel so the user can preview.
        // Auto-refresh is still disabled in edit mode to avoid DOM mutations while editing.
        const items = this.el.querySelectorAll(".carousel-item");
        const indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
        const indicators = indicatorsWrapper ? indicatorsWrapper.querySelectorAll("button[data-bs-slide-to]") : [];
        if (!items.length || !window.bootstrap?.Carousel) {
            return;
        }
        // Sync attributes for Bootstrap behaviour (and for non-JS fallback).
        const intervalStr = String(this.interval || 5000);
        this.el.dataset.bsInterval = intervalStr;
        this.el.dataset.bsRide = this.autoplay ? "carousel" : "false";
        this.el.setAttribute("data-bs-interval", intervalStr);
        this.el.setAttribute("data-bs-ride", this.autoplay ? "carousel" : "false");
        // Dispose any previous instance to avoid multiple initializations.
        this._disposeCarousel();
        // Only autoplay and show controls if more than one slide.
        const multiple = items.length > 1;
        this.prevButton?.classList.toggle("d-none", !multiple);
        this.nextButton?.classList.toggle("d-none", !multiple);
        if (indicatorsWrapper) {
            const hasButtons = indicators.length === items.length && multiple;
            indicatorsWrapper.classList.toggle("d-none", !hasButtons);
        }
        if (!multiple) {
            return;
        }
        // Initialize Bootstrap Carousel manually.
        this._bootstrapCarousel = new window.bootstrap.Carousel(this.el, {
            interval: this.autoplay ? this.interval : false,
            ride: this.autoplay ? "carousel" : false,
            pause: this.autoplay ? false : true,
            touch: true,
            wrap: true,
        });
        if (this.autoplay) {
            this._bootstrapCarousel.cycle();
        }
    },

    _readLimit() {
        const raw = (this.sectionEl && this.sectionEl.dataset.limit) || this.el.dataset.limit;
        const parsed = parseInt(raw || "12", 10);
        if (Number.isNaN(parsed)) {
            return 12;
        }
        return Math.min(Math.max(parsed, 1), 24);
    },

    _readInterval() {
        const raw = (this.sectionEl && this.sectionEl.dataset.interval) || this.el.dataset.interval || this.el.dataset.bsInterval || "5000";
        const parsed = parseInt(raw, 10);
        const interval = Number.isNaN(parsed) ? 5000 : parsed;
        this.el.dataset.interval = interval;
        this.el.dataset.bsInterval = interval;
        return interval;
    },

    _readAutoplay() {
        const raw = (this.sectionEl && this.sectionEl.dataset.bhzAutoplay) || this.el.dataset.bhzAutoplay;
        if (raw === undefined || raw === null || raw === "") {
            return true;
        }
        return String(raw).toLowerCase() !== "false";
    },

    _readRefreshMs() {
        const raw = (this.sectionEl && this.sectionEl.dataset.bhzRefreshMs) || this.el.dataset.bhzRefreshMs;
        const parsed = parseInt(raw || "0", 10);
        if (Number.isNaN(parsed) || parsed < 0) {
            return 0;
        }
        return parsed;
    },

    _scheduleRefresh() {
        if (this._isEditor()) {
            return;
        }
        const refreshMs = this._readRefreshMs();
        clearInterval(this._refreshTimer);
        this._refreshTimer = null;
        if (!refreshMs) {
            return;
        }
        this._refreshTimer = setInterval(() => {
            if (!document.body.contains(this.el)) {
                clearInterval(this._refreshTimer);
                this._refreshTimer = null;
                return;
            }
            this._refreshContent();
        }, refreshMs);
    },

    _isEditor() {
        // `publicWidget` already provides a reliable signal for website edit mode.
        // Avoid DOM/class heuristics here: they can be true for logged-in admins
        // even when NOT editing, which would disable autoplay/refresh.
        return !!this.editableMode;
    },

    destroy() {
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
        this._disposeCarousel();
        this._unbindNav();
        return this._super(...arguments);
    },

    _bindNav() {
        this.prevButton?.addEventListener("click", this._boundPrev);
        this.nextButton?.addEventListener("click", this._boundNext);
    },

    _unbindNav() {
        this.prevButton?.removeEventListener("click", this._boundPrev);
        this.nextButton?.removeEventListener("click", this._boundNext);
    },

    _onPrevClick(ev) {
        ev?.preventDefault?.();
        ev?.stopPropagation?.();
        this._bootstrapCarousel?.prev();
    },

    _onNextClick(ev) {
        ev?.preventDefault?.();
        ev?.stopPropagation?.();
        this._bootstrapCarousel?.next();
    },
});
