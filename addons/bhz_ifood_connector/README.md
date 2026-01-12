# BHZ iFood Connector (Odoo 19)

Integração iFood para comércios alimentícios (restaurantes/food) no Odoo 19.

## O que este módulo faz (MVP)
- Cadastro de **Conta iFood** por empresa (multi-company)
- Recebe eventos via **Webhook** (endpoint `/ifood/webhook/<token>`)
- Armazena pedidos em `bhz.ifood.order`
- Permite **importar pedido para `sale.order`** (versão MVP)
- Permite criar **mapa de produtos** (SKU iFood -> product.product)

## Menus
- iFood > Contas
- iFood > Pedidos
- iFood > Mapa de Produtos

## Webhook
Rota:
- `POST /ifood/webhook/<account_token>`

Onde:
- `<account_token>` é o valor do campo `webhook_secret` da conta.
- Se o header `X-IFood-Signature` vier no request, o módulo tenta validar
  usando HMAC SHA256 com o `webhook_secret`.

> Recomendação: publique esse endpoint em HTTPS e use um proxy (NGINX / Odoo.sh) com rate limit.

## Polling (Cron)
Existe um cron de exemplo para buscar pedidos por janela (últimos 10 minutos).
Você pode usar cron como fallback caso o webhook esteja indisponível.

Arquivo:
- `data/ir_cron.xml`

## Próximos passos (produção)
- Implementar parse completo do payload (itens, adicionais, taxas, descontos, entrega)
- Implementar criação correta de linhas `sale.order.line` com base no mapa SKU
- Implementar atualização de status (aceitar/preparar/enviar/entregar) conforme a API
- Implementar logs técnicos e reprocessamento
- Implementar multi-merchant em modo integrador (SaaS) com autenticação centralizada

## Desenvolvimento
Estrutura:
- models/
- controllers/
- views/
- data/
- security/

## Autor
BHZ Sistemas
