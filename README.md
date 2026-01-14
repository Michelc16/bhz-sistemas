# bhz-sistemas

## Testes manuais - bhz_dealer_website
- Atualizar o módulo e habilitar Dealer no website alvo.
- Publicar carros com `website_published=True` e `website_id` do site.
- Acessar `/carros` e validar grid/filtros; sem carros deve exibir aviso.
- No backend, usar botão “Ver no Site” do carro e confirmar abertura sem 404.
- Abrir `/carros/<id>-<slug>` diretamente e confirmar respeito a `active`, `website_published` e `website_id`.
