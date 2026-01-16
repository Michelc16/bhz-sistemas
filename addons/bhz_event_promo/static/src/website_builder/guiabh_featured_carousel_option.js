/** @odoo-module **/
odoo.define("bhz_event_promo.guiabh_featured_carousel_option", [], function (require) {
    "use strict";

    let BaseOptionComponent, Plugin, SNIPPET_SPECIFIC, withSequence, registry;
    try {
        BaseOptionComponent = require("@html_builder/core/utils").BaseOptionComponent;
        Plugin = require("@html_editor/plugin").Plugin;
        SNIPPET_SPECIFIC = require("@html_builder/utils/option_sequence").SNIPPET_SPECIFIC;
        withSequence = require("@html_editor/utils/resource").withSequence;
        registry = require("@web/core/registry");
    } catch (err) {
        // If builder libs aren't available (public/minimal assets), skip safely.
        return;
    }

    class GuiabhFeaturedCarouselOption extends BaseOptionComponent {
        static selector = ".s_guiabh_featured_carousel";
        static template = "bhz_event_promo.GuiabhFeaturedCarouselOption";

        setup() {
            super.setup(...arguments);
            this.interval = this._readInterval();
        }

        _readInterval() {
            const section = this.el || document.createElement("div");
            const carousel = section.querySelector?.(".guiabh-featured-carousel");
            const raw = carousel?.dataset.interval || section.dataset?.interval || "5000";
            const parsed = parseInt(raw, 10);
            return Number.isNaN(parsed) ? 5000 : parsed;
        }

        onIntervalInput(ev) {
            const value = this._sanitize(ev.target.value);
            ev.target.value = value;
        }

        onIntervalChange(ev) {
            const value = this._sanitize(ev.target.value);
            ev.target.value = value;
            this._applyInterval(value);
        }

        _sanitize(value) {
            const parsed = parseInt(value || "0", 10) || 0;
            const clamped = Math.min(Math.max(parsed, 1000), 20000);
            return clamped;
        }

        _applyInterval(value) {
            const section = this.el;
            if (!section) {
                return;
            }
            const carousel = section.querySelector
                ? section.querySelector(".guiabh-featured-carousel")
                : null;
            const valStr = String(value);
            section.dataset.interval = valStr;
            if (carousel) {
                carousel.dataset.interval = valStr;
                carousel.dataset.bsInterval = valStr;
            }
            carousel?.dispatchEvent(
                new CustomEvent("guiabh-featured-interval-update", {
                    bubbles: true,
                    detail: { interval: value },
                })
            );
            this.requestSave();
        }
    }

    class GuiabhFeaturedCarouselOptionPlugin extends Plugin {
        static id = "guiabhFeaturedCarouselOption";
        resources = {
            builder_options: [withSequence(SNIPPET_SPECIFIC, GuiabhFeaturedCarouselOption)],
        };
    }

    registry
        .category("website-plugins")
        .add(GuiabhFeaturedCarouselOptionPlugin.id, GuiabhFeaturedCarouselOptionPlugin);
});
