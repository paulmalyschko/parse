import os
import sys
import time
import unittest
import parse


class ParseTestTimeout(Exception):
    pass

def wait(r, value, timeout=30):
    end_time = time.time() + timeout
    while True:
        time.sleep(1)
        if time.time() >= end_time:
            raise ParseTestTimeout("Wait for value change timed out")
        if r['result'] == value:
            break

class ParseTestCase(unittest.TestCase):
    def setUp(self):
        app_id = os.environ['APPLICATION_ID']
        rest_api_key = os.environ['REST_API_KEY']
        master_key = os.environ['MASTER_KEY']
        parse.set_application('test-parse', app_id, rest_api_key, master_key)

    def tearDown(self):
        while True:
            q = parse.Query('TestObject')
            q.limit = 50
            r = q.find()
            if not r:
                break
            parse.Object.delete_all(r, ignore_acl=True)

    def test_save_object(self):
        obj = parse.Object('TestObject')
        obj.save()
        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

        r = {'result': False}
        def callback(result, error):
            value = result if not error else False
        
        obj = parse.Object('TestObject')
        obj.save_in_background(callback=callback)

        wait(r, True)
        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)


if __name__ == '__main__':
    unittest.main()