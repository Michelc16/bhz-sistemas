/** Lightweight carousel navigation for the highlights section. */
odoo.define("bhz_guiabh_website.theme_home", function () {
    "use strict";

    const scrollAmount = 320;

    const initCarousel = () => {
        const section = document.querySelector("[data-carousel]");
        if (!section) {
            return;
        }
        const track = section.querySelector("[data-carousel-track]");
        const prev = section.querySelector("[data-carousel-prev]");
        const next = section.querySelector("[data-carousel-next]");
        if (!(track && prev && next)) {
            return;
        }
        prev.addEventListener("click", () => {
            track.scrollBy({ left: -scrollAmount, behavior: "smooth" });
        });
        next.addEventListener("click", () => {
            track.scrollBy({ left: scrollAmount, behavior: "smooth" });
        });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initCarousel);
    } else {
        initCarousel();
    }
});
