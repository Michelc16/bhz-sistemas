/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: '.guiabh-featured-carousel',
    disabledInEditableMode: false,

    async start() {
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel");
        this.carouselInner = this.el.querySelector(".carousel-inner");
        this.indicatorsWrapper = this.el.querySelector(".carousel-indicators");
        this.controllerWrapper = this.el.querySelector(".o_carousel_controllers");
        this.prevButton = this.el.querySelector(".carousel-control-prev");
        this.nextButton = this.el.querySelector(".carousel-control-next");
        this.emptyMessage = this.el.parentElement.querySelector(".js-guiabh-featured-empty");
        this.limit = parseInt(this.sectionEl?.dataset.limit || "12", 10);
        this.interval = this._readInterval();
        this.items = [];
        this.indicators = [];
        this._intervalListener = (ev) => {
            const newVal = parseInt(ev.detail?.interval, 10);
            if (Number.isNaN(newVal)) {
                return;
            }
            this.interval = newVal;
            this.el.dataset.interval = newVal;
            this.el.dataset.bsInterval = newVal;
            this._applyIntervalToInstance();
        };
        this.el.addEventListener("guiabh-featured-interval-update", this._intervalListener);
        await Promise.all([this._fetchSlides(), this._super(...arguments)]);
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
        this.controllerWrapper = this.el.querySelector(".o_carousel_controllers");
        this.prevButton = this.el.querySelector(".carousel-control-prev");
        this.nextButton = this.el.querySelector(".carousel-control-next");
        this.items = Array.from(this.carouselInner?.querySelectorAll(".carousel-item") || []);
        this.indicators = Array.from(this.indicatorsWrapper?.querySelectorAll("button[data-bs-slide-to]") || []);
        if (this.items.length) {
            const hasActiveSlide = this.items.some((item) => item.classList.contains("active"));
            if (!hasActiveSlide) {
                this.items[0].classList.add("active");
            }
        }
        if (this.indicators.length) {
            const hasActiveIndicator = this.indicators.some((item) => item.classList.contains("active"));
            if (!hasActiveIndicator) {
                this.indicators[0].classList.add("active");
            }
        }

        const hasEvents = this.items.length > 0;
        const hasMultipleActive = this.items.length > 1;
        if (this.emptyMessage) {
            this.emptyMessage.classList.toggle("d-none", hasEvents);
        }
        this.indicatorsWrapper?.classList.toggle("d-none", !hasMultipleActive);
        this.prevButton?.classList.toggle("d-none", !hasMultipleActive);
        this.nextButton?.classList.toggle("d-none", !hasMultipleActive);
        this.controllerWrapper?.classList.toggle("d-none", !hasMultipleActive);

        this._refreshCarousel(hasMultipleActive);
        this._notifyContentChanged();
    },

    _refreshCarousel(has_multiple) {
        if (this._bootstrapCarousel) {
            this._bootstrapCarousel.dispose();
            this._bootstrapCarousel = null;
        }
        if (!this.items.length) {
            return;
        }
        if (window.bootstrap?.Carousel) {
            const interval = has_multiple ? this.interval : false;
            this._bootstrapCarousel = new window.bootstrap.Carousel(this.el, {
                interval,
                ride: false,
                pause: "hover",
                wrap: true,
            });
            if (!interval) {
                this._bootstrapCarousel.pause();
            }
        }
    },

    _applyIntervalToInstance() {
        if (!this._bootstrapCarousel) {
            return;
        }
        if (!this.items.length || this.items.length <= 1 || this.interval <= 0) {
            this._bootstrapCarousel._config.interval = false;
            this._bootstrapCarousel.pause();
        } else {
            this._bootstrapCarousel._config.interval = this.interval;
            this._bootstrapCarousel.cycle();
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
        this.el.dataset.bsRide = "false";
        return interval;
    },

    destroy() {
        if (this._bootstrapCarousel) {
            this._bootstrapCarousel.dispose();
        }
        if (this._intervalListener) {
            this.el.removeEventListener("guiabh-featured-interval-update", this._intervalListener);
        }
        return this._super(...arguments);
    },
});
