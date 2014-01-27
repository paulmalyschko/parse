"""
Parse HTTP library
------------------

:Copyright (c) 2013-2014 Paul Malyschko
:Licenced under BSD

"""

__title__ = 'parse'
__version__ = '0.0.1'
__build__ = 0x010100
__author__ = 'Paul Malyschko'
__licence__ = 'BSD'
__copyright__ = 'Copyright (c) 2013-2014 Paul Malyschko'
__all__ = ['set_application', 'Object', 'User', 'Query', 'Relation',
    'ACL', 'Role', 'File', 'Analytics', 'Push', 'Installation', 'Cloud',
    'GeoPoint', 'ParseException', 'DATETIME_MAX', 'DATETIME_FORMAT']


from . import constants
from .constants import DATETIME_MAX, DATETIME_FORMAT
from .models import (Object, User, Query, Relation, ACL, Role, File, Analytics,
    Push, Installation, Cloud, GeoPoint)
from .exceptions import ParseException

application = None

def set_application(name, app_id=None, rest_api_key=None, master_key=None):
    """Set the Parse application details"""
    global application

    kwargs = {
        'app_id': app_id,
        'rest_api_key': rest_api_key, 
        'master_key': master_key
    }

    if name not in constants.APPLICATIONS:
        if not all((app_id, rest_api_key)):
            raise ValueError("Require app ID and REST API key")

        constants.APPLICATIONS[name] = kwargs
    else:
        kwargs = {k: v for (k, v) in kwargs.items() if v is not None}
        constants.APPLICATIONS[name].update(**kwargs)

    application = name
    app = constants.APPLICATIONS[name]
    constants.APPLICATION_NAME = name
    constants.APPLICATION_ID = app['app_id']
    constants.REST_API_KEY = app['rest_api_key']
    constants.MASTER_KEY = app['master_key']