/**
 * JS leve para animações básicas no tema do marketplace.
 * Protegido para não rodar no backend (web client / Owl).
 */
odoo.define('theme_bhz_marketplace.marketplace', function (require) {
  'use strict';
  const body = document.body;
  const html = document.documentElement;

  // Não executa no backend do Odoo (web client) para evitar interferir no Owl.
  if ((body && body.classList.contains('o_web_client')) || (html && html.classList.contains('o_web_client'))) {
    return;
  }

  // Executa apenas em páginas do website.
  if (!body.classList.contains('o_website') && !html.classList.contains('o_website')) {
    return;
  }

  // Nenhuma manipulação de DOM para evitar conflitos com Owl/backend.
  // O CSS já é carregado via assets, então o JS permanece intencionalmente leve.
});
