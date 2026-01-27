/** @odoo-module **/

// Server-side renders slides/indicators; this widget only (re)initializes Bootstrap Carousel safely.
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",
    disabledInEditableMode: false,

    start() {
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel");
        this.interval = this._readInterval();
        this.prevButton = this.el.querySelector(".carousel-control-prev");
        this.nextButton = this.el.querySelector(".carousel-control-next");
        this._boundPrev = (ev) => this._onPrevClick(ev);
        this._boundNext = (ev) => this._onNextClick(ev);
        this._bindNav();
        this._ensureActives();
        this._initCarousel();
        return this._super(...arguments);
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
            ride: false,
            pause: false,
            touch: true,
            wrap: true,
        });
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
