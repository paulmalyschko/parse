import unittest

class ParseAppEngineTestCase(unittest.TestCase):
    def set_up(self):
        pass

    def tear_down(self):
        pass

    def test_appengine_running(self):
        """Test if AppEngine is running"""
        
        error = None
        try:
            import google.appengine
        except ImportError as e:
            error = e

        msg = "Google AppEngine devserver is not running or undetectable"
        self.assert_equal(error, None, msg)

if __name__ == '__main__':
    unittest.main()