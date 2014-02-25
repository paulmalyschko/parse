import datetime
import logging
import mimetypes
import re
import urllib
from numbers import Number

from . import parsejson as json
from . import utils
from .constants import (DATETIME_MAX, DATETIME_FORMAT, API_BASE_URL,
    API_VERSION, API_CLASSES_PATH, API_BATCH_PATH, API_USERS_PATH,
    API_LOGIN_PATH, API_PASSWORD_RESET_PATH, API_ROLES_PATH,
    API_FILES_PATH, API_EVENTS_PATH, API_PUSH_PATH,
    API_INSTALLATIONS_PATH, API_FUNCTIONS_PATH, CLASS_TYPES, 
    CLASS_PATHS, DEVICE_TYPE_IOS, DEVICE_TYPE_ANDROID,
    DEVICE_TYPE_WINRT, DEVICE_TYPE_WINPHONE, DEVICE_TYPE_DOTNET,
    DEVICE_TYPES, QUERY_OPS, QUERY_DEFAULT_LIMIT, QUERY_MIN_LIMIT,
    QUERY_MAX_LIMIT, QUERY_DEFAULT_SKIP, RELATION_OPS, RELATION_ROLE_KEYS,
    ACL_OPS, ANALYTICS_EVENTS, ANALYTICS_DIMENSION_LIMIT, PUSH_IOS_KEYS,
    PUSH_ANDROID_KEYS, RESERVED_KEYS)
from .exceptions import ParseException
from .utils import (build_headers, request, get, post, put, delete, 
    build_boolean_callback, build_integer_callback, build_object_callback,
    build_list_callback, build_bytes_callback)


