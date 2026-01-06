/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class GuiabhAnnouncedEvents extends Interaction {
    static selector = ".s_guiabh_announced_events";

    setup() {
        this.isEditMode = this._isWebsiteEditorActive();
        if (this.isEditMode) {
            return;
        }
        this.limit = this._parseLimit(this.el.dataset.limit);
        this.orderMode = this._getOrderMode();
        this.gridEl = this.el.querySelector(".js-guiabh-announced-grid");
        this.emptyEl = this.el.querySelector(".js-guiabh-announced-empty");
        this.categoryObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (!mutation.attributeName) {
                    continue;
                }
                const attrName = mutation.attributeName;
                if (attrName === "data-category-ids") {
                    this.fetchAndRender();
                    break;
                }
                if (attrName === "data-limit") {
                    this.limit = this._parseLimit(this.el.dataset.limit);
                    this.fetchAndRender();
                    break;
                }
                if (attrName === "data-order-mode") {
                    this.orderMode = this._getOrderMode();
                    this.fetchAndRender();
                    break;
                }
            }
        });
    }

    start() {
        if (this.isEditMode) {
            return;
        }
        if (this.el.isConnected) {
            this.categoryObserver.observe(this.el, {
                attributes: true,
                attributeFilter: ["data-category-ids", "data-limit", "data-order-mode"],
            });
        }
        return this.fetchAndRender();
    }

    destroy() {
        if (this.categoryObserver) {
            this.categoryObserver.disconnect();
        }
        this.categoryObserver = null;
    }

    _parseCategoryEntry(entry) {
        if (typeof entry === "number") {
            return entry;
        }
        if (entry && typeof entry === "object") {
            return entry.id;
        }
        if (typeof entry === "string") {
            const numeric = parseInt(entry, 10);
            return Number.isNaN(numeric) ? false : numeric;
        }
        return false;
    }

    _getCategoryIds() {
        const raw = this.el.dataset.categoryIds;
        if (!raw) {
            return [];
        }
        try {
            const parsed = JSON.parse(raw);
            return parsed
                .map((entry) => this._parseCategoryEntry(entry))
                .filter((id) => Number.isInteger(id) && id > 0);
        } catch (_err) {
            return [];
        }
    }

    _parseLimit(value) {
        const base = parseInt(value || "12", 10);
        if (Number.isNaN(base)) {
            return 12;
        }
        return Math.min(Math.max(base, 1), 24);
    }

    _getOrderMode() {
        const allowed = ["recent", "popular"];
        const raw = (this.el.dataset.orderMode || "recent").toLowerCase();
        return allowed.includes(raw) ? raw : "recent";
    }

    async fetchAndRender() {
        if (this.isEditMode || !this.gridEl) {
            return;
        }
        this.limit = this._parseLimit(this.el.dataset.limit);
        this.orderMode = this._getOrderMode();
        const params = {
            limit: this.limit,
            category_ids: this._getCategoryIds(),
            order_mode: this.orderMode,
        };
        try {
            const result = await rpc("/bhz_event_promo/snippet/announced_events", params);
            if (this.isDestroyed || !result) {
                return;
            }
            this._updateContent(result);
        } catch (_err) {
            // Ignore RPC errors on public pages; snippet already has fallback content.
        }
    }

    _updateContent({ html, has_events }) {
        if (this.gridEl && typeof html === "string") {
            this.gridEl.innerHTML = html;
            const interactionsService = this.services && this.services["public.interactions"];
            if (interactionsService && interactionsService.startInteractions) {
                interactionsService.startInteractions(this.gridEl);
            }
        }
        if (this.emptyEl) {
            this.emptyEl.classList.toggle("d-none", !!has_events);
        }
    }

    _isWebsiteEditorActive() {
        const body = document.body;
        const html = document.documentElement;
        const hasEditorClass =
            body?.classList?.contains("editor_enable") ||
            body?.classList?.contains("o_web_editor") ||
            body?.classList?.contains("o_website_editor") ||
            html?.classList?.contains("o_web_editor") ||
            html?.classList?.contains("o_website_editor");
        const hasManipulator = !!document.getElementById("oe_manipulators");
        const hasEditableAncestor = !!this.el.closest(".o_editable, .oe_editable");
        return hasEditorClass || hasManipulator || hasEditableAncestor;
    }
}

registry
    .category("public.interactions")
    .add("bhz_event_promo.guiabh_announced_events", GuiabhAnnouncedEvents);

registry.category("public.interactions.edit").add(
    "bhz_event_promo.guiabh_announced_events",
    {
        Interaction: GuiabhAnnouncedEvents,
    }
);
