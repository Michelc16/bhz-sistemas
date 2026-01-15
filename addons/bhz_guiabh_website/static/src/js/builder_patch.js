/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";

// Guard against missing homepage wrap element to avoid replaceChildren errors in builder.
patch(WebsiteBuilderClientAction.prototype, {
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

// Extra defensive fallbacks in case the patch above is not applied early enough.
if (WebsiteBuilderClientAction && WebsiteBuilderClientAction.prototype) {
    const originalAddWelcome = WebsiteBuilderClientAction.prototype.addWelcomeMessage;
    WebsiteBuilderClientAction.prototype.addWelcomeMessage = async function () {
        try {
            return await originalAddWelcome.call(this);
        } catch (err) {
            // Swallow errors caused by missing wrap to keep the builder usable.
            return;
        }
    };

    const originalResolveIframeLoaded = WebsiteBuilderClientAction.prototype.resolveIframeLoaded;
    WebsiteBuilderClientAction.prototype.resolveIframeLoaded = function () {
        try {
            return originalResolveIframeLoaded.call(this);
        } catch (err) {
            // If any DOM hook fails (e.g., replaceChildren on null), ignore to keep builder alive.
            return;
        }
    };
}
