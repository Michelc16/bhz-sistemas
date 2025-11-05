{
    'name': 'BHZ - Classificação do Parceiro',
    'version': '19.0.1.0.0',
    'summary': 'Classificação unificada de parceiros (Pessoa, Empresa, Fornecedor, Transportador)',
    'author': 'BHZ Sistemas Desenvolvimento e Tecnologia Ltda.',
    'website': 'https://bhzsistemas.com.br',
    'license': 'LGPL-3',
    'category': 'Contacts',
    'depends': [
        'base',
        'contacts',
        'purchase', 
    ],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
}
