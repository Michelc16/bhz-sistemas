# BHZ Marketplace Suite (Odoo 19)

Ordem de instalação sugerida
1. `bhz_marketplace_core`
2. `bhz_marketplace_payouts`
3. `bhz_marketplace_shipping`
4. `bhz_marketplace_chat`
5. `bhz_marketplace_returns_disputes`
6. `bhz_marketplace_rank_ads`
7. `bhz_marketplace_connectors/bhz_connector_base`
8. `bhz_marketplace_connectors/bhz_connector_tiny`
9. `bhz_marketplace_connectors/bhz_connector_bling`
10. `bhz_marketplace_connectors/bhz_connector_omie`

Checklist de teste (sequencial)
- Core: criar seller, aprovar; gerar token; criar produto com seller, enviar/aprovar/publicar; criar pedido e ver sellers; portal produtos/pedidos; vitrine pública `/seller/<slug>`; APIs ping/upsert/list com header `X-BHZ-Marketplace-Token`.
- Payouts: confirmar pedido → ledger sale_credit + commission_debit; ver menus Financeiro; portal `/my/bhz/marketplace/payouts`; criar payout e marcar pago gera payout_debit.
- Shipping: confirmar pedido → shipments por seller; acompanhar em menus Logística e portal `/my/bhz/marketplace/shipments`.
- Chat/Q&A: perguntar em produto, listar perguntas do seller em portal `/my/bhz/marketplace/questions` e backend; responder/ocultar.
- Returns/Disputes: abrir caso (via dados internos), ver portal `/my/bhz/marketplace/returns`, aprovar reembolso gera refund_debit no ledger.
- Rank/Ads: cadastrar reputação e ads, conferir campo `bhz_rank_score` no produto.
- Conectores: criar conta ERP, criar job e executar (simulado) para Tiny/Bling/Omie; ver portal `/my/bhz/marketplace/connectors`.

Notas
- Não há dependências externas além do próprio Odoo (base, product, sale, website, portal, mail). Integrações dos conectores são simuladas.
- Grupos criados por módulo controlam acesso a menus, registros e portal.
