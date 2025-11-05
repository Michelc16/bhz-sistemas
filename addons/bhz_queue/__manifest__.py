{
    "name": "BHZ Queue",
    "summary": "Fila simples de jobs para integrações BHZ.",
    "version": "19.0.1.0.0",
    "author": "BHZ Sistemas",
    "website": "https://bhzsistemas.com.br",
    "category": "Technical",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/queue_job_views.xml",
    ],
    "installable": True,
    "application": False,
}
