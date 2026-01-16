/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";

// Disable welcome message DOM manipulation to avoid replaceChildren/removeChild errors in builder.
patch(WebsiteBuilderClientAction.prototype, {
    async addWelcomeMessage() {
        return;
    },
});

// Guard resolveIframeLoaded to swallow any DOM errors originating from core builder.
const _originalResolveIframeLoaded = WebsiteBuilderClientAction.prototype.resolveIframeLoaded;
WebsiteBuilderClientAction.prototype.resolveIframeLoaded = function (...args) {
    try {
        return _originalResolveIframeLoaded ? _originalResolveIframeLoaded.apply(this, args) : undefined;
    } catch (err) {
        // Prevent editor crash when core tries to replaceChildren/removeChild on missing nodes.
        return;
    }
};

// Swallow DOM removeChild errors globally in builder context to avoid OwlError loops.
if (typeof window !== "undefined") {
    const originalOnError = window.onerror;
    window.onerror = function (message, source, lineno, colno, error) {
        const msg = (message || "").toString();
        const isRemoveChild = msg.includes("removeChild") && msg.includes("not a child");
        if (isRemoveChild) {
            return true; // mark as handled
        }
        if (originalOnError) {
            return originalOnError.apply(this, arguments);
        }
        return false;
    };
}
