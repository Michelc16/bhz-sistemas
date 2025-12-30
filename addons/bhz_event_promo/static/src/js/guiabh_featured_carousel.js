/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: '.s_guiabh_featured_carousel',

    start() {
        const carousel = this.el.querySelector('.carousel');
        if (carousel && !carousel.dataset.initialized) {
            carousel.dataset.initialized = '1';
            new bootstrap.Carousel(carousel, {
                interval: parseInt(carousel.dataset.bsInterval || '5000', 10),
                ride: 'carousel',
                pause: false,
                wrap: true,
            });
        }
        return this._super(...arguments);
    },
});
