# GuiaBH Theme (Odoo 19)

Tema moderno para o site GuiaBH, aplicado apenas quando selecionado manualmente.

- Estrutura em `/views/theme/` com header, footer e home próprios (url `/theme/guiabh/home`).
- Bundle de assets dedicado (`theme_guiabh_website.assets_frontend`) com SCSS e JS leves; nada é injetado em sites existentes até que o tema seja escolhido.
- Nenhum backend ou herança de layouts existentes; pronto para evoluir com páginas adicionais e integração de conteúdo.
- App backend “GuiaBH” com modelos próprios (categorias, eventos, lugares, filmes, jogos, notícias), views list/form/kanban e menus seguros.
- Categorias publicadas geram páginas dinâmicas (`/<slug>`) com SEO automático, listas de conteúdo e menus/submenus criados sem intervenção manual.
- Rotina de automação via cron destaca conteúdos recentes, ordena por relevância/data e despublica itens expirados; templates mostram fallbacks quando faltam imagens/textos.
- SEO avançado: sitemap dinâmico, URLs limpas por slug, meta tags automáticas (OpenGraph), Schema.org por tipo (Event, Place, Movie, SportsEvent, Article) e breadcrumbs gerados com base nos dados.
