import os
import sys
import time
import unittest
import parse


class ParseTestTimeout(Exception):
    pass

def delete_all_objects(class_name):
    while True:
        q = parse.Query(class_name)
        q.limit = 50
        r = q.find()
        if not r:
            break
        parse.Object.delete_all(r, ignore_acl=True)

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
        delete_all_objects('TestObject')

    def test_save(self):
        obj = parse.Object('TestObject')
        obj.save()

        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

    def test_save_in_background(self):
        r = {'result': None}
        def callback(result, error):
            r['result'] = result if not error else False
        
        obj = parse.Object('TestObject')
        obj.save_in_background(callback=callback).wait()
        wait(r)
        
        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

    def test_refresh(self):
        obj = parse.Object('TestObject')
        obj.save()
        object_id = obj.object_id

        obj = parse.Object('TestObject', object_id)
        obj.refresh()

        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

    def test_refresh_in_background(self):
        obj = parse.Object('TestObject')
        obj.save()
        object_id = obj.object_id

        r = {'result': None}
        def callback(result, error):
            r['result'] = result if not error else error

        obj = parse.Object('TestObject', object_id)
        obj.refresh_in_background(callback=callback).wait()
        wait(r)

        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)


if __name__ == '__main__':
    unittest.main()