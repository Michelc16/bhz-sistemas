/** @odoo-module **/

import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class GuiabhAnnouncedEventsOption extends BaseOptionComponent {
    static template = "bhz_event_promo.GuiabhAnnouncedEventsOption";
    static selector = ".s_guiabh_announced_events";
}

class GuiabhAnnouncedEventsOptionPlugin extends Plugin {
    static id = "guiabhAnnouncedEventsOption";
    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC, GuiabhAnnouncedEventsOption)],
        on_snippet_dropped_handlers: (params) => this.onSnippetDropped(params),
    };

    onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches(GuiabhAnnouncedEventsOption.selector)) {
            return;
        }
        if (!snippetEl.dataset.limit) {
            snippetEl.dataset.limit = "12";
        }
        if (!snippetEl.dataset.categoryIds) {
            snippetEl.dataset.categoryIds = "[]";
        }
        if (!snippetEl.dataset.orderMode) {
            snippetEl.dataset.orderMode = "recent";
        }
    }
}

registry
    .category("website-plugins")
    .add(GuiabhAnnouncedEventsOptionPlugin.id, GuiabhAnnouncedEventsOptionPlugin);
