/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class GuiabhAnnouncedEvents extends Interaction {
    static selector = ".s_guiabh_announced_events";

    setup() {
        this.limit = parseInt(this.el.dataset.limit || "12", 10);
        this.gridEl = this.el.querySelector(".js-guiabh-announced-grid");
        this.emptyEl = this.el.querySelector(".js-guiabh-announced-empty");
        this.categoryObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.attributeName === "data-category-ids") {
                    this.fetchAndRender();
                    break;
                }
            }
        });
    }

    start() {
        if (this.el.isConnected) {
            this.categoryObserver.observe(this.el, {
                attributes: true,
                attributeFilter: ["data-category-ids"],
            });
        }
        return this.fetchAndRender();
    }

    destroy() {
        if (this.categoryObserver) {
            this.categoryObserver.disconnect();
        }
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

    async fetchAndRender() {
        if (!this.gridEl) {
            return;
        }
        const params = {
            limit: this.limit,
            category_ids: this._getCategoryIds(),
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
