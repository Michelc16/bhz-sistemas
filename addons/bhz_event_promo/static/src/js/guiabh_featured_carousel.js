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
        this.prevButton = this.el.querySelector(".carousel-control-prev");
        this.nextButton = this.el.querySelector(".carousel-control-next");
        this._boundPrev = (ev) => this._onPrevClick(ev);
        this._boundNext = (ev) => this._onNextClick(ev);
        await this._refreshContent();
        this._bindNav();
        this._ensureActives();
        this._initCarousel();
        return this;
    },

    async _refreshContent() {
        // Pull latest featured events to avoid stale slides persisted in the page arch.
        if (!this.el || !this.sectionEl) {
            return;
        }
        const limit = this._readLimit();
        const carouselId = this.el.id || this.sectionEl.id || undefined;
        const inner = this.el.querySelector(".js-bhz-featured-inner");
        const indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
        const emptyEl = this.sectionEl.querySelector(
            ".js-bhz-featured-empty, .js-guiabh-featured-empty"
        );

        // Dispose before DOM mutations to avoid dangling bootstrap instances.
        this._disposeCarousel();

        try {
            const payload = await rpc("/_bhz_event_promo/featured", {
                limit,
                carousel_id: carouselId,
            });

            if (this.isDestroyed || !payload) {
                return;
            }

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
        if (indicators.length && !indicatorsWrapper.querySelector(".active")) {
            const first = indicatorsWrapper.querySelector('button[data-bs-slide-to="0"]') || indicators[0];
            first.classList.add("active");
            first.setAttribute("aria-current", "true");
        }
    },

    _initCarousel() {
        if (this._isEditor()) {
            return;
        }
        const items = this.el.querySelectorAll(".carousel-item");
        const indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
        const indicators = indicatorsWrapper ? indicatorsWrapper.querySelectorAll("button[data-bs-slide-to]") : [];
        if (!items.length || !window.bootstrap?.Carousel) {
            return;
        }
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
            interval: this.interval,
            ride: true,
            pause: false,
            touch: true,
            wrap: true,
        });
        this._bootstrapCarousel.cycle();
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

    _isEditor() {
        return this.editableMode || document.body.classList.contains("editor_enable");
    },

    destroy() {
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
