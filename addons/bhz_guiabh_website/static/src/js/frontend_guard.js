/** @odoo-module **/
(function () {
    // Swallow noisy removeChild errors that may bubble from Owl diffing on the public pages.
    if (typeof window === "undefined") {
        return;
    }

    const shouldIgnore = (message) => {
        const msg = (message || "").toString();
        return msg.includes("removeChild") && msg.includes("not a child");
    };

    const originalOnError = window.onerror;
    window.onerror = function (message, source, lineno, colno, error) {
        if (shouldIgnore(message)) {
            return true;
        }
        if (originalOnError) {
            return originalOnError.apply(this, arguments);
        }
        return false;
    };

    window.addEventListener(
        "unhandledrejection",
        (ev) => {
            const reason = ev && ev.reason ? ev.reason.message || ev.reason : "";
            if (shouldIgnore(reason)) {
                ev.preventDefault();
            }
        },
        { passive: true }
    );
})();
