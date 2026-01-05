/** @odoo-module **/

import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class GuiabhFootballMatchesOption extends BaseOptionComponent {
    static template = "bhz_football_agenda.GuiabhFootballMatchesOption";
    static selector = ".s_guiabh_football_matches";
}

class GuiabhFootballMatchesOptionPlugin extends Plugin {
    static id = "guiabhFootballMatchesOption";
    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC, GuiabhFootballMatchesOption)],
    };
}

registry
    .category("website-plugins")
    .add(GuiabhFootballMatchesOptionPlugin.id, GuiabhFootballMatchesOptionPlugin);
