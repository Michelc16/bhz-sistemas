# BHZ Event Promo – API de importação de eventos

Endpoints JSON (token obrigatório em `X-BHZ-Token: <token>` ou `Authorization: Bearer <token>`).

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/api/events/ping` | Verifica autenticação |
| POST | `/api/events/upsert` | Cria/atualiza evento único |
| POST | `/api/events/bulk_upsert` | Cria/atualiza em lote (`{"events": [...]}`) |
| GET | `/api/events/by_external/<source>/<external_id>` | Busca evento pela chave externa |

Configuração do token:
```bash
odoo shell -c odoo.conf -d DB -c "env['ir.config_parameter'].sudo().set_param('bhz_event_promo.api_token','SEU_TOKEN')"
```

Exemplo de upsert (cURL):
```bash
curl -X POST https://SEU_DOMINIO/api/events/upsert \
  -H "Content-Type: application/json" \
  -H "X-BHZ-Token: SEU_TOKEN" \
  -d '{
    "title": "Show de Verão",
    "start_datetime": "2026-02-10T20:00:00",
    "end_datetime": "2026-02-10T23:00:00",
    "timezone": "America/Sao_Paulo",
    "short_description": "Turnê 2026",
    "description_html": "<p>Lineup completo...</p>",
    "category": "Carnaval 2026",
    "organizer_name": "Produtora XYZ",
    "external_source": "sympla",
    "external_id": "abc123",
    "external_url": "https://sympla.com/abc123",
    "tickets_url": "https://ingressos.com/abc123",
    "image_url": "https://dominio.com/banner.jpg",
    "featured": true,
    "published": true
  }'
```

Exemplo bulk:
```bash
curl -X POST https://SEU_DOMINIO/api/events/bulk_upsert \
  -H "Content-Type: application/json" \
  -H "X-BHZ-Token: SEU_TOKEN" \
  -d '{"events": [ { "title": "...", "start_datetime": "2026-02-10T20:00:00", "timezone": "UTC", "external_source": "bot", "external_id": "1" } ]}'
```

Campos aceitos (principais):
- `title`, `start_datetime` (ISO 8601, obrigatório), `end_datetime` opcional, `timezone`
- `short_description`, `description_html`, `category`, `organizer_name`
- `external_source` (obrigatório), `external_id` (obrigatório), `external_url`
- `image_url` **ou** `image_base64`
- `featured` (bool), `published` (bool)
- `tickets_url` (gera inscrição externa), `website_id` opcional

Notas:
- Imagens até 5MB; suporta URL pública ou base64.
- Eventos publicados recebem `show_on_public_agenda` e `website_published` (se disponível); tenta posicionar em estágio “Anunciado” quando existir.
- Chave única `(external_source, external_id)` evita duplicados.
