/** @odoo-module **/

import { BaseOptionComponent } from "@website/builder/plugins/options";

export class GuiabhFeaturedCarouselOption extends BaseOptionComponent {
    static template = "bhz_event_promo.GuiabhFeaturedCarouselOption";

    setup() {
        super.setup();
        this._syncFromTarget();
    }

    // In the website builder, the selected snippet node is provided as props.target
    _targetEl() {
        return this.props?.target || this.el;
    }

    _syncFromTarget() {
        const el = this._targetEl();
        this.refreshMs = parseInt(el.getAttribute("data-bhz-refresh-ms") || "0", 10) || 0;
        this.autoplay = (el.getAttribute("data-bhz-autoplay") || "true") !== "false";
    }

    _sanitizeRefresh(value) {
        const ms = parseInt(value || "0", 10);
        if (isNaN(ms) || ms < 0) return 0;
        if (ms > 600000) return 600000;
        return ms;
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

    onRefreshChange(ev) {
        const ms = this._sanitizeRefresh(ev.target.value);
        this._applyRefresh(ms);
        this.env.editorBus.trigger("request_save");
    }

    onAutoplayChange(ev) {
        this._applyAutoplay(ev.target.checked);
        this.env.editorBus.trigger("request_save");
    }
}

export const guiabhFeaturedCarouselOption = {
    Component: GuiabhFeaturedCarouselOption,
};
