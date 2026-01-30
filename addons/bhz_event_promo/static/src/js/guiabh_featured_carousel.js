/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

function _toInt(value, fallback) {
    const n = parseInt(value, 10);
    return Number.isNaN(n) ? fallback : n;
}

function _toBool(value, fallback) {
    if (value === true || value === false) return value;
    if (value === undefined || value === null || value === "") return fallback;
    const s = String(value).toLowerCase().trim();
    if (["1", "true", "yes", "y", "on"].includes(s)) return true;
    if (["0", "false", "no", "n", "off"].includes(s)) return false;
    return fallback;
}

/**
 * Detects Website Builder / Edit mode robustly.
 * We must NOT touch the DOM inside the editable iframe, otherwise Owl may crash
 * with: "removeChild: The node to be removed is not a child of this node."
 */
function isWebsiteEditor() {
    const loc = window.location;
    if (loc && loc.search && loc.search.includes("enable_editor=1")) return true;
    const body = document.body;
    const html = document.documentElement;
    const has = (el, cls) => !!el && el.classList && el.classList.contains(cls);

    // Common markers
    const markers = [
        "o_is_editing",
        "o_we_editing",
        "o_website_edit_mode",
        "editor_enable",
        "o_is_editable",
        "o_editable",
    ];
    if (markers.some((c) => has(body, c) || has(html, c))) return true;

    // Website builder UI elements
    if (document.querySelector(".o_we_toolbar, .o_we_sidebar, .o_website_editor, .o_we_customize_panel")) {
        return true;
    }

    // When inside iframe, parent often holds the toolbar
    try {
        if (window.top && window.top !== window) {
            const pdoc = window.top.document;
            if (pdoc && pdoc.querySelector(".o_we_toolbar, .o_we_sidebar, .o_website_editor, .o_we_customize_panel")) {
                return true;
            }
        }
    } catch (e) {
        // cross-origin? ignore
    }

    // Fallback: editor iframe endpoints
    if (loc && typeof loc.pathname === "string") {
        if (loc.pathname.startsWith("/website/")) return true;
    }

    return false;
}


// Remove DOM artifacts injected by browser auto-translate (e.g. nested <font> tags).
// These artifacts can break the website editor (Owl removeChild errors) because they
// change the DOM unexpectedly while the builder is patching.
function cleanupTranslateArtifacts(rootEl) {
    if (!rootEl) return;
    const fonts = rootEl.querySelectorAll("font[dir], font[style]");
    fonts.forEach((fontEl) => {
        // unwrap font tag: move its children before and remove it
        const parent = fontEl.parentNode;
        if (!parent) return;
        while (fontEl.firstChild) {
            parent.insertBefore(fontEl.firstChild, fontEl);
        }
        parent.removeChild(fontEl);
    });
}

function ensureActiveSlide(innerEl) {
    if (!innerEl) return;
    const items = innerEl.querySelectorAll(".carousel-item");
    if (!items.length) return;
    if ([...items].some((el) => el.classList.contains("active"))) return;
    items[0].classList.add("active");
}


function safeReplaceHtml(el, html) {
    if (!el) return;
    const tpl = document.createElement("template");
    tpl.innerHTML = html || "";
    // Atomic replacement reduces DOM churn and prevents editor patch conflicts.
    el.replaceChildren(...tpl.content.childNodes);
}

function setVisibility({ hasEvents, hasMultiple, prevBtn, nextBtn, indicatorsEl, emptyEl }) {
    if (emptyEl) emptyEl.classList.toggle("d-none", !!hasEvents);
    if (prevBtn) prevBtn.classList.toggle("d-none", !(hasEvents && hasMultiple));
    if (nextBtn) nextBtn.classList.toggle("d-none", !(hasEvents && hasMultiple));
    if (indicatorsEl) indicatorsEl.classList.toggle("d-none", !(hasEvents && hasMultiple));
}

/**
 * Bootstrap carousel init + safe fallback if bootstrap is not present.
 */
