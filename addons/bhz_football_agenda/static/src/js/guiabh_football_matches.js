/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class GuiabhFootballMatches extends Interaction {
    static selector = ".s_guiabh_football_matches";

    setup() {
        this.isEditMode = this._isWebsiteEditorActive();
        this.limit = this._parseLimit(this.el.dataset.limit);
        this.orderMode = this._getOrderMode();
        this.gridEl = this.el.querySelector(".js-guiabh-football-grid");
        this.emptyEl = this.el.querySelector(".js-guiabh-football-empty");
        this.attrObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (!mutation.attributeName) {
                    continue;
                }
                const attrName = mutation.attributeName;
                if (attrName === "data-team-ids") {
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
        if (this.el.isConnected) {
            this.attrObserver.observe(this.el, {
                attributes: true,
                attributeFilter: ["data-team-ids", "data-limit", "data-order-mode"],
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

    _parseLimit(value) {
        const parsed = parseInt(value || "6", 10);
        if (Number.isNaN(parsed)) {
            return 6;
        }
        return Math.min(Math.max(parsed, 1), 24);
    }

    _getOrderMode() {
        const allowed = ["recent", "popular"];
        const raw = (this.el.dataset.orderMode || "recent").toLowerCase();
        return allowed.includes(raw) ? raw : "recent";
    }

    async fetchAndRender() {
        if (!this.gridEl) {
            return;
        }
        this.limit = this._parseLimit(this.el.dataset.limit);
        this.orderMode = this._getOrderMode();
        const teamIds = this._parseTeamIds(this.el.dataset.teamIds);
        try {
            const payload = await rpc("/bhz_football/snippet/matches", {
                team_ids: teamIds,
                limit: this.limit,
                order_mode: this.orderMode,
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
        if (this.gridEl && typeof html === "string") {
            this.gridEl.innerHTML = html;
            const interactionsService = this.services && this.services["public.interactions"];
            if (interactionsService && interactionsService.startInteractions) {
                interactionsService.startInteractions(this.gridEl);
            }
        }
        if (this.emptyEl) {
            this.emptyEl.classList.toggle("d-none", !!has_matches);
        }
        this._notifyContentChanged();
    }

    _isWebsiteEditorActive() {
        const body = document.body;
        const html = document.documentElement;
        const editClassHints = [
            "editor_enable",
            "o_web_editor",
            "o_website_editor",
            "o_edit_mode",
            "o_we_edit_mode",
            "o_editable_mode",
            "o_builder_edit_mode",
            "o_editable",
        ];
        const hasEditorClass = editClassHints.some(
            (cls) => body?.classList?.contains(cls) || html?.classList?.contains(cls)
        );
        const hasManipulator =
            !!document.getElementById("oe_manipulators") ||
            !!document.querySelector(".o_web_editor, .o_we_website_top_actions");
        const hasEditableAncestor = !!this.el.closest(
            ".o_editable, .oe_editable, .oe_structure, [contenteditable='true']"
        );
        return hasEditorClass || hasManipulator || hasEditableAncestor;
    }

    _notifyContentChanged() {
        if (!this._isWebsiteEditorActive()) {
            return;
        }
        this.el.dispatchEvent(
            new CustomEvent("content_changed", {
                bubbles: true,
            })
        );
    }
}

registry
    .category("public.interactions")
    .add("bhz_football_agenda.guiabh_football_matches", GuiabhFootballMatches);
registry.category("public.interactions.edit").add(
    "bhz_football_agenda.guiabh_football_matches",
    { Interaction: GuiabhFootballMatches }
);
