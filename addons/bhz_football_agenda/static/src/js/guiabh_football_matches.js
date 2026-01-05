/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class GuiabhFootballMatches extends Interaction {
    static selector = ".s_guiabh_football_matches";

    setup() {
        this.isEditMode = !!this.el.closest(".o_editable");
        if (this.isEditMode) {
            return;
        }
        this.limit = parseInt(this.el.dataset.limit || "6", 10);
        this.gridEl = this.el.querySelector(".js-guiabh-football-grid");
        this.emptyEl = this.el.querySelector(".js-guiabh-football-empty");
        this.attrObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.attributeName === "data-team-ids") {
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
                attributeFilter: ["data-team-ids"],
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

    _parseTeamIds(rawValue) {
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
        const teamIds = this._parseTeamIds(this.el.dataset.teamIds);
        try {
            const payload = await rpc("/bhz_football/snippet/matches", {
                team_ids: teamIds,
                limit: this.limit,
            });
            if (!payload || this.isDestroyed) {
                return;
            }
            this._updateContent(payload);
        } catch (_err) {
            // Ignore RPC failures.
        }
    }

    _updateContent({ html, has_matches }) {
        if (typeof html === "string" && this.gridEl) {
            this.gridEl.innerHTML = html;
            this.services["public.interactions"].startInteractions(this.gridEl);
        }
        if (this.emptyEl) {
            this.emptyEl.classList.toggle("d-none", !!has_matches);
        }
    }
}

registry
    .category("public.interactions")
    .add("bhz_football_agenda.guiabh_football_matches", GuiabhFootballMatches);
registry.category("public.interactions.edit").add(
    "bhz_football_agenda.guiabh_football_matches",
    { Interaction: GuiabhFootballMatches }
);
