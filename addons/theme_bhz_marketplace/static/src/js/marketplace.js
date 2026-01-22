/**
 * JS leve para animações básicas no tema do marketplace.
 */
odoo.define('theme_bhz_marketplace.marketplace', function (require) {
  'use strict';
  const { loadCSS } = require('web.asset_utils');

  // Garantir carregamento do CSS (caso precise lazy load em certos builds)
  loadCSS('/theme_bhz_marketplace/static/src/css/marketplace.css');
});
