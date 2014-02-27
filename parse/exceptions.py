"""
Exceptions

"""

class ParseException(Exception):
    """Base Exception class"""
    
    def __init__(self, *args):
        super(ParseException, self).__init__(*args)
        self.code = None
        self.reason = None