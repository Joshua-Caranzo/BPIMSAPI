""" Database configuration """

DATABASE_CONFIG = {
    'connections': {
        'default': 'mysql://root:NRtsEqqNGzErwvHgjeyExaxkQPlnUNad@maglev.proxy.rlwy.net:14138/railway',
    },
    'apps': {
        'models': {
            'models': ['models'], 
            'default_connection': 'default',
        }
    }
}
