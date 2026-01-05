/** @odoo-module **/

import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class GuiabhCineartMoviesOption extends BaseOptionComponent {
    static template = "bhz_cineart.GuiabhCineartMoviesOption";
    static selector = ".s_guiabh_cineart_movies";
}

class GuiabhCineartMoviesOptionPlugin extends Plugin {
    static id = "guiabhCineartMoviesOption";
    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC, GuiabhCineartMoviesOption)],
        on_snippet_dropped_handlers: (params) => this.onSnippetDropped(params),
    };

    onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches(GuiabhCineartMoviesOption.selector)) {
            return;
        }
        if (!snippetEl.dataset.limit) {
            snippetEl.dataset.limit = "8";
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
    .add(GuiabhCineartMoviesOptionPlugin.id, GuiabhCineartMoviesOptionPlugin);
