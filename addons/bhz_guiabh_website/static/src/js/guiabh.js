/** @odoo-module **/
import publicWidget from 'web.public.widget';
import ajax from 'web.ajax';
import options from 'website.snippets.options';

const GuiabhUtils = {
    formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr.replace(' ', 'T'));
            return date.toLocaleDateString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return dateStr;
        }
    },
    formatPrice(item, showPrice) {
        if (!showPrice) return '';
        if (item.price_type === 'free') {
            return '<span class="text-chip">Gratuito</span>';
        }
        if (item.price_type === 'paid' && item.min_price) {
            const symbol = item.currency_symbol || 'R$';
            return `<span class="text-chip">A partir de ${symbol}${item.min_price}</span>`;
        }
        return '';
    },
    renderEventCard(item, showPrice) {
        const price = GuiabhUtils.formatPrice(item, showPrice);
        return `
            <div class="guiabh-card">
                <div class="cover">
                    <img src="${item.cover}" alt="${item.name}" loading="lazy"/>
                    ${item.is_featured ? '<div class="badge">Destaque</div>' : ''}
                </div>
                <div class="content">
                    <div class="guiabh-meta"><i class="fa fa-calendar"></i><span>${GuiabhUtils.formatDate(item.start_datetime)}</span></div>
                    <h3>${item.name}</h3>
                    <div class="meta">
                        ${item.region ? `<span class="text-chip">${item.region}</span>` : ''}
                        ${item.category ? `<span class="text-chip">${item.category}</span>` : ''}
                    </div>
                    <p class="text-muted">${item.short_description || ''}</p>
                    <div class="footer">
                        ${price}
                        <a href="${item.url}" class="btn btn-link">Ver detalhes</a>
                    </div>
                </div>
            </div>`;
    },
    renderPlaceCard(item) {
        return `
            <div class="guiabh-card">
                <div class="cover">
                    <img src="${item.cover}" alt="${item.name}" loading="lazy"/>
                    ${item.is_featured ? '<div class="badge">Popular</div>' : ''}
                </div>
                <div class="content">
                    <div class="guiabh-meta"><i class="fa fa-map-marker"></i><span>${item.region || ''}</span></div>
                    <h3>${item.name}</h3>
                    <p class="text-muted">${item.short_description || ''}</p>
                    <div class="meta">
                        ${item.type ? `<span class="text-chip">${item.type}</span>` : ''}
                        ${item.price_range ? `<span class="text-chip">${item.price_range}</span>` : ''}
                    </div>
                    <div class="footer"><a href="${item.url}" class="btn btn-link">Saiba mais</a></div>
                </div>
            </div>`;
    },
};

publicWidget.registry.GuiabhChipFilter = publicWidget.Widget.extend({
    selector: '.js-guiabh-chip-filter',
    events: {
        'click .js-chip': '_onClick',
    },
    _onClick(ev) {
        ev.preventDefault();
        const $chip = $(ev.currentTarget);
        const param = $chip.data('param');
        const value = $chip.data('value');
        const baseUrl = this.$el.data('base-url') || window.location.pathname;
        const url = new URL(baseUrl, window.location.origin);
        if (param) {
            url.searchParams.set(param, value);
        }
        window.location = url.toString();
    },
});

publicWidget.registry.GuiabhDynamicSnippet = publicWidget.Widget.extend({
    selector: '.js-guiabh-dynamic',
    events: {
        reload: '_load',
    },
    start() {
        this._load();
        return this._super(...arguments);
    },
    _params() {
        const $section = this.$el.closest('[data-snippet]');
        const data = $section.data();
        const params = { limit: parseInt(data.limit) || 6 };
        if (data.showPrice === false || data.showPrice === 'false') {
            params.show_price = false;
        }
        if (data.categoryId) params.category_id = data.categoryId;
        if (data.regionId) params.region_id = data.regionId;
        if (data.placeTypeId) params.place_type_id = data.placeTypeId;
        if (data.tags) params.tags = data.tags;
        return params;
    },
    _load() {
        const type = this.$el.data('type');
        const layout = this.$el.data('layout') || 'grid';
        const params = this._params();
        const route = type === 'places' ? '/guiabh/snippet/places' : '/guiabh/snippet/events';
        const showPrice = params.show_price !== false;
        ajax.jsonRpc(route, 'call', params).then((data) => {
            this.$el.empty();
            const items = data && data.items ? data.items : [];
            if (!items.length) {
                this.$el.append('<p class="text-muted">Adicione conteúdo para preencher este bloco.</p>');
                return;
            }
            const html = items.map((item) => (type === 'places' ? GuiabhUtils.renderPlaceCard(item) : GuiabhUtils.renderEventCard(item, showPrice))).join('');
            if (layout === 'carousel') {
                this.$el.addClass('guiabh-carousel');
            }
            this.$el.append(html);
        }).catch(() => {
            this.$el.append('<p class="text-muted">Não foi possível carregar os cards.</p>');
        });
    },
});

options.registry.GuiabhEventsOptions = options.Class.extend({
    limit6() {
        this._setLimit(6);
    },
    limit9() {
        this._setLimit(9);
    },
    limit12() {
        this._setLimit(12);
    },
    togglePrice(previewMode, value) {
        this.$target.attr('data-show-price', value);
        this._refresh();
    },
    _setLimit(limit) {
        this.$target.attr('data-limit', limit);
        this._refresh();
    },
    _refresh() {
        this.$target.find('.js-guiabh-dynamic').trigger('reload');
    },
});

options.registry.GuiabhPlacesOptions = options.Class.extend({
    limit6() {
        this._setLimit(6);
    },
    limit9() {
        this._setLimit(9);
    },
    limit12() {
        this._setLimit(12);
    },
    _setLimit(limit) {
        this.$target.attr('data-limit', limit);
        this._refresh();
    },
    _refresh() {
        this.$target.find('.js-guiabh-dynamic').trigger('reload');
    },
});
