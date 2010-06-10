# encoding: utf-8

"""

Created 2010-06-04 by MAximillian Dornseif
Copyright (c) 2010 HUDORA. All rights reserved."""


# siehe http://stackoverflow.com/questions/1305532/convert-python-dict-to-object
class Struct(object):
    def __init__(self, **entries): 
        self.__dict__.update(entries)
        self.default = None

    def __getattr__(self, name):
        return self.default


def make_struct(obj):
    """Converts a dict to an object, leaves the object untouched.
    Read Only!
    """
    if not hasattr(obj, '__dict__'):
        return Struct(**obj)
    return obj
