import unittest
from webapp2 import RequestHandler, WSGIApplication
from google.appengine.ext.testbed import Testbed, URLFETCH_SERVICE_NAME

# bogus handler for app.yaml
class Handler(RequestHandler):
    def get(self):
        self.response.out.write('Parse test application')

app = WSGIApplication([('/', Handler)], debug=True)

# unit test suite
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