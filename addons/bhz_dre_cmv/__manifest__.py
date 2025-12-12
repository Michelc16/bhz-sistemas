{
    "name": "BHZ DRE + CMV",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "DRE com template configurável e geração mensal",
    "depends": ["account"],
    "data": [
        # segurança primeiro
        "security/security.xml",
        "security/ir.model.access.csv",

        # views (actions dentro do xml do wizard ou em action separado)
        "views/bhz_dre_template_views.xml",
        "views/bhz_dre_report_views.xml",
        "views/bhz_dre_wizard_views.xml",

        # report qweb + action do report
        "report/bhz_dre_report_templates.xml",
        "report/bhz_dre_report_action.xml",

        # menu por último (depende de actions já existirem)
        "views/bhz_dre_menu.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
