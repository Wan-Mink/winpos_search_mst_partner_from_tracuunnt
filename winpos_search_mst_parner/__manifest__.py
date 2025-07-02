{
    'name': 'WinPOS Search MST Partner',
    'version': '1.0',
    'depends': ['base'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'winpos_search_mst_parner/static/src/js/auto_captcha.js',
        ],
    },
}