from datetime import datetime, timedelta


DATETIME_MAX = datetime.max - timedelta(microseconds=999)
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

API_BASE_URL = 'https://api.parse.com'
API_VERSION = '1'
API_CLASSES_PATH = 'classes'
API_BATCH_PATH = 'batch'
API_USERS_PATH = 'users'
API_LOGIN_PATH = 'login'
API_PASSWORD_RESET_PATH = 'requestPasswordReset'
API_ROLES_PATH = 'roles'
API_FILES_PATH = 'files'
API_EVENTS_PATH = 'events'
API_PUSH_PATH = 'push'
API_INSTALLATIONS_PATH = 'installations'
API_FUNCTIONS_PATH = 'functions'

CLASS_TYPE_USER = '_User'
CLASS_TYPE_ROLE = '_Role'
CLASS_TYPE_INSTALLATION = '_Installation'
CLASS_TYPES = (CLASS_TYPE_USER, CLASS_TYPE_ROLE, 
    CLASS_TYPE_INSTALLATION)

CLASS_PATHS = {
    CLASS_TYPE_USER: API_USERS_PATH,
    CLASS_TYPE_ROLE: API_ROLES_PATH,
    CLASS_TYPE_INSTALLATION: API_INSTALLATIONS_PATH
}

DEVICE_TYPE_IOS = "ios"
DEVICE_TYPE_ANDROID = "android"
DEVICE_TYPE_WINRT = "winrt"
DEVICE_TYPE_WINPHONE = "winphone"
DEVICE_TYPE_DOTNET = "dotnet"
DEVICE_TYPES = (DEVICE_TYPE_IOS, DEVICE_TYPE_ANDROID, DEVICE_TYPE_WINRT,
    DEVICE_TYPE_WINPHONE, DEVICE_TYPE_DOTNET)

QUERY_OPS = ('$lt', '$lte', '$gt', '$gte', '$ne', '$in', '$nin', '$exists',
    '$select', '$regex', '$all', '$inQuery', '$notInQuery', '$relatedTo',
    '$or')
QUERY_DEFAULT_LIMIT = 100
QUERY_MIN_LIMIT = 0
QUERY_MAX_LIMIT = 1000
QUERY_DEFAULT_SKIP = 0

RELATION_OPS = ('AddRelation', 'RemoveRelation')
RELATION_ROLE_KEYS = ('users', 'roles')

ACL_OPS = ('read', 'write')

ANALYTICS_EVENTS = ('AppOpened')
ANALYTICS_DIMENSION_LIMIT = 25

PUSH_IOS_KEYS = ('badge', 'sound', 'content-available')
PUSH_ANDROID_KEYS = ('action', 'title')

RESERVED_KEYS = ('objectId', 'createdAt', 'updatedAt' 'className', 'ACL',
    'sessionToken', '__type', '__op')

APPLICATIONS = {}
APPLICATION_NAME = None
APPLICATION_ID = None
REST_API_KEY = None
MASTER_KEY = None