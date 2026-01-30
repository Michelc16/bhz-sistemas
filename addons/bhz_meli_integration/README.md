# BHZ Mercado Livre (Odoo 19)

## Configuração do app no Mercado Livre
- Redirect URIs obrigatórias: `https://www.bhzsistemas.com.br/meli/auth/callback` e os callbacks dos ambientes dev/odoo.sh (ex.: `https://<seu-env>.odoo.sh/meli/auth/callback`).
- Scopes mínimos: **Orders_v2** (pedidos) e **Itens/Catálogo** (produtos).
- URL de retornos de chamada de notificação: não é obrigatória para o cron/polling. Caso webhooks sejam configurados depois, aponte para `/meli/notifications`.

## Parâmetros no Odoo (por empresa)
Defina os parâmetros de sistema (Configurações > Técnico > Parâmetros de sistema), com a empresa correta selecionada:
- `bhz_meli.client_id`
- `bhz_meli.client_secret`
- `bhz_meli.redirect_uri` (mesma URI registrada no app)

## Testes rápidos
1. Crie uma `Conta Mercado Livre` e escolha a empresa certa.
2. Clique em **Conectar Mercado Livre** e conclua o OAuth. O registro deve ficar com estado `Conectado`, `ml_user_id` e `site_id` preenchidos.
3. Rode manualmente os agendamentos “BHZ ML: Buscar pedidos” e “BHZ ML: Buscar produtos” ou use os botões das listas.
4. Verifique os menus Pedidos ML e Produtos ML. Os campos `last_sync_*` e `last_error` na conta mostram diagnósticos; os logs do servidor listam URLs/status das chamadas e quantidades importadas.
