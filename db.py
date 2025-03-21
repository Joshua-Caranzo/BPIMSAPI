""" Database configuration """

DATABASE_CONFIG = {
    'connections': {
        'default': 'mysql://root:3x@c0nlt@localhost:3306/bpimsdb',
    },
    'apps': {
        'models': {
            'models': ['models'], 
            'default_connection': 'default',
        }
    }
}
