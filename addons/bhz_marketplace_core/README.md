# BHZ Marketplace Core

Núcleo do marketplace multivendedor (Odoo 19).

Recursos:
- Seller com aprovação e KYC, API token por seller.
- Campos de marketplace em produtos e pedidos; aprovação publica no website.
- Portal do vendedor (/my/bhz/marketplace) para ver produtos e pedidos.
- Vitrine pública do seller em `/seller/<slug>`.
- APIs JSON com token `X-BHZ-Marketplace-Token`:
  - `/api/bhz/marketplace/ping`
  - `/api/bhz/marketplace/products/upsert`
  - `/api/bhz/marketplace/orders/list`

Ordem de teste rápida:
1. Criar Seller (draft) e aprovar.
2. Gerar token API do seller.
3. Cadastrar produto com seller e enviar para aprovação; aprovar e verificar publicação.
4. Criar pedido com linhas de produtos do seller; conferir sellers no pedido.
5. Acessar portal `/my/bhz/marketplace/products` e `/my/bhz/marketplace/orders`.
6. Acessar vitrine pública `/seller/<slug>`.
7. Chamar API ping e upsert/list com header do token.
