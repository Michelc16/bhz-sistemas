/** @odoo-module **/
odoo.define("bhz_event_promo.guiabh_announced_events_option", [], function (require) {
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

    class GuiabhAnnouncedEventsOption extends BaseOptionComponent {
        static selector = ".s_guiabh_announced_events";
        static template = "bhz_event_promo.GuiabhAnnouncedEventsOption";

        setup() {
            super.setup(...arguments);
            this.limit = this._readLimit();
        }

        _readLimit() {
            const section = this.el || document.createElement("div");
            const raw = section.dataset?.limit || "12";
            const parsed = parseInt(raw, 10);
            if (Number.isNaN(parsed)) {
                return 12;
            }
            return Math.min(Math.max(parsed, 1), 24);
        }

        onLimitInput(ev) {
            const value = this._sanitize(ev.target.value);
            ev.target.value = value;
        }

        onLimitChange(ev) {
            const value = this._sanitize(ev.target.value);
            ev.target.value = value;
            this._applyLimit(value);
        }

        _sanitize(value) {
            const parsed = parseInt(value || "0", 10) || 0;
            return Math.min(Math.max(parsed, 1), 24);
        }

        _applyLimit(value) {
            const section = this.el;
            if (!section) {
                return;
            }
            const valStr = String(value);
            section.dataset.limit = valStr;
            section.dispatchEvent(
                new CustomEvent("change", {
                    bubbles: true,
                })
            );
            this.requestSave();
        }
    }

    class GuiabhAnnouncedEventsOptionPlugin extends Plugin {
        static id = "guiabhAnnouncedEventsOption";
        resources = {
            builder_options: [withSequence(SNIPPET_SPECIFIC, GuiabhAnnouncedEventsOption)],
        };
    }

    registry
        .category("website-plugins")
        .add(GuiabhAnnouncedEventsOptionPlugin.id, GuiabhAnnouncedEventsOptionPlugin);
});
