/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: '.guiabh-featured-carousel',
    disabledInEditableMode: false,

    start() {
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel");
        this.carouselInner = this.el.querySelector('.carousel-inner');
        this.indicatorsWrapper = this.el.querySelector('.carousel-indicators');
        this.prevButton = this.el.querySelector('[data-action="prev"]');
        this.nextButton = this.el.querySelector('[data-action="next"]');
        this.emptyMessage = this.el.parentElement.querySelector('.js-guiabh-featured-empty');
        this.interval = this._readInterval();
        this.limit = parseInt(this.sectionEl?.dataset.limit || '12', 10);
        this.currentIndex = 0;
        this.items = [];
        this.indicators = [];
        this._bindControls();
        this._intervalListener = (ev) => {
            const newVal = parseInt(ev.detail?.interval, 10);
            if (Number.isNaN(newVal)) {
                return;
            }
            this.interval = newVal;
            this.el.dataset.interval = newVal;
            this.el.dataset.bsInterval = newVal;
            this._restartAutoplay();
        };
        this.el.addEventListener("guiabh-featured-interval-update", this._intervalListener);
        return Promise.all([this._fetchSlides(), this._super(...arguments)]);
    },

    async _fetchSlides() {
        const params = { limit: this.limit, carousel_id: this.el.id };
        try {
            const payload = await rpc("/bhz_event_promo/snippet/featured_events", params);
            if (!payload || this.isDestroyed) {
                return;
            }
            this._applyPayload(payload);
        } catch (err) {
            // Keep quiet on public pages; fallback message already exists.
            console.error("Failed to load featured events", err);
        }
    },

    _applyPayload({ slides, indicators, has_events, has_multiple }) {
        if (this.carouselInner && typeof slides === "string") {
            this.carouselInner.innerHTML = slides;
        }
        if (this.indicatorsWrapper && typeof indicators === "string") {
            this.indicatorsWrapper.innerHTML = indicators;
        }
        this.carouselInner = this.el.querySelector(".carousel-inner");
        this.indicatorsWrapper = this.el.querySelector(".carousel-indicators");
        this.prevButton = this.el.querySelector('[data-action="prev"]');
        this.nextButton = this.el.querySelector('[data-action="next"]');
        this.items = Array.from(this.carouselInner?.querySelectorAll(".carousel-item") || []);
        this.indicators = Array.from(this.indicatorsWrapper?.querySelectorAll("[data-slide-to]") || []);
        this.currentIndex = 0;

        if (this.emptyMessage) {
            this.emptyMessage.classList.toggle("d-none", !!has_events);
        }

        this.el.classList.toggle("is-js", !!has_events);
        this.indicatorsWrapper?.classList.toggle("d-none", !(has_events && has_multiple));
        this.prevButton?.classList.toggle("d-none", !(has_events && has_multiple));
        this.nextButton?.classList.toggle("d-none", !(has_events && has_multiple));

        if (this.items.length) {
            this._show(0);
            if (has_multiple) {
                this._restartAutoplay();
            } else if (this._timer) {
                clearInterval(this._timer);
            }
        } else {
            if (this._timer) {
                clearInterval(this._timer);
            }
        }

        this._notifyContentChanged();
    },

    _bindControls() {
        this._controlsHandler = (ev) => {
            const prev = ev.target.closest('[data-action="prev"]');
            if (prev && this.el.contains(prev)) {
                ev.preventDefault();
                this._show(this.currentIndex - 1);
                this._restartAutoplay();
                return;
            }
            const next = ev.target.closest('[data-action="next"]');
            if (next && this.el.contains(next)) {
                ev.preventDefault();
                this._show(this.currentIndex + 1);
                this._restartAutoplay();
                return;
            }
            const indicator = ev.target.closest('[data-slide-to]');
            if (indicator && this.indicators.includes(indicator)) {
                ev.preventDefault();
                const idx = this.indicators.indexOf(indicator);
                if (idx >= 0) {
                    this._show(idx);
                    this._restartAutoplay();
                }
            }
        };
        this.el.addEventListener('click', this._controlsHandler);
    },

    _startAutoplay() {
        if (this.interval <= 0 || this.items.length <= 1) {
            return;
        }
        this._timer = setInterval(() => this._show(this.currentIndex + 1), this.interval);
        if (this.bootstrapCarousel) {
            this.bootstrapCarousel.dispose();
        }
        if (window.Carousel) {
            this.bootstrapCarousel = window.Carousel.getOrCreateInstance(this.el, {
                interval: this.interval,
                ride: this.interval > 0 ? "carousel" : false,
            });
        }
    },

    _restartAutoplay() {
        if (this._timer) {
            clearInterval(this._timer);
        }
        this._startAutoplay();
    },

    _show(index) {
        if (!this.items.length) {
            return;
        }
        const newIndex = (index + this.items.length) % this.items.length;
        this.items.forEach((item, idx) => {
            item.classList.toggle("active", idx === newIndex);
        });
        this.indicators.forEach((indicator, idx) => {
            indicator.classList.toggle("active", idx === newIndex);
        });
        this.currentIndex = newIndex;
        if (this.bootstrapCarousel) {
            this.bootstrapCarousel.to(this.currentIndex);
        }
    },

    _notifyContentChanged() {
        this.el.dispatchEvent(new CustomEvent("content_changed", { bubbles: true }));
    },

    _readInterval() {
        const attr =
            (this.sectionEl && this.sectionEl.dataset.interval) ||
            this.el.dataset.interval ||
            "5000";
        const parsed = parseInt(attr, 10);
        const interval = Number.isNaN(parsed) ? 5000 : parsed;
        this.el.dataset.interval = interval;
        this.el.dataset.bsInterval = interval;
        if (interval > 0) {
            this.el.dataset.bsRide = "carousel";
        } else {
            this.el.dataset.bsRide = "false";
        }
        return interval;
    },

    destroy() {
        if (this._timer) {
            clearInterval(this._timer);
        }
        if (this.bootstrapCarousel) {
            this.bootstrapCarousel.dispose();
        }
        if (this._intervalListener) {
            this.el.removeEventListener("guiabh-featured-interval-update", this._intervalListener);
        }
        if (this._controlsHandler) {
            this.el.removeEventListener('click', this._controlsHandler);
        }
        return this._super(...arguments);
    },
});
