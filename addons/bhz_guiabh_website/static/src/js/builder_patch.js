/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";

// Guard against missing homepage wrap element to avoid replaceChildren errors in builder.
patch(WebsiteBuilderClientAction.prototype, "bhz_guiabh_website.safe_welcome", {
    async addWelcomeMessage() {
        if (this.websiteService.isRestrictedEditor && !this.state.isEditing) {
            const doc = this.websiteContent?.el?.contentDocument;
            const wrapEl = doc && doc.querySelector("#wrapwrap.homepage #wrap");
            if (!wrapEl) {
                return;
            }
            if (!wrapEl.innerHTML.trim()) {
                this.welcomeMessageEl = this.welcomeMessageEl || document.createElement("div");
                wrapEl.replaceChildren(this.welcomeMessageEl);
            }
        }
    },
});
