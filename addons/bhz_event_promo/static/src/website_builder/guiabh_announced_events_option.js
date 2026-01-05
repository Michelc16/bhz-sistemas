/** @odoo-module **/

import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class GuiabhAnnouncedEventsOption extends BaseOptionComponent {
    static template = "bhz_event_promo.GuiabhAnnouncedEventsOption";
    static dependencies = ["dynamicSnippetOption"];
    static selector = ".s_guiabh_announced_events";

    setup() {
        super.setup();
        const { getModelNameFilter } = this.dependencies.dynamicSnippetOption;
        this.dynamicOptionParams = useDynamicSnippetOption(getModelNameFilter());
    }
}

class GuiabhAnnouncedEventsOptionPlugin extends Plugin {
    static id = "guiabhAnnouncedEventsOption";
    static dependencies = ["dynamicSnippetOption"];
    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, GuiabhAnnouncedEventsOption),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    getModelNameFilter() {
        return "event.event";
    }

    async onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches(GuiabhAnnouncedEventsOption.selector)) {
            return;
        }
        setDatasetIfUndefined(snippetEl, "limit", "12");
        setDatasetIfUndefined(snippetEl, "categoryIds", "[]");
        await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
            snippetEl,
            this.getModelNameFilter()
        );
    }
}

registry
    .category("website-plugins")
    .add(GuiabhAnnouncedEventsOptionPlugin.id, GuiabhAnnouncedEventsOptionPlugin);
