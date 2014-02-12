import unittest
from google.appengine.ext.testbed import Testbed, URLFETCH_SERVICE_NAME

class ParseAppEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_urlfetch_stub()
        self.urlfetch_stub = self.testbed.get_stub(URLFETCH_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

if __name__ == '__main__':
    unittest.main()