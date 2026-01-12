# BHZ Web Fix

Compat de webclient para Odoo 19:
- Adiciona `_on_webclient_bootstrap` em `res.users` caso o core não tenha, evitando crash ao abrir `/web`.
- Se o método existir no core, delega para `super()`.

Quando remover:
- Quando sua base/versão já possuir `_on_webclient_bootstrap` nativo e o webclient abrir sem este módulo.

Como testar:
1) Instale/atualize o módulo `bhz_web_fix`.
2) Reinicie o servidor (se aplicável).
3) Acesse `/web` e verifique que o webclient abre sem `AttributeError` em `_on_webclient_bootstrap`.
