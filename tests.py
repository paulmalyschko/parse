import os
import sys
import time
import unittest
import parse


TEST_CLASS_NAME = 'TestObject'

class ParseTestTimeout(Exception):
    pass

def delete_all_objects(class_name=TEST_CLASS_NAME):
    while True:
        q = parse.Query(class_name)
        q.limit = 50
        r = q.find()
        if not r:
            break
        parse.Object.delete_all(r, ignore_acl=True)

def save_object(class_name=TEST_CLASS_NAME, key=None, value=None):
    obj = parse.Object(class_name)
    if key is not None and value is not None:
        obj[key] = value
    obj.save()
    return obj

def wait(r, timeout=30):
    end_time = time.time() + timeout
    while True:
        time.sleep(1)
        if time.time() >= end_time:
            raise ParseTestTimeout("Wait for value change timed out")
        if r['result'] is not None:
            break

class ParseObjectTestCase(unittest.TestCase):
    def setUp(self):
        app_id = os.environ['APPLICATION_ID']
        rest_api_key = os.environ['REST_API_KEY']
        master_key = os.environ['MASTER_KEY']
        parse.set_application('test-parse', app_id, rest_api_key, master_key)

    def tearDown(self):
        delete_all_objects(TEST_CLASS_NAME)

    def test_save(self):
        obj = save_object()
        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

    def test_save_in_background(self):
        r = {'result': None}
        def callback(result, error):
            r['result'] = result if not error else False
        
        obj = parse.Object(TEST_CLASS_NAME)
        obj.save_in_background(callback=callback).wait()
        wait(r)

        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

    def test_refresh(self):
        object_id = save_object().object_id
        obj = parse.Object(TEST_CLASS_NAME, object_id)
        obj.refresh()

        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

    def test_refresh_in_background(self):
        object_id = save_object().object_id

        r = {'result': None}
        def callback(result, error):
            r['result'] = result if not error else error

        obj = parse.Object(TEST_CLASS_NAME, object_id)
        obj.refresh_in_background(callback=callback).wait()
        wait(r)

        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

    def test_delete(self):
        obj = save_object()
        object_id = obj.object_id
        obj.delete()

        obj = parse.Object(TEST_CLASS_NAME, object_id)
        with self.assertRaises(parse.ParseException):
            obj.refresh()

    def test_delete_in_background(self):
        obj = save_object()
        object_id = obj.object_id

        r = {'result': None}
        def callback(result, error):
            r['result'] = result if not error else False

        obj.delete_in_background(callback=callback).wait()
        wait(r)

        obj = parse.Object(TEST_CLASS_NAME, object_id)
        with self.assertRaises(parse.ParseException):
            obj.refresh()

    def test_increment(self):
        obj = save_object(key='counter', value=0)
        object_id = obj.object_id

        increments = [1, 3, -5]
        values = [1, 4, -1]

        for i, v in zip(increments, values):
            obj.increment('counter', amount=i)
            self.assertEqual(obj['counter'], v)

            obj = parse.Object(TEST_CLASS_NAME, object_id)
            obj.refresh()
            self.assertEqual(obj['counter'], v)

    def test_add_objects_to_array(self):
        obj = save_object(key='array', value=[1, 'foo'])
        object_id = obj.object_id

        array = [1, 'foo', 2, 'foo', 'bar']
        obj.add_objects_to_array('array', [2, 'foo', 'bar'])
        self.assertItemsEqual(obj['array'], array)

        obj = parse.Object(TEST_CLASS_NAME, object_id)
        obj.refresh()
        self.assertItemsEqual(obj['array'], array)

    def test_add_unique_objects_to_array(self):
        obj = save_object(key='array', value=[1, 'foo'])
        object_id = obj.object_id

        array = [1, 'foo', 2, 'bar']
        obj.add_unique_objects_to_array('array', [2, 'foo', 'bar'])
        self.assertItemsEqual(obj['array'], array)

        obj = parse.Object(TEST_CLASS_NAME, object_id)
        obj.refresh()
        self.assertItemsEqual(obj['array'], array)

    def remove_objects_from_array(self):
        obj = save_object(key='array', value=[1, 'foo', 2, 'bar', 2, 'foo'])
        object_id = obj.object_id

        array = [1, 'bar']
        obj.remove_objects_from_array('array', ['foo', 2])
        self.assertItemsEqual(obj)

        obj = parse.Object(TEST_CLASS_NAME, object_id)
        obj.refresh()
        self.assertItemsEqual(obj['array'], array)


if __name__ == '__main__':
    unittest.main()