import unittest
app = None

# try to run a webapp2 instance
try:
    from webapp2 import RequestHandler, WSGIApplication

    class Handler(RequestHandler):
        def get(self):
            self.response.out.write('')

    app = WSGIApplication([('/', Handler)], debug=True)
except ImportError:
    pass

class ParseAppEngineTestCase(unittest.TestCase):
    def test_appengine_running(self):
        """Test if AppEngine is running"""
        
        error = None
        try:
            import google.appengine
        except ImportError as e:
            error = e

        msg = "Google AppEngine devserver is not running or undetectable"
        self.assertEqual(error, None, msg)

if __name__ == '__main__':
    unittest.main()