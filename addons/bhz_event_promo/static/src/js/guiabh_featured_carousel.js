/** @odoo-module **/

// Server-side already renders slides; JS keeps carousel stable (editor-safe) and optionally refreshes payload.
import publicWidget from "@web/legacy/js/public/public_widget";

const DEFAULT_REFRESH_MS = 60000; // polling only in public mode

publicWidget.registry.GuiabhFeaturedCarousel = publicWidget.Widget.extend({
    selector: ".js-bhz-featured-carousel",
    disabledInEditableMode: false,

    async start() {
        this.sectionEl = this.el.closest(".s_guiabh_featured_carousel");
        this.interval = this._readInterval();
        this.refreshMs = parseInt(this.sectionEl?.dataset.refresh || DEFAULT_REFRESH_MS, 10);
        this._intervalListener = (ev) => {
            const newVal = parseInt(ev.detail?.interval, 10);
            if (Number.isNaN(newVal)) {
                return;
            }
            this.interval = newVal;
            this.el.dataset.interval = newVal;
            this.el.dataset.bsInterval = newVal;
            this._applyIntervalToInstance();
        };
        this.el.addEventListener("guiabh-featured-interval-update", this._intervalListener);

        // Avoid auto-init before we control the DOM
        this.el.removeAttribute("data-bs-ride");

        await this._super(...arguments);
        await this._render(); // first render with existing server HTML

        if (!this.editableMode && this.refreshMs > 0) {
            this._pollTimer = setInterval(() => this._render(), this.refreshMs);
        }
    },

    async _render() {
        // In this implementation, slides are already server-rendered; just normalize and init bootstrap.
        this._disposeCarousel();
        this._ensureActives();
        this._toggleControls();
        this._initCarousel();
    },

    _disposeCarousel() {
        const existing = window.bootstrap?.Carousel?.getInstance?.(this.el);
        if (existing) {
            existing.dispose();
        }
        this._bootstrapCarousel = null;
    },

    _ensureActives() {
        const items = this.el.querySelectorAll(".carousel-item");
        if (items.length && !this.el.querySelector(".carousel-item.active")) {
            items[0].classList.add("active");
        }
        const indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
        const indicators = indicatorsWrapper ? indicatorsWrapper.querySelectorAll("button[data-bs-slide-to]") : [];
        if (indicators.length && !indicatorsWrapper.querySelector(".active")) {
            const first = indicatorsWrapper.querySelector('button[data-bs-slide-to="0"]') || indicators[0];
            first.classList.add("active");
            first.setAttribute("aria-current", "true");
        }
    },

    _toggleControls() {
        const items = this.el.querySelectorAll(".carousel-item");
        const multiple = items.length > 1;
        const prev = this.el.querySelector(".carousel-control-prev");
        const next = this.el.querySelector(".carousel-control-next");
        const indicatorsWrapper = this.el.querySelector(".js-bhz-featured-indicators");
        prev?.classList.toggle("d-none", !multiple);
        next?.classList.toggle("d-none", !multiple);
        if (indicatorsWrapper) {
            const hasButtons = indicatorsWrapper.querySelector("button");
            const classes = indicatorsWrapper.className.split(" ").filter(Boolean);
            const filtered = classes.filter((cls) => cls !== "carousel-indicators");
            if (multiple && hasButtons) {
                indicatorsWrapper.className = ["carousel-indicators", ...filtered].join(" ");
            } else {
                indicatorsWrapper.className = filtered.join(" ");
            }
            indicatorsWrapper.classList.toggle("d-none", !(multiple && hasButtons));
        }
        const emptyAlert = this.el.closest(".s_guiabh_featured_carousel")?.querySelector(".js-bhz-featured-empty");
        if (emptyAlert) {
            emptyAlert.classList.toggle("d-none", items.length > 0);
        }
    },

    _initCarousel() {
        const items = this.el.querySelectorAll(".carousel-item");
        if (!items.length || !window.bootstrap?.Carousel) {
            return;
        }
        const interval = items.length > 1 && !this.editableMode ? this.interval : false;
        this._bootstrapCarousel = new window.bootstrap.Carousel(this.el, {
            interval,
            ride: false,
            pause: this.editableMode ? true : "hover",
            touch: true,
            wrap: true,
        });
        if (interval) {
            this._bootstrapCarousel.cycle();
        } else {
            this._bootstrapCarousel.pause();
        }
    },

    _applyIntervalToInstance() {
        if (!this._bootstrapCarousel) {
            return;
        }
        if (this.interval <= 0) {
            this._bootstrapCarousel._config.interval = false;
            this._bootstrapCarousel.pause();
        } else {
            this._bootstrapCarousel._config.interval = this.interval;
            this._bootstrapCarousel.cycle();
        }
    },

    _readInterval() {
        const attr = (this.sectionEl && this.sectionEl.dataset.interval) || this.el.dataset.interval || this.el.dataset.bsInterval || "5000";
        const parsed = parseInt(attr, 10);
        const interval = Number.isNaN(parsed) ? 5000 : parsed;
        this.el.dataset.interval = interval;
        this.el.dataset.bsInterval = interval;
        return interval;
    },

    destroy() {
        if (this._pollTimer) {
            clearInterval(this._pollTimer);
        }
        this._disposeCarousel();
        if (this._intervalListener) {
            this.el.removeEventListener("guiabh-featured-interval-update", this._intervalListener);
        }
        return this._super(...arguments);
    },
});
