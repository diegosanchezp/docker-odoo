{
    'name': "regla_reabastecimiento_prioridad",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Diego Sánchez",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['product', 'stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        "views/product_view.xml",
        "views/stock_menu_views.xml",
        "data/ir_cron.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}

