/** @odoo-module **/
odoo.define('bhz_event_promo.guiabh_featured_carousel', function (require) {
    'use strict';

    let publicWidget, rpc;
    try {
        publicWidget = require('web.public.widget');
        rpc = require('web.rpc');
    } catch (err) {
        // Minimal assets loaded; skip JS to avoid noisy errors.
        return;
    }

    publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
        selector: '.js-bhz-featured-carousel',
        disabledInEditableMode: false,

        async start() {
            this.sectionEl = this.el.closest(".s_guiabh_featured_carousel");
            this.carouselInner = this.el.querySelector(".js-bhz-featured-inner");
            this.indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
            this.prevButton = this.el.querySelector(".carousel-control-prev");
            this.nextButton = this.el.querySelector(".carousel-control-next");
            this.emptyMessage = this.sectionEl?.querySelector(".js-bhz-featured-empty");
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
                const payload = await rpc.query({
                    route: "/_bhz_event_promo/featured",
                    params,
                });
                if (!payload || this.isDestroyed) {
                    return;
                }
                this._applyPayload(payload);
            } catch (err) {
                // Fallback to empty payload to avoid breaking the page.
                this._applyPayload({
                    items_html: "",
                    indicators_html: "",
                    has_events: false,
                    has_multiple: false,
                });
            }
        },

        _applyPayload({ items_html, indicators_html, has_events, has_multiple }) {
            if (this.carouselInner && typeof items_html === "string") {
                this.carouselInner.innerHTML = items_html;
            }
            if (this.indicatorsWrapper && typeof indicators_html === "string") {
                this.indicatorsWrapper.innerHTML = indicators_html;
            }
            this.carouselInner = this.el.querySelector(".js-bhz-featured-inner");
            this.indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
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
            const hasMultipleActive = has_multiple && this.items.length > 1;
            if (this.emptyMessage) {
                this.emptyMessage.classList.toggle("d-none", hasEvents);
            }
            this.indicatorsWrapper?.classList.toggle("d-none", !hasMultipleActive);
            this.prevButton?.classList.toggle("d-none", !hasMultipleActive);
            this.nextButton?.classList.toggle("d-none", !hasMultipleActive);
            this._refreshCarousel(hasMultipleActive);
            this._applyIntervalToInstance();
            this._notifyContentChanged();
        },

        _refreshCarousel(has_multiple) {
            if (this._bootstrapCarousel) {
                this._bootstrapCarousel.dispose();
                this._bootstrapCarousel = null;
            }
            if (!has_multiple || !this.items.length) {
                return;
            }
            if (has_multiple && this.indicators.length < this.items.length) {
                return;
            }
            if (!window.bootstrap?.Carousel) {
                return;
            }
            const interval = has_multiple ? this.interval : false;
            this._bootstrapCarousel = new window.bootstrap.Carousel(this.el, {
                interval,
                ride: false,
                pause: "hover",
                wrap: true,
            });
            if (!interval) {
                this._bootstrapCarousel.pause();
            } else {
                this._bootstrapCarousel.cycle();
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
});
