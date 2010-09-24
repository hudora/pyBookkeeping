#!/usr/bin/env python
# encoding: utf-8
""" urls.py --- Describe Tool here äöü---
"""

# urls.py
# Created by Christoph Borgolte on 12-08-2010 for HUDORA.
# Copyright (c) 2010 HUDORA. All rights reserved.


from django.conf.urls.defaults import *
from piston.resource import Resource
from piston.authentication import OAuthAuthentication
from piston.authentication import HttpBasicAuthentication

from api_server.api.handlers import InvoiceHandler, KreditLimitHandler, OPHandler


# see http://andrew.io/weblog/2010/01/django-piston-and-handling-csrf-tokens/
class CsrfExemptResource(Resource):
    """A Custom Resource that is csrf exempt"""
    def __init__(self, handler, authentication=None):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)


#auth = OAuthAuthentication(realm="ic_api")
auth = HttpBasicAuthentication()

invoicehandler = CsrfExemptResource(InvoiceHandler, authentication=auth)
creditlinehandler = CsrfExemptResource(KreditLimitHandler, authentication=auth)
ophandler = CsrfExemptResource(OPHandler, authentication=auth)

urlpatterns = patterns('',
    url(r'^invoice/$', invoicehandler),
    url(r'^invoice/(?P<company>\w+)/$', invoicehandler),
    url(r'^creditline/$', creditlinehandler),
    url(r'^creditline/(?P<company>\w+)/$', creditlinehandler),
    url(r'^op/$', ophandler),
    url(r'^op/(?P<company>\w+)/$', ophandler),
)
