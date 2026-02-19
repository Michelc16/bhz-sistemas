/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { withSequence } from "@html_editor/utils/resource";

class GuiabhFeaturedCarouselOption extends BaseOptionComponent {
    static selector = ".s_guiabh_featured_carousel";
    static template = "bhz_event_promo.GuiabhFeaturedCarouselOption";

    setup() {
        super.setup(...arguments);
        this._syncFromTarget();
    }

    _targetEl() {
        return this.props?.target || this.el;
    }

    _syncFromTarget() {
        const el = this._targetEl();
        this.interval = this._sanitizeInterval(el.getAttribute("data-interval") || "5000");
        this.refreshMs = parseInt(el.getAttribute("data-bhz-refresh-ms") || "0", 10) || 0;
        this.autoplay = (el.getAttribute("data-bhz-autoplay") || "true") !== "false";
    }

    _sanitizeInterval(value) {
        const ms = parseInt(value || "5000", 10);
        if (Number.isNaN(ms) || ms < 1000) return 1000;
        if (ms > 20000) return 20000;
        return ms;
    }

    _sanitizeRefresh(value) {
        const ms = parseInt(value || "0", 10);
        if (Number.isNaN(ms) || ms < 0) return 0;
        if (ms > 600000) return 600000;
        return ms;
    }

    _applyInterval(ms) {
        const el = this._targetEl();
        el.setAttribute("data-interval", String(ms));
        this.interval = ms;
    }

    _applyRefresh(ms) {
        const el = this._targetEl();
        el.setAttribute("data-bhz-refresh-ms", String(ms));
        this.refreshMs = ms;
    }

    _applyAutoplay(enabled) {
        const el = this._targetEl();
        el.setAttribute("data-bhz-autoplay", enabled ? "true" : "false");
        this.autoplay = enabled;
    }

    onIntervalInput(ev) {
        ev.target.value = String(this._sanitizeInterval(ev.target.value));
    }

    onIntervalChange(ev) {
        const ms = this._sanitizeInterval(ev.target.value);
        this._applyInterval(ms);
        ev.target.value = String(ms);
        this.requestSave();
    }

    onRefreshInput(ev) {
        ev.target.value = String(this._sanitizeRefresh(ev.target.value));
    }

    onRefreshChange(ev) {
        const ms = this._sanitizeRefresh(ev.target.value);
        this._applyRefresh(ms);
        ev.target.value = String(ms);
        this.requestSave();
    }

    onAutoplayToggle(ev) {
        this._applyAutoplay(ev.target.checked);
        this.requestSave();
    }
}

class GuiabhFeaturedCarouselOptionPlugin extends Plugin {
    static id = "guiabhFeaturedCarouselOption";
    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC, GuiabhFeaturedCarouselOption)],
        on_snippet_dropped_handlers: (params) => this.onSnippetDropped(params),
    };

    onSnippetDropped({ snippetEl }) {
        if (!snippetEl?.matches?.(GuiabhFeaturedCarouselOption.selector)) {
            return;
        }
        if (!snippetEl.dataset.limit) {
            snippetEl.dataset.limit = "12";
        }
        if (!snippetEl.dataset.interval) {
            snippetEl.dataset.interval = "5000";
        }
        if (!snippetEl.dataset.bhzRefreshMs) {
            snippetEl.dataset.bhzRefreshMs = "60000";
        }
        if (!snippetEl.dataset.bhzAutoplay) {
            snippetEl.dataset.bhzAutoplay = "true";
        }
    }
}

if (registry?.category) {
    registry
        .category("website-plugins")
        .add(GuiabhFeaturedCarouselOptionPlugin.id, GuiabhFeaturedCarouselOptionPlugin);
}
