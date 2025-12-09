# -*- coding: utf-8 -*-
{
    "name": "BHZ DRE e CMV",
    "summary": "Demonstração do Resultado do Exercício com cálculo de CMV mensal",
    "description": """
Módulo de DRE e CMV baseado no modelo utilizado pela BHZ / Ventura.

- DRE configurável por linhas (template)
- Cálculo de CMV por período (mês) usando valuation de estoque
- Geração de relatório em formato parecido com a planilha enviada
    """,
    "author": "BHZ Sistemas",
    "website": "https://bhzsistemas.com.br",
    "license": "LGPL-3",
    "category": "Accounting",
    "version": "19.0.1.0.0",
    "depends": [
        "account",
        "stock",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/bhz_dre_menu.xml",
        "views/bhz_dre_template_views.xml",
        "views/bhz_dre_report_views.xml",
        "views/bhz_dre_wizard_views.xml",
        "report/bhz_dre_report_templates.xml",
    ],
    "application": True,
}
