// NOTE: Server-side now renders the slides; this JS is kept only for interval live update in the editor.
/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",
    disabledInEditableMode: false,

    async start() {
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel");
        this.interval = this._readInterval();
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
        await this._super(...arguments);
        this._refreshCarousel();
    },

    _refreshCarousel() {
        if (this._bootstrapCarousel) {
            this._bootstrapCarousel.dispose();
            this._bootstrapCarousel = null;
        }
        if (!window.bootstrap?.Carousel) {
            return;
        }
        const items = this.el.querySelectorAll(".carousel-item");
        if (!items.length) {
            return;
        }
        const interval = items.length > 1 ? this.interval : false;
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
        if (this.interval <= 0) {
            this._bootstrapCarousel._config.interval = false;
            this._bootstrapCarousel.pause();
        } else {
            this._bootstrapCarousel._config.interval = this.interval;
            this._bootstrapCarousel.cycle();
        }
    },

    _readInterval() {
        const attr = (this.sectionEl && this.sectionEl.dataset.interval) || this.el.dataset.interval || "5000";
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
