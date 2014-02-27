import base64
import json
import logging
from numbers import Number

from .packages import requests

from . import constants
from . import parsejson as json
from .exceptions import ParseException


def build_headers(master_key=False, session_token=None,
    mime_type='application/json'):
    headers = {}
    if mime_type is not None:
        headers['Content-Type'] = mime_type
    headers['X-Parse-Application-Id'] = constants.APPLICATION_ID
    headers['X-Parse-REST-API-Key'] = constants.REST_API_KEY
    
    if master_key:
        headers['X-Parse-Master-Key'] = constants.MASTER_KEY
    
    if session_token is not None:
        headers['X-Parse-Session-Token'] = session_token
    
    return headers

def generate_exception(error):
    try:
        r = json.load(error.response.text)
        e = ParseException(r['error'])
        e.reason = r['error']
        e.code = r['code']
    except KeyError:
        # no code == authentication error
        e = ParseException("Unauthorized")
        e.reason = None
        e.code = None
    except AttributeError:
        # RequestException
        print str(error)
        e = ParseException(str(error))
        e.reason = None
        e.code = None
    except (TypeError, ValueError):
        # invalid JSON
        e = requests.HTTPError(str(error))
        e.reason = str(error)
        e.code = error.code
        e.response = error.response
    
    print e
    return e

def request(method, url, **kwargs):
    data = kwargs.get('data')
    headers = kwargs.get('headers')
    timeout = kwargs.get('timeout')
    verify = kwargs.get('verify', True)
    cookies = kwargs.get('cookies')
    callback = kwargs.get('callback')
    
    if callback:
        r = requests.request(method, url, data=data, headers=headers,
            timeout=timeout, verify=verify, cookies=cookies, callback=callback)
    else:
        try:
            r = requests.request(method, url, data=data, headers=headers,
                timeout=timeout, verify=verify, cookies=cookies)
        except (requests.HTTPError, requests.RequestException) as e:
            raise generate_exception(e)
    
    return r

def get(url, **kwargs):
    return request('GET', url, **kwargs)

def post(url, **kwargs):
    return request('POST', url, **kwargs)

def put(url, **kwargs):
    return request('PUT', url, **kwargs)

def delete(url, **kwargs):
    return request('DELETE', url, **kwargs)

def build_callback(result_type, handler, **kwargs):
    objs = kwargs.pop('objs', None)
    callback = kwargs.pop('callback', None)

    def wrapper(response, error):
        result = None
        if response and not error:
            result = handler(response, objs=objs)
            if not isinstance(result, result_type):
                msg = "Result is of incorrect type"
                raise TypeError(msg)
        elif isinstance(error, requests.HTTPError):
            error = get_error(error)

        if callback:
            callback(result, error, **kwargs)
    
    return wrapper

def build_boolean_callback(handler, **kwargs):
    return build_callback(bool, handler, **kwargs)

def build_integer_callback(handler, **kwargs):
    return build_callback(int, handler, **kwargs)

def build_list_callback(handler, **kwargs):
    return build_callback((list, None), handler, **kwargs)

def build_object_callback(handler, **kwargs):
    return build_callback((dict, None), handler, **kwargs)

def build_bytes_callback(handler, **kwargs):
    return build_callback((str, None), handler, **kwargs)