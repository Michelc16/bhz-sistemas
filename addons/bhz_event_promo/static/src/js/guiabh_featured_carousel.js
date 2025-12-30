/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: '.guiabh-featured-carousel',

    start() {
        this.items = Array.from(this.el.querySelectorAll('.carousel-item'));
        this.indicators = Array.from(this.el.querySelectorAll('[data-slide-to]'));
        this.currentIndex = 0;
        this.intervalMs = parseInt(this.el.dataset.interval || '5000', 10);
        if (this.items.length) {
            this.items[0].classList.add('active');
            if (this.indicators[0]) {
                this.indicators[0].classList.add('active');
            }
        }
        if (this.items.length > 1) {
            this._bindControls();
            this._startAutoplay();
        }
        return this._super(...arguments);
    },

    _bindControls() {
        const prev = this.el.querySelector('[data-action="prev"]');
        const next = this.el.querySelector('[data-action="next"]');
        prev && prev.addEventListener('click', (ev) => {
            ev.preventDefault();
            this._show(this.currentIndex - 1);
            this._restartAutoplay();
        });
        next && next.addEventListener('click', (ev) => {
            ev.preventDefault();
            this._show(this.currentIndex + 1);
            this._restartAutoplay();
        });
        this.indicators.forEach((indicator, idx) => {
            indicator.addEventListener('click', (ev) => {
                ev.preventDefault();
                this._show(idx);
                this._restartAutoplay();
            });
        });
    },

    _startAutoplay() {
        if (this.intervalMs <= 0) {
            return;
        }
        this._timer = setInterval(() => this._show(this.currentIndex + 1), this.intervalMs);
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
        this.items[this.currentIndex].classList.remove('active');
        if (this.indicators[this.currentIndex]) {
            this.indicators[this.currentIndex].classList.remove('active');
        }
        this.currentIndex = (index + this.items.length) % this.items.length;
        this.items[this.currentIndex].classList.add('active');
        if (this.indicators[this.currentIndex]) {
            this.indicators[this.currentIndex].classList.add('active');
        }
    },

    destroy() {
        if (this._timer) {
            clearInterval(this._timer);
        }
        return this._super(...arguments);
    },
});