function startAutoplay({ carouselEl, intervalMs, hasMultiple }) {
    if (!carouselEl || !hasMultiple) return { stop() {} };

    // Prefer bootstrap if available
    const bs = window.bootstrap;
    if (bs && bs.Carousel) {
        // Force correct attributes even if saved as "false" in HTML
        carouselEl.setAttribute("data-bs-ride", "carousel");
        carouselEl.setAttribute("data-bs-interval", String(intervalMs));

        let inst = bs.Carousel.getInstance(carouselEl);
        if (!inst) {
            inst = new bs.Carousel(carouselEl, {
                interval: intervalMs,
                ride: "carousel",
                pause: false,
                touch: true,
                wrap: true,
            });
        } else {
            // update interval if possible
            try {
                inst._config.interval = intervalMs;
            } catch (e) {}
        }
        try {
            inst.cycle();
        } catch (e) {}
        return {
            stop() {
                try { inst.pause(); } catch (e) {}
            },
        };
    }

    // Fallback: manual slider
    let timer = window.setInterval(() => {
        const items = carouselEl.querySelectorAll(".carousel-item");
        if (!items.length) return;
        let activeIdx = -1;
        items.forEach((el, idx) => {
            if (el.classList.contains("active")) activeIdx = idx;
        });
        const nextIdx = activeIdx === -1 ? 0 : (activeIdx + 1) % items.length;

        if (activeIdx >= 0) items[activeIdx].classList.remove("active");
        items[nextIdx].classList.add("active");

        // indicators
        const indicators = carouselEl.querySelectorAll(".carousel-indicators [data-bs-slide-to], .carousel-indicators button");
        if (indicators.length) {
            indicators.forEach((b) => b.classList.remove("active"));
            if (indicators[nextIdx]) indicators[nextIdx].classList.add("active");
        }
    }, intervalMs);

    return { stop() { window.clearInterval(timer); } };
}

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".s_guiabh_featured_carousel",
    // This is the key to stop running inside the website editor
    disabledInEditableMode: false,

    start() {
        this._superStart = this._super.bind(this);
        this._refreshTimer = null;
        this._autoplayHandle = { stop() {} };

        // Always call super synchronously
        const superRes = this._superStart();

        // In the website editor, we avoid automatic DOM mutations (can break the builder),
        // but we provide a manual "refresh preview" button so the user doesn't need to delete/re-add the snippet.
        if (isWebsiteEditor()) {
            this._setupEditorPreview();
            return superRes;
        }

        this._setup();
        return superRes;
    },

    destroy() {
        try { this._clearTimers(); } catch (e) {}
        this._super.apply(this, arguments);
    },

    _clearTimers() {
        if (this._refreshTimer) {
            window.clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
        if (this._autoplayHandle) {
            try { this._autoplayHandle.stop(); } catch (e) {}
            this._autoplayHandle = { stop() {} };
        }
    },

    _setupEditorPreview() {
        // In Website Builder, avoid background timers/autoplay and only refresh when user clicks.
        const sectionEl = this.el;
        const carouselEl = sectionEl.querySelector(".js-bhz-featured-carousel");
        const innerEl = sectionEl.querySelector(".js-bhz-featured-inner");
        const indicatorsEl = sectionEl.querySelector(".js-bhz-featured-indicators");
        const emptyEl = sectionEl.querySelector(".js-bhz-featured-empty");
        const prevBtn = sectionEl.querySelector(".carousel-control-prev");
        const nextBtn = sectionEl.querySelector(".carousel-control-next");
        const refreshBtn = sectionEl.querySelector(".js-bhz-featured-refresh");

        if (!carouselEl || !innerEl) return;

        // Prevent browser translate artifacts from being serialized into the page arch.
        // Do it on next frame so the editor finishes initial patching first.
        window.requestAnimationFrame(() => {
            try { cleanupTranslateArtifacts(sectionEl); } catch (e) {}
        });

        const limit = _toInt(sectionEl.dataset.limit, 12);
        const intervalMs = _toInt(sectionEl.dataset.interval, 5000);
        const refreshMs = _toInt(sectionEl.dataset.bhzRefreshMs, 0);
        const autoplay = false; // always false in builder

        this._dom = { sectionEl, carouselEl, innerEl, indicatorsEl, emptyEl, prevBtn, nextBtn, refreshBtn };
        this._cfg = { limit, intervalMs, refreshMs, autoplay };

        if (refreshBtn) {
            refreshBtn.addEventListener("click", (ev) => {
                ev.preventDefault();
                ev.stopPropagation();

                // Refresh safely: update DOM in one atomic operation to avoid confusing the editor.
                refreshBtn.disabled = true;
                refreshBtn.classList.add("disabled");

                Promise.resolve()
                    .then(() => this._refresh({ force: true, safe: true }))
                    .catch(() => {})
                    .finally(() => {
                        refreshBtn.disabled = false;
                        refreshBtn.classList.remove("disabled");
                    });
            });
        }
    },

    _setup() {
        const sectionEl = this.el;
        const carouselEl = sectionEl.querySelector(".js-bhz-featured-carousel");
        const innerEl = sectionEl.querySelector(".js-bhz-featured-inner");
        const indicatorsEl = sectionEl.querySelector(".js-bhz-featured-indicators");
        const emptyEl = sectionEl.querySelector(".js-bhz-featured-empty");
        const prevBtn = sectionEl.querySelector(".carousel-control-prev");
        const nextBtn = sectionEl.querySelector(".carousel-control-next");

        if (!carouselEl || !innerEl) return;

        const limit = _toInt(sectionEl.dataset.limit, 12);
        const intervalMs = _toInt(sectionEl.dataset.interval, 5000);
        const refreshMs = _toInt(sectionEl.dataset.bhzRefreshMs, 60000);
        const autoplay = _toBool(sectionEl.dataset.bhzAutoplay, true);

        // Store for later
        this._dom = { sectionEl, carouselEl, innerEl, indicatorsEl, emptyEl, prevBtn, nextBtn };
        this._cfg = { limit, intervalMs, refreshMs, autoplay };

        return Promise.resolve(this._refresh())
            .then(() => {

        // Auto refresh
        if (refreshMs && refreshMs > 0) {
            this._refreshTimer = window.setInterval(() => {
                this._refresh();
            }, refreshMs);
        }

        // Autoplay
        if (autoplay) {
            this._autoplayHandle = startAutoplay({
                carouselEl,
                intervalMs,
                hasMultiple: !!this._hasMultiple,
            });
        }
            });
    },

    _refresh(opts = {}) {
        // Avoid automatic refresh in editor unless explicitly forced (preview button)
        if (isWebsiteEditor() && !opts.force) return Promise.resolve();

        const { carouselEl, innerEl, indicatorsEl, emptyEl, prevBtn, nextBtn } = this._dom || {};
        const { limit } = this._cfg || {};
        if (!carouselEl || !innerEl) return Promise.resolve();

        return rpc("/_bhz_event_promo/featured", {
            limit: limit || 12,
            carousel_id: carouselEl.getAttribute("id") || null,
        }).then((payload) => {
            const itemsHtml = (payload && (payload.items_html || payload.slides)) || "";
            const indicatorsHtml = (payload && (payload.indicators_html || payload.indicators)) || "";
            const hasEvents = !!(payload && payload.has_events);
            const hasMultiple = !!(payload && payload.has_multiple);

            // Update DOM
            if (opts.safe) { safeReplaceHtml(innerEl, itemsHtml); } else { innerEl.innerHTML = itemsHtml; }
            if (indicatorsEl) { if (opts.safe) { safeReplaceHtml(indicatorsEl, indicatorsHtml); } else { indicatorsEl.innerHTML = indicatorsHtml; } }

            // Toggle UI
            this._hasMultiple = hasMultiple;
            setVisibility({ hasEvents, hasMultiple, prevBtn, nextBtn, indicatorsEl, emptyEl });

            // Ensure first slide active (Bootstrap requirement)
            const firstItem = innerEl.querySelector(".carousel-item");
            if (firstItem && !innerEl.querySelector(".carousel-item.active")) {
                firstItem.classList.add("active");
            }
        }).catch(() => {
            // On failure, show empty
            innerEl.innerHTML = "";
            if (indicatorsEl) indicatorsEl.innerHTML = "";
            setVisibility({ hasEvents: false, hasMultiple: false, prevBtn, nextBtn, indicatorsEl, emptyEl });
        });
    },
});