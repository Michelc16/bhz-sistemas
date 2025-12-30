/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: '.s_guiabh_featured_carousel',

    start() {
        this.carousel = this.el.querySelector('.carousel');
        if (!this.carousel || this.carousel.dataset.guiabhInitialized) {
            return this._super(...arguments);
        }
        this.carousel.dataset.guiabhInitialized = '1';
        this.items = Array.from(this.carousel.querySelectorAll('.carousel-item'));
        this.indicators = Array.from(this.carousel.querySelectorAll('[data-guiabh-slide-to]'));
        this.index = 0;
        this.wrap = this.carousel.dataset.guiabhWrap !== 'false';
        this.interval = parseInt(this.carousel.dataset.guiabhInterval || '5000', 10);
        this._bindControls();
        this._update();
        this._startAuto();
        return this._super(...arguments);
    },

    _bindControls() {
        const prev = this.carousel.querySelector('[data-guiabh-control="prev"]');
        const next = this.carousel.querySelector('[data-guiabh-control="next"]');
        if (prev) {
            prev.addEventListener('click', (ev) => {
                ev.preventDefault();
                this._move(-1);
            });
        }
        if (next) {
            next.addEventListener('click', (ev) => {
                ev.preventDefault();
                this._move(1);
            });
        }
        this.indicators.forEach((btn, idx) => {
            btn.addEventListener('click', (ev) => {
                ev.preventDefault();
                this.index = idx;
                this._update();
                this._restartAuto();
            });
        });
    },

    _startAuto() {
        if (this.interval <= 0 || this.items.length <= 1) {
            return;
        }
        this._timer = setInterval(() => this._move(1), this.interval);
    },

    _restartAuto() {
        if (this._timer) {
            clearInterval(this._timer);
            this._timer = null;
        }
        this._startAuto();
    },

    _move(step) {
        const len = this.items.length;
        let nextIdx = this.index + step;
        if (this.wrap) {
            nextIdx = (nextIdx % len + len) % len;
        } else {
            nextIdx = Math.min(Math.max(nextIdx, 0), len - 1);
        }
        this.index = nextIdx;
        this._update();
    },

    _update() {
        this.items.forEach((item, idx) => {
            item.classList.toggle('active', idx === this.index);
        });
        this.indicators.forEach((indicator, idx) => {
            indicator.classList.toggle('active', idx === this.index);
        });
    },
});
