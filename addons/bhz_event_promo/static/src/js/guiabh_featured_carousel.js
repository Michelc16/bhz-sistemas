/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: '.s_guiabh_featured_carousel',

    start() {
        const carouselEl = this.el.querySelector('.carousel');
        if (!carouselEl || carouselEl.dataset.guiabhInitialized) {
            return this._super(...arguments);
        }
        carouselEl.dataset.guiabhInitialized = '1';
        const interval = parseInt(carouselEl.dataset.bsInterval || '5000', 10);
        const ride = carouselEl.dataset.bsRide || 'carousel';
        const wrap = carouselEl.dataset.bsWrap !== 'false';
        const pause = carouselEl.dataset.bsPause || false;
        const touch = carouselEl.dataset.bsTouch !== 'false';
        if (window.bootstrap && window.bootstrap.Carousel) {
            new window.bootstrap.Carousel(carouselEl, {
                interval,
                ride,
                wrap,
                pause,
                touch,
            });
        }
        return this._super(...arguments);
    },
});
