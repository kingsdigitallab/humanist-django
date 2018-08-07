from .base import *  # noqa

ALLOWED_HOSTS = ['humanist.kdl.kcl.ac.uk']

INTERNAL_IPS = INTERNAL_IPS + ['']

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'app_humanist_liv',
        'USER': 'app_humanist',
        'PASSWORD': '',
        'HOST': ''
    },
}

SECRET_KEY = ''
