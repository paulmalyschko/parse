import os
import sys
import time
import unittest
import parse


class ParseTestTimeout(Exception):
    pass

def wait(r, timeout=30):
    print ">>> wait..."
    end_time = time.time() + timeout
    while True:
        time.sleep(1)
        if time.time() >= end_time:
            raise ParseTestTimeout("Wait for value change timed out")
        if r['result'] is not None:
            break

class ParseTestCase(unittest.TestCase):
    def setUp(self):
        print ">>> set up"
        app_id = os.environ['APPLICATION_ID']
        rest_api_key = os.environ['REST_API_KEY']
        master_key = os.environ['MASTER_KEY']
        parse.set_application('test-parse', app_id, rest_api_key, master_key)

    def tearDown(self):
        print ">>> tear down"
        while True:
            q = parse.Query('TestObject')
            q.limit = 50
            r = q.find()
            if not r:
                break
            parse.Object.delete_all(r, ignore_acl=True)

    def test_save_object(self):
        print ">>> test_save_object"
        obj = parse.Object('TestObject')
        obj.save()
        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)

        r = {'result': None}
        def callback(result, error):
            print ">>> test_save_object callback called"
            r['result'] = result if not error else False
        
        obj = parse.Object('TestObject')
        obj.save_in_background(callback=callback)

        wait(r)
        self.assertIsNotNone(obj.object_id)
        self.assertIsNotNone(obj.created_at)


if __name__ == '__main__':
    unittest.main()