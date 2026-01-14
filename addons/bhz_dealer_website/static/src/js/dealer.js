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

  publicWidget.registry.BhzDealerFilters = publicWidget.Widget.extend({
    selector: ".bhz-filter-toggle",
    events: {
      "click": "_toggleFilters",
    },
    start() {
      this.$filters = this.$el.next(".bhz-filters");
      return this._super(...arguments);
    },
    _toggleFilters(ev) {
      ev.preventDefault();
      if (this.$filters && this.$filters.length) {
        this.$filters.toggleClass("is-open");
      }
    },
  });

  publicWidget.registry.BhzDealerFilterForm = publicWidget.Widget.extend({
    selector: ".bhz-filter-form",
    events: {
      "input [data-price-mask]": "_sanitizeNumber",
      "input [data-km-mask]": "_sanitizeNumber",
      "submit": "_cleanNumbers",
    },
    _sanitizeNumber(ev) {
      const $input = $(ev.currentTarget);
      const digits = ($input.val() || "").toString().replace(/\D/g, "");
      $input.val(digits);
    },
    _cleanNumbers(ev) {
      const $form = $(ev.currentTarget);
      $form.find("[data-price-mask],[data-km-mask]").each((_, el) => {
        const $el = $(el);
        const digits = ($el.val() || "").toString().replace(/\D/g, "");
        $el.val(digits);
      });
    },
  });

  publicWidget.registry.BhzDealerWhatsApp = publicWidget.Widget.extend({
    selector: ".bhz-dealer",
    start() {
      this._injectButton();
      return this._super(...arguments);
    },
    _injectButton() {
      const $body = $("body");
      const phone = $body.data("bhz-whatsapp") || this._guessPhone();
      if (!phone) {
        return;
      }
      const message = encodeURIComponent($body.data("bhz-whatsapp-msg") || "Olá, quero saber mais sobre os carros.");
      const url = `https://wa.me/${phone}?text=${message}`;
      const $btn = $(`
        <a class="bhz-floating-whatsapp" target="_blank" rel="noopener" aria-label="WhatsApp" href="${url}">
          <i class="fa fa-whatsapp"></i> Fale no WhatsApp
        </a>
      `);
      $("body").append($btn);
    },
    _guessPhone() {
      const meta = $('meta[name="whatsapp"]');
      if (meta.length) {
        return meta.attr("content");
      }
      return null;
    },
  });

  publicWidget.registry.BhzDealerLeadModal = publicWidget.Widget.extend({
    selector: "body",
    events: {
      "click .bhz-interest-btn": "_openModal",
      "submit #bhz-lead-form": "_submitLead",
      "submit .bhz-lead-form": "_submitInline",
    },
    _openModal(ev) {
      ev.preventDefault();
      const $btn = $(ev.currentTarget);
      const carId = $btn.data("car-id");
      const carName = $btn.data("car-name");
      let $modal = $("#bhz-lead-modal");
      if (!$modal.length) {
        $modal = $(`
          <div class="modal fade" id="bhz-lead-modal" tabindex="-1">
            <div class="modal-dialog">
              <div class="modal-content">
                <div class="modal-header">
                  <h5 class="modal-title">Tenho interesse</h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <form id="bhz-lead-form">
                  <div class="modal-body">
                    <input type="hidden" name="car_id" />
                    <input type="text" name="hp_field" class="d-none" aria-hidden="true" />
                    <div class="mb-2">
                      <label class="form-label">Nome</label>
                      <input type="text" name="name" class="form-control" required />
                    </div>
                    <div class="mb-2">
                      <label class="form-label">Telefone</label>
                      <input type="text" name="phone" class="form-control" />
                    </div>
                    <div class="mb-2">
                      <label class="form-label">E-mail</label>
                      <input type="email" name="email" class="form-control" />
                    </div>
                    <div class="mb-2">
                      <label class="form-label">Mensagem</label>
                      <textarea name="message" class="form-control" rows="3">Tenho interesse no carro.</textarea>
                    </div>
                  </div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Fechar</button>
                    <button type="submit" class="btn btn-primary">Enviar</button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        `);
        $("body").append($modal);
      }
      $modal.find("input[name='car_id']").val(carId || "");
      $modal.find("textarea[name='message']").val(`Tenho interesse no carro: ${carName || ""}`);
      if (window.bootstrap && window.bootstrap.Modal) {
        const modal = bootstrap.Modal.getOrCreateInstance($modal[0]);
        modal.show();
      } else {
        $modal.modal("show");
      }
    },
    async _submitInline(ev) {
      ev.preventDefault();
      const $form = $(ev.currentTarget);
      const data = this._collectData($form);
      if (!data.name) {
        alert("Informe seu nome.");
        return;
      }
      await this._sendLead($form, data);
    },
    async _submitLead(ev) {
      ev.preventDefault();
      const $form = $(ev.currentTarget);
      const data = this._collectData($form);
      await this._sendLead($form, data, true);
    },
    _collectData($form) {
      return {
        car_id: $form.find("[name='car_id']").val(),
        name: $form.find("[name='name']").val(),
        phone: $form.find("[name='phone']").val(),
        email: $form.find("[name='email']").val(),
        message: $form.find("[name='message']").val(),
        hp_field: $form.find("[name='hp_field']").val(),
        lead_type: $form.find("[name='lead_type']").val(),
        car_brand: $form.find("[name='car_brand']").val(),
        car_model: $form.find("[name='car_model']").val(),
        car_year: $form.find("[name='car_year']").val(),
        car_km: $form.find("[name='car_km']").val(),
      };
    },
    async _sendLead($form, data, closeModal = false) {
      const $submit = $form.find("button[type='submit']");
      $submit.prop("disabled", true).text("Enviando...");
      try {
        await ajax.jsonRpc("/carros/lead", "call", data);
        $form[0].reset();
        if (closeModal) {
          if (window.bootstrap && window.bootstrap.Modal) {
            bootstrap.Modal.getInstance($("#bhz-lead-modal")[0]).hide();
          } else {
            $("#bhz-lead-modal").modal("hide");
          }
        }
        alert("Recebemos seu interesse! Em breve entraremos em contato.");
      } catch (err) {
        console.error("Erro ao enviar lead", err);
        alert("Não foi possível enviar agora. Tente novamente.");
      } finally {
        $submit.prop("disabled", false).text("Enviar");
      }
    },
  });
});
