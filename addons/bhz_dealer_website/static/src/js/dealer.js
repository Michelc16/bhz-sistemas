/** Melhoria de site e snippets para concessionária **/
odoo.define("bhz_dealer_website.dealer", function (require) {
  "use strict";

  const publicWidget = require("web.public.widget");
  const ajax = require("web.ajax");
  const options = require("web_editor.snippets.options");

  publicWidget.registry.BhzDealerGallery = publicWidget.Widget.extend({
    selector: ".bhz-detail-gallery",
    events: {
      "click img": "_onThumbClick",
    },
    _onThumbClick(ev) {
      const $thumb = $(ev.currentTarget);
      const src = $thumb.attr("src");
      if (!src) {
        return;
      }
      const $main = this.$el.closest(".bhz-detail").find(".bhz-detail-main img");
      if ($main.length) {
        $main.attr("src", src);
      }
    },
  });

  publicWidget.registry.BhzDealerCarShowcase = publicWidget.Widget.extend({
    selector: ".s_car_showcase",
    events: {
      "snippet-car-reload": "_renderCards",
    },
    start() {
      this._renderCards();
      return this._super(...arguments);
    },
    async _renderCards() {
      const mode = this.$el.data("mode") || "featured";
      const brand = this.$el.data("brand") || "";
      const limit = this.$el.data("limit") || 6;
      const $grid = this.$el.find(".bhz-showcase-grid");
      $grid.html('<div class="bhz-muted">Carregando...</div>');
      try {
        const data = await ajax.jsonRpc("/bhz_dealer/snippet/cars", "call", {
          mode,
          brand,
          limit,
        });
        $grid.html(data && data.html ? data.html : "<div class='alert alert-warning'>Sem dados.</div>");
      } catch (err) {
        console.warn("Erro ao carregar vitrine", err);
        $grid.html("<div class='alert alert-warning'>Não foi possível carregar os carros.</div>");
      }
    },
  });

  options.registry.BhzDealerCarShowcase = options.Class.extend({
    selectMode(previewMode, value) {
      this.$target.attr("data-mode", value || "featured");
      this._reload();
    },
    selectBrand(previewMode, value) {
      this.$target.attr("data-brand", value || "");
      this._reload();
    },
    selectLimit(previewMode, value) {
      this.$target.attr("data-limit", value || 6);
      this._reload();
    },
    onBuilt() {
      this._super(...arguments);
      this._reload();
    },
    cleanForSave() {
      // limpa cards antes de salvar para evitar conteúdo fixo
      this.$target.find(".bhz-showcase-grid").empty();
      return this._super(...arguments);
    },
    _reload() {
      this.$target.trigger("snippet-car-reload");
    },
  });
});
