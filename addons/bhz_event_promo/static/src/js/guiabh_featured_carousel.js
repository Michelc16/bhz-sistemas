/** @odoo-module **/

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".s_guiabh_featured_carousel .carousel").forEach(function (el) {
        if (!el.dataset.bsInterval) {
            el.dataset.bsInterval = "5000";
        }
        if (!el.dataset.bsRide) {
            el.dataset.bsRide = "carousel";
        }
        const interval = parseInt(el.dataset.bsInterval, 10) || 5000;
        new bootstrap.Carousel(el, {
            interval: interval,
            ride: el.dataset.bsRide === "carousel" ? "carousel" : false,
            wrap: true,
            pause: false,
            touch: true,
        });
    });
});
