/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class GuiabhCineartMovies extends Interaction {
    static selector = ".s_guiabh_cineart_movies";

    setup() {
        this.isEditMode = !!this.el.closest(".o_editable");
        if (this.isEditMode) {
            return;
        }
        this.limit = parseInt(this.el.dataset.limit || "8", 10);
        this.gridEl = this.el.querySelector(".js-guiabh-cineart-grid");
        this.emptyEl = this.el.querySelector(".js-guiabh-cineart-empty");
        this.attrObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.attributeName === "data-category-ids") {
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
            this.attrObserver.observe(this.el, {
                attributes: true,
                attributeFilter: ["data-category-ids"],
            });
        }
        return this.fetchAndRender();
    }

    destroy() {
        if (this.attrObserver) {
            this.attrObserver.disconnect();
        }
        this.attrObserver = null;
    }

    _parseIds(rawValue) {
        if (!rawValue) {
            return [];
        }
        try {
            const decoded = JSON.parse(rawValue);
            return decoded
                .map((entry) => {
                    if (typeof entry === "number") {
                        return entry;
                    }
                    if (entry && typeof entry === "object") {
                        return entry.id;
                    }
                    if (typeof entry === "string") {
                        const parsed = parseInt(entry, 10);
                        return Number.isNaN(parsed) ? false : parsed;
                    }
                    return false;
                })
                .filter((value) => Number.isInteger(value) && value > 0);
        } catch (_err) {
            return [];
        }
    }

    async fetchAndRender() {
        if (this.isEditMode || !this.gridEl) {
            return;
        }
        const categoryIds = this._parseIds(this.el.dataset.categoryIds);
        try {
            const payload = await rpc("/bhz_cineart/snippet/movies", {
                category_ids: categoryIds,
                limit: this.limit,
            });
            if (!payload || this.isDestroyed) {
                return;
            }
            this._updateContent(payload);
        } catch (_err) {
            // Ignore errors in public mode.
        }
    }

    _updateContent({ html, has_movies }) {
        if (this.gridEl && typeof html === "string") {
            this.gridEl.innerHTML = html;
            const interactionsService = this.services && this.services["public.interactions"];
            if (interactionsService && interactionsService.startInteractions) {
                interactionsService.startInteractions(this.gridEl);
            }
        }
        if (this.emptyEl) {
            this.emptyEl.classList.toggle("d-none", !!has_movies);
        }
    }
}

registry.category("public.interactions").add(
    "bhz_cineart.guiabh_cineart_movies",
    GuiabhCineartMovies
);
registry.category("public.interactions.edit").add(
    "bhz_cineart.guiabh_cineart_movies",
    { Interaction: GuiabhCineartMovies }
);
