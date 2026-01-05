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
    };
}

registry
    .category("website-plugins")
    .add(GuiabhAnnouncedEventsOptionPlugin.id, GuiabhAnnouncedEventsOptionPlugin);