class Object(dict):
    def __init__(self, *args, **kwargs):
        self._created_at = False
        self._updated_at = False
        self.has_geopoint = False
        self.dirty_keys = []
        
        if len(args) == 1:
            super(Object, self).__setitem__('__type', 'Object')
            super(Object, self).__setitem__('className', args[0])
            super(Object, self).update(**kwargs)
        elif len(args) == 2:
            if len(kwargs) > 0:
                raise ValueError("Pointer does not take keyword args")
            
            super(Object, self).__setitem__('__type', 'Pointer')
            super(Object, self).__setitem__('className', args[0])
            super(Object, self).__setitem__('objectId', args[1])
        else:
            msg = "Classname or classname and object id required"
            raise ValueError(msg)
        
        super(Object, self).update(**kwargs)
        
        for key in [k for k, v in self.items() if isinstance(v, Relation)]:
            self[key].instance = self
            self[key].key = key
    
    def __repr__(self):
        return json.dump(self)
    
    def __setitem__(self, key, value):
        if self.is_reserved(key):
            raise KeyError("Cannot set reserved key")
        
        if key == 'createdAt':
            self._created_at = False
        
        if key == 'updatedAt':
            self._updated_at = False
        
        # set parent and key for a relation so it can append/remove
        if isinstance(value, Relation):
            value.instance = self
            value.key = key

        if isinstance(value, File):
            if self.is_dirty():
                msg = "File must be uploaded before it can be set"
                raise ValueError(msg)

        if isinstance(value, GeoPoint):
            if self.has_geopoint:
                msg = "An object can only have one geopoint"
                raise ValueError(msg)
            self.has_geopoint = True

        super(Object, self).__setitem__(unicode(key), value)
        self.dirty(key)
    
    def __delitem__(self, key):
        if self.is_reserved(key):
            raise KeyError("Cannot delete reserved key")
        
        if key == 'createdAt':
            self._created_at = False

        if key == 'updatedAt':
            self._updated_at = False
        
        if isinstance(self[key], Relation):
            self[key].instance = None
            self[key].key = None

        if isinstance(self[key], GeoPoint):
            self.has_geopoint = False
        
        super(Object, self).__delitem__(unicode(key))
        self.dirty(key)
    
    def update(self, *args, **kwargs):
        if args and kwargs:
            msg = "Should be either a dictionary or keywords"
            raise ValueError(msg)
        
        if len(args) > 0:
            raise ValueError("Should only be a single dictionary")
        
        try:
            for key, value in args[0].items():
                self.__setitem__(key, value)
        except KeyError:
            for key, value in kwargs.items():
                self.__setitem__(key, value)
    
    def is_reserved(self, key):
        return key in RESERVED_KEYS or key[0] == '_'
    
    def is_dirty(self, key):
        return key in self.dirty_keys and not self.is_reserved(key)
    
    def dirty(self, key):
        if not self.is_dirty(key):
            self.dirty_keys.append(key)
    
    def clean(self, key=None):
        if key is not None:
            self.dirty_keys.remove(key)
        else:
            del self.dirty_keys[:]

    @property
    def object_id(self):
        return self['objectId'] if 'objectId' in self else None
    
    @property
    def created_at(self):
        if self._created_at is False:
            try:
                self._created_at = datetime.datetime.strptime(
                    self['createdAt'], DATETIME_FORMAT)
            except KeyError:
                self._created_at = None
        
        return self._created_at
    
    @property
    def updated_at(self):
        if self._updated_at is False:
            try:
                self._updated_at = datetime.datetime.strptime(
                    self['updatedAt'], DATETIME_FORMAT)
            except KeyError:
                self._updated_at = None
        
        return self._updated_at
    
    @property
    def class_name(self):
        return self['className'] if 'className' in self else None
    
    @property
    def ACL(self):
        return self['ACL'] if 'ACL' in self else None
    
    @ACL.setter
    def ACL(self, acl):
        self['ACL'] = acl
    
    def is_data_available(self):
        return self['__type'] == 'Pointer'
    
    def object_without_data(self):
        if self.object_id is None:
            return
        
        return Object(self.class_name, self.object_id)
    
    def build_url(self, object_id=False):
        paths = [API_BASE_URL, API_VERSION, API_CLASSES_PATH,
            self.class_name]
        
        if object_id and self.object_id is not None:
            paths.append(self.object_id)
        
        return '/'.join(paths)
    
    def build_relative_url(self, object_id=False):
        return self.build_url(object_id).replace(API_BASE_URL, '', 1)
    
    def handle_save_result(self, response, **kwargs):
        self.clean()
        super(Object, self).update(json.load(response.text))
        return True
    
    def build_save_args(self, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        saved = self.object_id is not None
        save_items = {k: self[k] for k in self.dirty_keys if k in self}
        del_items = {k: None for k in self.dirty_keys if k not in self}
        items = dict(save_items.items() + del_items.items())

        url = self.build_url(saved)
        method = 'POST' if not saved else 'PUT'
        headers = build_headers(master_key=ignore_acl)
        data = json.dump(items)

        if callback is not None:
            callback = build_boolean_callback(self.handle_save_result,
                callback=callback, **kwargs)

        return (method, url, {'headers': headers, 'data': data,
            'callback': callback})

    def save(self, **kwargs):
        method, url, kwargs = self.build_save_args(**kwargs)
        return self.handle_save_result(request(method, url, **kwargs))
    
    def save_in_background(self, **kwargs):
        method, url, kwargs = self.build_save_args(**kwargs)
        return request(method, url, **kwargs)
    
    def handle_refresh_result(self, response, **kwargs):
        self.clean()
        super(Object, self).update(json.load(response.text, self.class_name))
        return self
    
    def build_refresh_args(self, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        url = self.build_url(True)
        headers = build_headers(master_key=ignore_acl)

        if callback is not None:
            callback = build_object_callback(self.handle_refresh_result,
                callback=callback, **kwargs)
        
        return (url, {'headers': headers, 'callback': callback})

    def refresh(self, **kwargs):
        url, kwargs = self.build_refresh_args(**kwargs)
        self.handle_refresh_result(get(url, **kwargs))
    
    def refresh_in_background(self, **kwargs):
        url, kwargs = self.build_refresh_args(**kwargs)
        return get(url, **kwargs)
    
    def fetch(self, **kwargs):
        self.refresh(**kwargs)
    
    def fetch_in_background(self, **kwargs):
        return self.refresh_in_background(**kwargs)
    
    def handle_delete_result(self, response, **kwargs):
        self.clean()
        for key in ('objectId', 'createdAt', 'updatedAt'):
            super(Object, self).__delitem__(key)
        return True
    
    def build_delete_args(self, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        url = build_url(True)
        headers = build_headers(master_key=ignore_acl)

        if callback is not None:
            callback = build_boolean_callback(self.handle_delete_result,
                callback=callback, **kwargs)
        
        return (url, {'headers': headers, 'callback': callback})

    def delete(self, **kwargs):
        url, kwargs = self.build_delete_args(**kwargs)
        return self.handle_delete_result(delete(url, **kwargs))
    
    def delete_in_background(self, **kwargs):
        url, kwargs = self.build_delete_args(**kwargs)
        return delete(url, **kwargs)

    def increment(self, key, amt=1, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        url = self.build_url(True)
        headers = build_headers(master_key=ignore_acl)
        data = json.dump({key: {'__op': 'Increment', 'amount': amt}})
        put(url, headers=headers, data=data)
    
    def add_objects_to_array(self, key, objs, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        url = self.build_url(True)
        headers = build_headers(master_key=ignore_acl)
        data = json.dump({key: {'__op': 'Add', 'objects': objs}})
        put(url, headers=headers, data=data)
        self[key] = self[key] + objs
    
    def add_unique_objects_to_array(self, key, objs, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        url = self.build_url(True)
        headers = build_headers(master_key=ignore_acl)
        data = json.dump({key: {'__op': 'AddUnique', 'objects': objs}})
        put(url, headers=headers, data=data)
        self[key] = list({obj for obj in (self[key] + objs)})
                
    def remove_objects_from_array(self, key, objs, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        url = self.build_url(True)
        headers = build_headers(master_key=ignore_acl)
        data = json.dump({key: {'__op': 'Remove', 'objects': objs}})
        put(url, headers=headers, data=data)
        for obj in objs:
            self[key].remove(obj)
    
    @staticmethod
    def build_batch_url():
        paths = [API_BASE_URL, API_VERSION, API_BATCH_PATH]
        return '/'.join(paths)
    
    def build_batch_save_data(self):
        saved = self.object_id is not None
        return {
            'method': 'POST' if not saved else 'PUT',
            'path': self.build_relative_url(saved),
            'body': {k: self[k] for k in self.dirty_keys}
        }
    
    @staticmethod
    def handle_batch_save_result(response, **kwargs):
        objs = kwargs.pop('objs', None)
        errors = []
        for (obj, result) in zip(objs, json.load(response.text)):
            if 'success' in result:
                obj.clean()
                super(Object, obj).update(result['success'])
            elif 'error' in result:
                errors.append(result['error'])
            else:
                msg = "No success or error values in batch save"
                raise ValueError(msg)

        return len(errors) == 0

    @staticmethod
    def build_batch_save_args(**kwargs):
        objs = kwargs.pop('objs', None)
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)
        requests = [obj.build_batch_save_data() for obj in objs]

        url = Object.build_batch_url()
        headers = build_headers(master_key=ignore_acl)
        data = json.dump({'requests': requests})

        if callback is not None:
            callback = build_boolean_callback(
                Object.handle_batch_save_result, objs=objs,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback': callback})

    @staticmethod
    def save_all(objs, **kwargs):
        url, kwargs = Object.build_batch_save_args(**kwargs)
        return Object.handle_batch_save_result(post(url, **kwargs),
            objs=objs)
    
    @staticmethod
    def save_all_in_background(objs, **kwargs):
        url, kwargs = Object.build_batch_save_args(objs=objs, **kwargs)
        return post(url, **kwargs)
    
    def build_batch_refresh_data(self):
        return {
            'method': 'GET',
            'path': self.build_relative_url(True),
            'body': {k: self[k] for k in self.dirty_keys}
        }

    @staticmethod
    def handle_batch_refresh_result(response, **kwargs):
        objs = kwargs.pop('objs', None)
        errors = []
        for (obj, result) in zip(objs, json.load(response.text)):
            if 'success' in result:
                obj.clean()
                super(Object, obj).update(result['success'])
            elif 'error' in result:
                errors.append(result['error'])
            else:
                msg = "No success or error values in batch save"
                raise ValueError(msg)

        return len(errors) == 0

    @staticmethod
    def build_batch_refresh_args(**kwargs):
        objs = kwargs.pop('objs', None)
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)
        requests = [obj.build_batch_refresh_data() for obj in objs]

        url = Object.build_batch_url()
        headers = build_headers(master_key=ignore_acl)
        data = json.dump({'requests': requests})

        if callback is not None:
            callback = build_boolean_callback(
                Object.handle_batch_refresh_result, objs=objs,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback': callback})

    @staticmethod
    def refresh_all(objs, **kwargs):
        url, kwargs = Object.build_batch_refresh_args(**kwargs)
        return Object.handle_batch_refresh_result(post(url, **kwargs),
            objs=objs)
    
    @staticmethod
    def refresh_all_in_background(objs, **kwargs):
        url, kwargs = Object.build_batch_refresh_args(objs=objs,
            **kwargs)
        return post(url, **kwargs)
    
    @staticmethod
    def fetch_all(objs, **kwargs):
        return self.refresh_all(objs, **kwargs)
    
    @staticmethod
    def fetch_all_in_background(objs, **kwargs):
        return self.refresh_all_in_background(objs, **kwargs)

    def build_batch_delete_data(self):
        return {
            'method': 'DELETE',
            'path': self.build_relative_url(True),
            'body': {k: self[k] for k in self.dirty_keys}
        }

    @staticmethod
    def handle_batch_delete_result(response, **kwargs):
        objs = kwargs.pop('objs', None)
        errors = []
        for (obj, result) in zip(objs, json.load(response.text)):
            if 'success' in result:
                obj.clean()
                for key in ('objectId', 'createdAt', 'updatedAt'):
                    super(Object, obj).__delitem__(key)
            elif 'error' in result:
                errors.append(result['error'])
            else:
                msg = "No success or error values in batch save"
                raise ValueError(msg)

        return len(errors) == 0

    @staticmethod
    def build_batch_delete_args(**kwargs):
        objs = kwargs.pop('objs', None)
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)
        requests = [obj.build_batch_delete_data() for obj in objs]

        url = Object.build_batch_url()
        headers = build_headers(master_key=ignore_acl)
        data = json.dump({'requests': requests})
        
        if callback is not None:
            callback = build_boolean_callback(
                Object.handle_batch_delete_result, objs=objs,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback': callback})

    @staticmethod
    def delete_all(objs, **kwargs):
        url, kwargs = Object.build_batch_delete_args(objs=objs, **kwargs)
        return Object.handle_batch_delete_result(post(url, **kwargs),
            objs=objs)
    
    @staticmethod
    def delete_all_in_background(objs, **kwargs):
        url, kwargs = Object.build_batch_delete_args(objs=objs,
            **kwargs)
        return post(url, **kwargs)

class User(Object):
    def __init__(self, **kwargs):
        super(User, self).__init__('_User', *args, **kwargs)

    @property
    def username(self):
        return self['username'] if 'username' in self else None

    @username.setter
    def username(self, username):
        self['username'] = username

    @property
    def password(self):
        return self['password'] if 'password' in self else None

    @password.setter
    def password(self, password):
        self['password'] = password

    @property
    def email(self):
        return self['email'] if 'email' in self else None

    @email.setter
    def email(self, email):
        self['email'] = email

    @property
    def session_token(self):
        return self['sessionToken'] if 'sessionToken' in self else None

    def is_authenticated(self):
        return self.session_token is not None

    def build_url(self, object_id=False):
        paths = [API_BASE_URL, API_VERSION, API_USERS_PATH]

        if object_id and self.object_id is not None:
            paths.append(self.object_id)

        return '/'.join(paths)
    
    @staticmethod
    def build_login_url(self):
        paths = [API_BASE_URL, API_VERSION, API_LOGIN_PATH]
        return '/'.join(paths)
    
    def build_password_reset_url(self):
        paths = [API_BASE_URL, API_VERSION, API_PASSWORD_RESET_PATH]
        return '/'.join(paths)
    
    def sign_up(self):
        return self.save()

    def sign_up_in_background(self, **kwargs):
        return self.save_in_background(**kwargs)
    
    @staticmethod
    def build_login_args(user, username, password, **kwargs):
        callback = kwargs.pop('callback', None)

        url = self.build_login_url()
        headers = build_headers()
        data = urllib.urlencode({'username': username,
            'password': password})

        if callback is not None:
            callback = build_boolean_callback(User.handle_login_result,
                objs=user, callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback':
            callback})

    @staticmethod
    def handle_login_result(response, **kwargs):
        user = kwargs.pop('objs', None)
        super(User, user).update(json.load(response.text))
        return user

    @staticmethod
    def login(username, password):
        user = User()
        url, kwargs = User.build_login_args(user, username, password)
        return User.handle_login_result(user, get(url, **kwargs))

    @staticmethod
    def login_in_background(username, password, **kwargs):
        user = User()
        url, kwargs = User.build_login_args(user, username, password,
            **kwargs)
        return get(url, **kwargs)

    def log_out(self):
        del self['sessionToken']
    
    @staticmethod
    def handle_request_password_reset(response, **kwargs):
        return len(json.load(response.text)) == 0

    @staticmethod
    def build_request_password_reset_args(email, **kwargs):
        callback = kwargs.pop('callback', None)

        url = self.build_password_reset_url()
        headers = build_headers()
        data = json.dump({'email': email})

        if callback is not None:
            callback = build_boolean_callback(
                User.handle_request_password_reset, callback=callback,
                **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback':
            callback})

    @staticmethod
    def request_password_reset(email):
        url, kwargs = User.build_request_password_reset_args(email)
        return User.handle_request_password_reset(post(url, **kwargs))

    @staticmethod
    def request_password_reset_in_background(email, **kwargs):
        url, kwargs = User.build_request_password_reset_args(email,
            **kwargs)
        return post(url, **kwargs)

    @staticmethod
    def query():
        return Query(CLASS_TYPE_USER)

class Query(object):
    def __init__(self, class_name):
        self._class_name = class_name
        self.ignore_acl = False
        self.data = {}
        self._limit = QUERY_DEFAULT_LIMIT
        self._skip = QUERY_DEFAULT_SKIP

    @property
    def class_name(self):
        return self._class_name
    
    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, limit):
        if not isinstance(limit, Number):
            raise TypeError("Limit requires a number")
        self._limit = max(0, min(limit, QUERY_MAX_LIMIT))
        if self._limit != QUERY_DEFAULT_LIMIT:
            self.data['limit'] = self._limit
        elif 'limit' in self.data:
            del self.data['limit']

    @property
    def skip(self):
        return self._skip

    @skip.setter
    def skip(self, skip):
        if not isinstance(skip, Number):
            raise TypeError("Limit requires a number")
        self._skip = max(0, skip)
        if self._skip != QUERY_DEFAULT_SKIP:
            self.data['skip'] = self._skip
        elif 'skip' in self.data:
            del self.data['skip']

    def build_url(self, object_id=None):
        paths = [API_BASE_URL, API_VERSION]
        
        try:
            paths.append(CLASS_PATHS[self.class_name])
        except KeyError:
            paths.append(API_CLASSES_PATH)
            paths.append(self.class_name)
        
        if object_id is not None:
            paths.append(object_id)

        return '/'.join(paths)

    def set_where_op_for_key(self, key, op, value):
        if op not in QUERY_OPS:
            raise ValueError('%s is not a valid operation' % (op))

        if 'where' not in self.data:
            self.data['where'] = {}

        if key not in self.data['where']:
            self.data['where'][key] = {}

        self.data['where'][key][op] = value
        return self
    
    def set_where_op(self, op, value):
        if op not in QUERY_OPS:
            raise ValueError('%s is not a valid operation' % (op))

        if 'where' not in self.data:
            self.data['where'] = {}

        self.data['where'][op] = value
        return self
    
    def eq(self, key, value):
        if 'where' not in self.data:
            self.data['where'] = {}
        
        self.data['where'][key] = value
        return self

    def lt(self, key, value):
        if not isinstance(value, (Number, datetime.datetime)):
            raise TypeError("Constraint requires a number or datetime")
        return self.set_where_op_for_key(key, '$lt', value)

    def lte(self, key, value):
        if not isinstance(value, (Number, datetime.datetime)):
            raise TypeError("Constraint requires a number or datetime")
        return self.set_where_op_for_key(key, '$lte', value)

    def gt(self, key, value):
        if not isinstance(value, (Number, datetime.datetime)):
            raise TypeError("Constraint requires a number or datetime")
        return self.set_where_op_for_key(key, '$gt', value)

    def gte(self, key, value):
        if not isinstance(value, (Number, datetime.datetime)):
            raise TypeError("Constraint requires a number or datetime")
        return self.set_where_op_for_key(key, '$gte', value)

    def ne(self, key, value):
        if not isinstance(value, (Number, datetime.datetime)):
            raise TypeError("Constraint requires a number or datetime")
        return self.set_where_op_for_key(key, '$ne', value)

    def contained_in(self, key, *values):
        return self.set_where_op_for_key(key, '$in', values)

    def not_contained_in(self, key, *values):
        return self.set_where_op_for_key(key, '$nin', values)

    def contains_all(self, key, *values):
        return self.set_where_op_for_key(key, '$all', values)

    def exists(self, key):
        return self.set_where_op_for_key(key, '$exists', True)

    def not_exist(self, key):
        return self.set_where_op_for_key(key, '$exists', False)        

    def select(self, key, value):
        return self

    def regex(self, key, value):
        if not isinstance(value, basestring):
            raise TypeError("Constraint requires a string")
        return self.set_where_op_for_key(key, '$regex', value)

    def order(self, key, ascending):
        if not isinstance(ascending, bool):
            raise TypeError("Constraint requires a boolean")
        self.data['order'] = key if ascending else ''.join(['-', key])
        return self

    def include(self, key):
        if not isinstance(key, basestring):
            raise TypeError("Constraint requires a string")

        try:
            data = self.data['include'].split(',')
        except KeyError:
            data = []

        data.append(key)
        self.data['include'] = ','.join(data)
        return self

    def related_to(self, obj, key):
        value = {
            'object': obj.object_without_data(),
            'key': key
        }
        
        return self.set_where_op('$relatedTo', value)
    
    @staticmethod
    def or_query_with_subqueries(*queries):
        value = [query.data['where'] for query in queries]
        query = Query().set_where_op('$or', value)
        return query
    
    def build_get_args(self, object_id, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        url = self.build_url(object_id)
        headers = build_headers(master_key=ignore_acl)

        if callback is not None:
            callback = build_object_callback(self.handle_get_result, 
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'callback': callback})

    def handle_get_result(self, response, **kwargs):
        return json.load(response.text, class_name=self.class_name)

    def get(self, object_id, **kwargs):
        url, kwargs = self.build_get_args(object_id, **kwargs)
        return self.handle_get_result(get(url, **kwargs))
    
    def get_in_background(self, object_id, **kwargs):
        url, kwargs = self.build_get_args(object_id, **kwargs)
        return get(url, **kwargs)

    def build_query_data(self):
        data = dict(self.data)
        if 'where' in data:
            data['where'] = json.dump(data['where'])
        return urllib.urlencode(data)

    def build_count_args(self, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        url = self.build_url()
        headers = build_headers(master_key=ignore_acl)
        data = build_query_data()

        if callback is not None:
            callback = build_integer_callback(self.handle_count_result,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback':
            callback})

    def handle_count_result(self, response, **kwargs):
        result = json.load(response.text, class_name=self.class_name)
        return result['count']

    def count(self, **kwargs):
        self.data['count'] = 1
        url, kwargs = self.build_count_args(**kwargs)
        return self.handle_count_result(get(url, **kwargs))

    def count_in_background(self, **kwargs):
        self.data['count'] = 1
        url, kwargs = self.build_count_args(**kwargs)
        return get(url, **kwargs)

    def build_find_args(self, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        url = self.build_url()
        headers = build_headers(master_key=ignore_acl)
        data = self.build_query_data()

        if callback is not None:
            callback = build_list_callback(self.handle_find_result,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback':
            callback})

    def handle_find_result(self, response, **kwargs):
        result = json.load(response.text, class_name=self.class_name)
        return result['results']

    def find(self, **kwargs):
        url, kwargs = self.build_find_args(**kwargs)
        return self.handle_find_result(get(url, **kwargs))

    def find_in_background(self, **kwargs):
        url, kwargs = self.build_find_args(**kwargs)
        return get(url, **kwargs)

class Relation(object):
    def __init__(self, class_name):
        self.class_name = class_name
        self.instance = None
        self.key = None
        self.objects = []

    def __repr__(self):
        if self.is_role_relation():
            return json.dump({'__op': 'AddRelation', 'objects': objs})
        else:
            return json.dump({'__type': 'Relation',
                'className': self.class_name})
    
    def is_role_relation(self):
        if not isinstance(self.instance, Role):
            return False

        return self.key in RELATION_ROLE_KEYS

    def request_relation(self, op, *objs):
        if op not in RELATION_OPS:
            raise ValueError('%s is not a valid operation' % (op))

        if self.instance is None or self.key is None:
            msg = "Relation needs to be set inside an object"
            raise ValueError(msg)

        url = self.instance.build_url(object_id=True)
        headers = build_headers()
        data = json.dump({self.key: {'__op': op, 'objects': objs}})
        
        try:
            r = put(url, headers=headers, data=str(self))
        except ParseException:
            pass
    
    def query(self):
        return Query(self.class_name).related_to(self.instance, self.key)
    
    def get(self):
        if self.instance is None or self.key is None:
            raise ValueError("Relation needs to be set inside an object")
        
        return self.query().find()
    
    def append(self, *objs):
        objs = [obj.object_without_data() for obj in objs]
        if self.is_role_relation():
            self.objects += [obj for obj in objs if obj not in self.objects]
        else:
            self.request_relation('AddRelation', *objs)

    def remove(self, *objs):
        objs = [obj.object_without_data() for obj in objs]
        if self.is_role_relation():
            self.objects -= [obj for obj in objs if obj not in self.objects]
        else:
            self.request_relation('RemoveRelation', *objs)

class ACL(object):
    def __init__(self, **kwargs):
        self.data = kwargs

    def __repr__(self):
        json.dump(self.data)

    def set_acl(self, id, op, perm):
        if op not in ACL_OPS:
            raise ValueError("Operation cannot be done on ACLs")

        if perm is True:
            self.data[id][op] = True
        elif op in self.data[id]:
            del self.data[id][op]

    def get_acl(self, id, op):
        if op not in ACL_OPS:
            raise ValueError("Operation cannot be done on ACLs")

        return True if op in self.data[id] else False

    def get_public_read_access(self):
        return self.get_acl('*', 'read')

    def set_public_read_access(self, perm):
        self.set_acl('*', 'read', perm)

    def get_public_write_access(self):
        return self.get_acl('*', 'write')

    def set_public_write_access(self, perm):
        self.set_acl('*', 'write', perm)

    def get_user_read_access(self, user):
        return self.get_acl(user.object_id, 'read')

    def set_user_read_access(self, user, perm):
        self.set_acl(user.object_id, 'read', perm)

    def get_user_write_access(self, user):
        return self.get_acl(user.object_id, 'write')

    def set_user_write_access(self, user, perm):
        self.set_acl(user.object_id, 'write', perm)

class Role(Object):
    def __init__(self, name, acl, users=None, roles=None, **kwargs):
        if re.match('^[\w-_]+$', name) is None:
            raise ValueError('Name must contain alphanumeric, - or _ chars')

        self.name = name
        self.ACL = acl
        super(Role, self).update(**kwargs)
        
        if self.users is None:
            self.users = Relation(CLASS_TYPE_USER)
        
        if self.roles is None:
            self.roles = Relation(CLASS_TYPE_ROLE)
    
    @property
    def name(self):
        return self['name'] if 'name' in self else None
    
    @name.setter
    def name(self, name):
        self['name'] = name
    
    @property
    def users(self):
        return self['users'] if 'users' in self else None
    
    @property
    def roles(self):
        return self['roles'] if 'roles' in self else None
    
    def build_url(self, object_id=False):
        paths = [API_BASE_URL, API_VERSION, API_ROLES_PATH]

        if object_id and self.object_id is not None:
            paths.append(self.object_id)

        return '/'.join(paths)

    @staticmethod
    def query():
        return Query(CLASS_TYPE_ROLE)

class File(object):
    def __init__(self, name, data):
        self._name = name
        self._url = None
        self.data = data

    def __repr__(self):
        return json.dump(self)

    @property
    def name(self):
        return self._name

    @property
    def url(self):
        return self._url

    @property
    def is_dirty(self):
        return True if self.url is None else False

    @property
    def is_data_available(self):
        return True if self.data is not None else False

    def guess_mime_type(self):
        url = urllib.pathname2url(self.name)
        mime_type, encoding = mimetypes.guess_type(url)
        if mime_type is None:
            mime_type = 'text/plain'
        return mime_type

    def build_url(self):
        paths = [API_BASE_URL, API_VERSION, API_FILES_PATH, self.name]
        return '/'.join(paths)

    def build_save_args(self, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        url = self.build_url()
        headers = build_headers(master_key=ignore_acl,
            mime_type=self.guess_mime_type())
        data = self.data

        if callback is not None:
            callback = build_boolean_callback(self.handle_save_result,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback': callback})

    def handle_save_result(self, response, **kwargs):
        result = json.load(response.text)
        self._name = result['name']
        self._url = result['url']
        self.mime_type = self.guess_mime_type()

    def save(self, **kwargs):
        url, kwargs = self.build_save_args(**kwargs)
        return self.handle_save_result(post(url, **kwargs))

    def save_in_background(self, **kwargs):
        url, kwargs = self.build_save_args(**kwargs)
        return post(url, **kwargs)

    def build_get_data_args(self, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        url = self.url
        headers = build_headers(master_key=ignore_acl, mime_type=None)

        if callback is not None:
            callback = build_bytes_callback(self.handle_get_data_result,
                callback=callback, **kwargs)

    def handle_get_data_result(self, response, **kwargs):
        result = json.load(response.text)
        self.mime_type = mime_type
        self._data = data

    def get_data(self, **kwargs):
        if self.is_dirty() or self.is_data_available():
            raise ValueError("Hasn't been saved")

        url, kwargs = self.build_get_data_args(**kwargs)
        return self.handle_get_data_result(get(url, **kwargs))

    def get_data_in_background(self, **kwargs):
        if self.is_dirty() or self.is_data_available():
            raise ValueError("Hasn't been saved")
        
        url, kwargs = self.build_get_data_args(**kwargs)
        return get(url, **kwargs)

    def build_delete_args(self, **kwargs):
        ignore_acl = kwargs.pop('ignore_acl', False)
        callback = kwargs.pop('callback', None)

        url = self.build_url()
        headers = build_headers(master_key=True)

        if callback is not None:
            callback = build_boolean_callback(self.handle_delete_result,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'callback': callback})

    def handle_delete_result(self, response, **kwargs):
        del self.data
        return True

    def delete(self, **kwargs):
        url, kwargs = self.build_delete_args(**kwargs)
        return self.handle_delete_result(delete(url, **kwargs))

    def delete_in_background(self, **kwargs):
        url, kwargs = self.build_delete_args(**kwargs)
        return delete(url, **kwargs)

class Analytics(object):
    @staticmethod
    def build_url(event_name):
        paths = [API_BASE_URL, API_VERSION, API_EVENTS_PATH, event_name]
        return '/'.join(paths)
    
    @staticmethod
    def track_app_opened(at=None):
        url = Analytics.build_url('AppOpened')
        headers = build_headers()
        data = {'at': at} if at is not None else None
        post(url, headers=headers, data=data)

    @staticmethod
    def track_event(event_name, at=None, dimensions=None):
        dimensions = dimensions if dimensions is not None else {}
        url = Analytics.build_url(event_name)
        headers = build_headers()
        data = {}

        if at is not None:
            data['at'] = at

        if dimensions is not None:
            if len(dimensions) > ANALYTICS_DIMENSION_LIMIT:
                msg = "Can only send a maximum of %d dimensions" % \
                    (ANALYTICS_DIMENSION_LIMIT)
                raise ValueError(msg)
            data['dimensions'] = dimensions

        data = data if data else None
        post(url, headers=headers, data=data)

class Push(object):
    def __init__(self, **kwargs):
        channels = kwargs.pop('channels', [])
        channels = [] if channels is None else channels
        message = kwargs.pop('message', None)
        data = kwargs.pop('data', {})
        data = {} if data is None else data
        device_types = kwargs.pop('device_types', DEVICE_TYPES)
        expiration_time = kwargs.pop('expiration_time', None)
        expiration_interval = kwargs.pop('expiration_interval', None)
        query = kwargs.pop('query', None)

        for device_type in device_types:
            if device_type not in globals.DEVICE_TYPES:
                raise ValueError("Invalid device type '%s'" % (device_type))
        
        if expiration_time is not None and expiration_interval is not None:
            msg = "Can only set an expiration time or interval"
            raise ValueError(msg)
        
        self.channels = channels
        if message is not None:
            self.data = {'alert': message}
        self.data = data
        self._device_types = device_types
        self._expiration_time = None
        self._expiration_interval = None
        
        if expiration_time is not None:
            self.expiration_time = expiration_time
        
        if expiration_interval is not None:
            self.expiration_interval = expiration_interval
        
        self._query = None
        self.query = query
    
    @property
    def device_types(self):
        return self._device_types
    
    def add_device_type(self, device_type):
        if device_type not in DEVICE_TYPES:
            raise ValueError("Invalid device type '%s'" % (device_type))
        
        if device_type not in self._device_types:
            self._device_types.append(device_type)
            self._device_types.sort()
    
    def remove_device_type(self, device_type):
        if device_type not in DEVICE_TYPES:
            raise ValueError("Invalid device type '%s'" % (device_type))
        
        try:
            self._device_types.remove(device_type)
            self._device_types.sort()
        except KeyError:
            raise ValueError("Device type not set")
        
    @property
    def expiration_time(self):
        return self._expiration_time
    
    @expiration_time.setter
    def expiration_time(self, time):
        self._expiration_time = time
        self._expiration_interval = None
    
    @property
    def expiration_interval(self):
        return self._expiration_interval
    
    @expiration_interval.setter
    def expiration_interval(self, interval):
        self._expiration_interval = interval
        self._expiration_time = None
    
    @property
    def query(self):
        return self._query
    
    @query.setter
    def query(self, query):
        self._query = query
    
    def build_url(self):
        paths = [API_BASE_URL, API_VERSION, API_PUSH_PATH]
        return '/'.join(paths)
    
    def build_send_data(self):
        data = {
            'channels': self.channels,
            'data': self.data
        }
        
        if self.query is not None:
            data['where'] = self.query.where
    
    def handle_send_result(self, response, **kwargs):
        return True

    def build_send_args(self, **kwargs):
        callback = kwargs.pop('callback', None)

        url = self.build_url()
        headers = build_headers()
        data = self.build_send_data()

        if callback is not None:
            callback = build_boolean_callback(self.handle_send_result,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback': callback})

    def send(self, **kwargs):
        url, kwargs = self.build_send_args(**kwargs)
        return self.handle_send_result(post(url, **kwargs))
    
    def send_in_background(self, **kwargs):
        url, kwargs = self.build_send_args(**kwargs)
        return post(url, **kwargs)

class Installation(Object):
    def __init__(self, device_type, installation_id, device_token=None,
        badge=None, timezone=None, channels=None, **kwargs):
        device_type = args[0]
        installation_id = args[1]
        device_token = kwargs.pop('device_token', None)
        badge = kwargs.pop('badge', None)
        timezone = kwargs.pop('timezone', None)
        channels = kwargs.pop('channels', None)
        
        self['deviceType'] = device_type
        self['installationId'] = installation_id
        self.device_token = device_token
        self.badge = badge
        self['timezone'] = timezone
        self['channels'] = channels
        super(Installation, self).update(**kwargs)
    
    @property
    def device_type(self):
        return self['deviceType'] if 'deviceType' in self else None
    
    @property
    def installation_id(self):
        return self['installationId'] if 'installationId' in self else None
    
    @property
    def device_token(self):
        if self.device_type != DEVICE_TYPE_IOS:
            return None
        
        return self['deviceToken'] if 'deviceToken' in self else None
    
    @device_token.setter
    def device_token(self, device_token):
        if self.device_type != DEVICE_TYPE_IOS:
            msg = "Cannot set the device token for non-iOS devices"
            raise ValueError(msg)
        
        self['deviceToken'] = device_token
    
    @property
    def badge(self):
        if self.device_type != DEVICE_TYPE_IOS:
            return None
        
        return self['badge'] if 'badge' in self else None
    
    @badge.setter
    def badge(self, badge):
        if self.device_type != DEVICE_TYPE_IOS:
            msg = "Cannot set the badge for non-iOS devices"
            raise ValueError(msg)
        
        self['badge'] = badge
    
    @property
    def timezone(self):
        return self['timezone'] if 'timezone' in self else None
    
    @property
    def channels(self):
        return self['channels'] if 'channels' in self else None
    
    def subscribe_channel(self, channel):
        if re.match('^[\w-_]+$', channel) is None:
            msg = 'Channel must contain alphanumeric, - or _ chars'
            raise ValueError(msg)
        
        try:
            self['channels'].append(channel)
            self.dirty('channels')
        except KeyError:
            self['channels'] = [channel]
    
    def unsubscribe_channel(self, channel):
        try:
            self['channels'].remove(channel)
            self.dirty('channels')
        except ValueError:
            msg = "Installation not subscribed to channel '%s'" % (channel)
            raise ValueError(msg)
        except KeyError:
            pass
    
    def build_url(self, object_id=False):
        paths = [API_BASE_URL, API_VERSION, API_INSTALLATIONS_PATH]
        
        if object_id and self.object_id is not None:
            paths.append(self.object_id)
        
        return '/'.join(paths)
    
    def query(self):
        query = Query(self.class_name)
        return query

class Cloud(object):
    @staticmethod
    def build_url(fn):
        paths = [API_BASE_URL, API_VERSION, API_FUNCTIONS_PATH, fn]
        return '/'.join(paths)
    
    @staticmethod
    def build_function_args(fn, params=None, **kwargs):
        callback = kwargs.pop('callback', None)

        url = Cloud.build_url(fn)
        headers = build_headers()
        params = params if params is not None else {}
        data = json.dump(params)

        if callback is not None:
            callback = build_object_callback(Cloud.handle_function_result,
                callback=callback, **kwargs)

        return (url, {'headers': headers, 'data': data, 'callback': callback})

    @staticmethod
    def handle_function_result(response, **kwargs):
        r = json.load(response.text)
        try:
            return r['result']
        except KeyError:
            e = ParseException()
            e.code = r['code']
            e.reason = r['error']
            raise e

    @staticmethod
    def call_function(fn, params=None, **kwargs):
        url, kwargs = Cloud.build_function_args(fn, params, **kwargs)
        Cloud.handle_function_result(post(url, **kwargs))

    @staticmethod
    def call_function_in_background(fn, params=None, **kwargs):
        url, kwargs = Cloud.build_function_args(fn, params, **kwargs)
        return post(url, **kwargs)

class GeoPoint(object):
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    @property
    def latitude(self):
        return self._latitude

    @latitude.setter
    def latitude(self, latitude):
        if not -90.0 < latitude < 90.0:
            raise ValueError("Latitude out of bounds")
        self._latitude = latitude

    @property
    def longitude(self):
        return self._longitude

    @longitude.setter
    def longitude(self, longitude):
        if not -180.0 < longitude < 180.0:
            raise ValueError("Longitude out of bounds")
        self._longitude = longitude