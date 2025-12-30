# BHZ Football Agenda – API

Envie jogos via HTTP POST para alimentar o modelo `bhz.football.match`.

## Endpoint

- URL: `/bhz/football/api/matches`
- Método: `POST`
- Autenticação: `Authorization: Bearer <TOKEN>`
- Conteúdo: `application/json`

### Exemplo `curl`

```bash
curl -X POST https://seu-odoo.com/bhz/football/api/matches \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
        "source": "bot-externo",
        "matches": [
          {
            "external_id": "BOT-CRU-AMG-20260110",
            "match_datetime": "2026-01-10 15:00:00",
            "competition": "Campeonato Mineiro",
            "round_phase": "1ª Fase",
            "home_team": "Cruzeiro",
            "away_team": "América-MG",
            "stadium": "Mineirão",
            "city": "Belo Horizonte (MG)",
            "broadcast": "Globo",
            "ticket_url": "https://ingressos.exemplo",
            "website_published": true,
            "active": true
          }
        ]
      }'
```

### Resposta

```json
{
  "created": 1,
  "updated": 0,
  "errors": []
}
```

### Configuração do Token

No backend, acesse **BHZ Futebol → Configurações** e defina o token que será enviado no header `Authorization`.
