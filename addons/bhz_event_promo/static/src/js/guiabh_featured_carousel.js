/** @odoo-module **/

// Server-side renders slides and indicators; JS only bootstraps Carousel when needed.
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",
    disabledInEditableMode: false,

    async start() {
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel");
        this.interval = this._readInterval();
        this.prevButton = this.el.querySelector(".carousel-control-prev");
        this.nextButton = this.el.querySelector(".carousel-control-next");
        this._boundPrev = this._onPrevClick.bind(this);
        this._boundNext = this._onNextClick.bind(this);
        await this._super(...arguments);
        this._bindNav();
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
        if (items.length < 2) {
            return;
        }
        if (indicatorsWrapper && indicators.length !== items.length) {
            return;
        }
        const interval = this.interval;
        this._bootstrapCarousel = new window.bootstrap.Carousel(this.el, {
            interval,
            ride: false,
            pause: "hover",
            touch: true,
            wrap: true,
        });
        if (interval) {
            this._bootstrapCarousel.cycle();
        } else {
            this._bootstrapCarousel.pause();
        }
    },

    _applyIntervalToInstance() {
        if (!this._bootstrapCarousel) {
            return;
        }
        if (this.interval <= 0 || this._isEditor()) {
            this._bootstrapCarousel._config.interval = false;
            this._bootstrapCarousel.pause();
        } else {
            this._bootstrapCarousel._config.interval = this.interval;
            this._bootstrapCarousel.cycle();
        }
    },

    _readInterval() {
        const attr = (this.sectionEl && this.sectionEl.dataset.interval) || this.el.dataset.interval || this.el.dataset.bsInterval || "5000";
        const parsed = parseInt(attr, 10);
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
        if (this.prevButton) {
            this.prevButton.addEventListener("click", this._boundPrev);
        }
        if (this.nextButton) {
            this.nextButton.addEventListener("click", this._boundNext);
        }
    },

    _unbindNav() {
        if (this.prevButton) {
            this.prevButton.removeEventListener("click", this._boundPrev);
        }
        if (this.nextButton) {
            this.nextButton.removeEventListener("click", this._boundNext);
        }
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
