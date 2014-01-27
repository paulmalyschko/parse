import base64
import datetime
import json

import models
from .constants import DATETIME_FORMAT, CLASS_TYPE_USER


class JSONDecoder(json.JSONDecoder):
    def __init__(self, class_name=None):
        super(JSONDecoder, self).__init__(object_hook=self.object_hook)
        self.class_name = class_name

    def object_hook(self, obj):
        keys = ('objectId', 'createdAt', 'updatedAt')

        if self.class_name is None:
            self.class_name = obj['className']

        if all(key in obj for key in keys):
            if self.class_name != CLASS_TYPE_USER:
                return models.Object(self.class_name, **obj)
            else:
                return models.User(**obj)
        elif '__type' in obj:
            if obj['__type'] == 'Pointer':
                return models.Object(obj['className'], obj['objectId'])
            elif obj['__type'] == 'Date':
                return datetime.datetime.strptime(obj['iso'],
                    DATETIME_FORMAT)
            elif obj['__type'] == 'Bytes':
                return bytearray(base64.base64decode(obj['base64']))
            elif obj['__type'] == 'Relation':
                return models.Relation(obj['className'])
            elif obj['__type'] == 'GeoPoint':
                return models.GeoPoint(obj['latitude'],
                    obj['longitude'])

        return obj


class JSONEncoder(json.JSONEncoder):
    def __init__(self, class_name=None):
        super(JSONEncoder, self).__init__()
        self.class_name = class_name

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return {
                '__type': 'Date',
                'iso': obj.strftime(DATETIME_FORMAT)
            }
        elif isinstance(obj, bytearray):
            return {
                '__type': 'Bytes',
                'base64': base64.base64encode(str(obj))
            }
        elif isinstance(obj, models.Relation):
            return {
                '__type': 'Relation',
                'className': obj.class_name
            }
        elif isinstance(obj, models.File):
            return {
                '__type': 'File',
                'name': obj.name
            }
        elif isinstance(obj, models.GeoPoint):
            return {
                '__type': 'GeoPoint',
                'latitude': obj.latitude,
                'longitude': obj.longitude
            }

        return super(JSONEncoder, self).default(obj)

def load(s, class_name=None):
    return JSONDecoder(class_name).decode(s)

def dump(obj, class_name=None):
    return JSONEncoder(class_name).encode(obj)