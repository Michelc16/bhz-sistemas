/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

const CarouselWidget = publicWidget.Widget.extend({
    selector: '.s_guiabh_featured_carousel',

    start() {
        this._initCarousel();
        return this._super.apply(this, arguments);
    },

    _initCarousel() {
        const carouselEl = this.el.querySelector('.carousel');
        if (!carouselEl || carouselEl.dataset.guiabhCarousel === '1') {
            return;
        }
        carouselEl.dataset.guiabhCarousel = '1';

        const interval = parseInt(carouselEl.dataset.bsInterval || '5000', 10);
        const ride = carouselEl.dataset.bsRide === 'carousel' ? 'carousel' : false;
        const wrap = carouselEl.dataset.bsWrap !== 'false';
        const pause = carouselEl.dataset.bsPause || false;
        const touch = carouselEl.dataset.bsTouch !== 'false';

        const BootstrapCarousel = window.bootstrap && window.bootstrap.Carousel;
        if (!BootstrapCarousel) {
            return;
        }
        new BootstrapCarousel(carouselEl, {
            interval,
            ride,
            wrap,
            pause,
            touch,
        });
    },
});

publicWidget.registry.BhzFeaturedCarousel = CarouselWidget;

export default CarouselWidget;
