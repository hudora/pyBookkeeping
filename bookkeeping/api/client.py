#!/usr/bin/env python
# encoding: utf-8

"""
REST API Client für Bookkeeping
"""

# Created by Christoph Borgolte on 13-08-2010 for HUDORA.
# Copyright (c) 2010 HUDORA. All rights reserved.


from restkit import Resource, BasicAuth
import datetime
import simplejson as json

def datestr(date):
    """
    Konvertiere Datum zu String im ISO-Format

    >>> import datetime
    >>> datestr(datetime.datetime(2010, 04, 01))
    '2010-04-01'
    >>> datestr(datetime.date(2010, 04, 01))
    '2010-04-01'
    """

    if isinstance(date, datetime.datetime):
        date = date.date().isoformat()
    elif isinstance(date, datetime.date):
        date = date.isoformat()
    return date

def get_client(**kwargs):
    """
    Erzeuge Client-Instanz für Bookkeeping API
    
    Die erforderliche Konfiguration kann durchgeführt werden über:
    * Über Keyword-Parameter username, password und endpoint
    * Umgebungsvariblen (BK_API_USERNAME, BK_API_PASSWORD, BK_API_ENDPOINT)
    * Django settings: settings.BK_API als dict mit den Schlüsseln 'username', 'password', 'endpoint'
    
    Diese Reihenfolge entspricht der Suchreihenfolge.
    """
    
    import os
    try:
        from django.conf import settings
        bk_settings = getattr(settings, 'BK_API', {})
    except ImportError:
        bk_settings = {}
    
    for param in 'username', 'password', 'endpoint':
        if not param in kwargs:
            kwargs[param] = os.environ.get("BOOKKEEPING_API_%s" % param.upper(), bk_settings.get(param, None))
    
    return Bookkeeping(kwargs.get('username'), kwargs.get('password'), kwargs.get('endpoint'))


class Bookkeeping(Resource):
    """API Client für Bookkeeping"""

    def __init__(self, username, password, endpoint=None, pool_instance=None, **kwargs):
        auth = BasicAuth(username, password)

        if 'filters' in kwargs:
            filters.append(auth)
        else:
            filters = [auth]

        super(Bookkeeping, self).__init__(endpoint, follow_redirect=True, max_follow_redirect=10,
                                          pool_instance=pool_instance, filters=filters, **kwargs)

    def request(self, *args, **kwargs):
        response = super(Bookkeeping, self).request(*args, **kwargs)
        return json.loads(response.body_string())

    def invoice(self, company, rechnungsnr, date):
        return self.get('invoice/', company=company, rechnungsnr=rechnungsnr)

    def create_invoice(self, company, invoice):
        """
        Erzeuge eine Rechnung aus dem SimpleInvoiceProtocol.
        """
        return self.post('invoice/%s/' % company, json.dumps(invoice), headers={'Content-Type': 'application/json'})

    def creditline(self, company, kundennr, consumption):
        return self.get('creditline/', company=company, kundennr=kundennr, consumption=consumption)
