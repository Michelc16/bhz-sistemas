# BHZ GuiaBH Website

Módulo de site completo para o GuiaBH (eventos + lugares + guias) no Odoo 19, inspirado em experiências modernas de bilheteria mas com identidade própria.

## Principais recursos
- Modelos para eventos, lugares e taxonomias (regiões, categorias, tipos, tags) com slugs únicos por website.
- Rotas públicas: home, listagens e detalhes de eventos e lugares, guia do fim de semana e blocos JSON-LD para SEO/OG.
- Snippets editáveis (hero de busca, carrossel de destaque, grids de eventos/lugares, cards editoriais) com opções de quantidade e preço.
- Layout mobile-first com SCSS, chips de filtro, navbar sticky e imagens responsivas.
- Demo data: 6 regiões, 8 categorias de eventos, 6 tipos de lugar, 10 tags, 6 eventos e 6 lugares com placeholders locais.

## Instalação
1. Copie `addons/bhz_guiabh_website` para sua pasta de addons.
2. Atualize a lista de Apps e instale "BHZ GuiaBH Website" (categoria Website). Nenhuma dependência externa é necessária.
3. As páginas e menus são criados automaticamente; edite pelo Website Builder conforme desejar.

## Rotas públicas
- `/` – Home com hero de busca, destaques, próximos eventos, lugares e blocos editoriais.
- `/eventos` – Listagem com filtros por data (hoje/amanhã/fds), categoria, região, gratuitos/pagos, texto e ordenação.
- `/eventos/<slug>` – Detalhe do evento, CTA de ingressos e eventos relacionados (JSON-LD Event).
- `/lugares` – Listagem com filtros por tipo, região, tags e busca.
- `/lugares/<slug>` – Detalhe do lugar com eventos no local (JSON-LD LocalBusiness).
- `/guias/fim-de-semana` – Página editorial pronta para edição com sugestões do fim de semana.

## Snippets e edição
- Abra o Website Builder e arraste os snippets "Hero GuiaBH", "Eventos em destaque", "Grid de eventos", "Grid de lugares" e "Cards editoriais".
- Use as opções do painel (quantidade, mostrar/ocultar preço) para customizar; filtros via chips aplicam querystring automaticamente.
- Cards/carrosséis recarregam via JSON-RPC para respeitar os filtros e limites definidos.

## Notas
- Compatível com multi-website: slugs únicos por site e menus criados no website padrão, sem alterar temas existentes.
- SEO: meta tags dinâmicas, OpenGraph e JSON-LD nas páginas de detalhe.
- Performance: assets em bundles de frontend, imagens locais com lazy load e uso de `/web/image` para servir binários.
