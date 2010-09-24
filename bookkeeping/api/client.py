#!/usr/bin/env python
# encoding: utf-8

"""
REST API Client für Bookkeeping
"""

# Created by Christoph Borgolte on 13-08-2010 for HUDORA.
# Copyright (c) 2010 HUDORA. All rights reserved.


from django.conf import settings
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


class Bookkeeping(Resource):
    """API Client für InventoryControl"""

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

if __name__ == '__main__':
    invoice = {
        "infotext_kunde": "xxy",
        "leistungszeitpunkt": "2010-08-01",
        "land": "DE",
        "tel": "+49 2191 60912-5217",
        "kundenauftragsnr": "kdauftr123123",
        "ort": "Remscheid",
        "orderlines": [
            {
                "infotext_kunde": "",
                "preis": 236,
                "guid": "WL20000023-0000",
                "menge": 1,
                "artnr": "WS15201"
            },
            {
                "infotext_kunde": "",
                "preis": 71,
                "guid": "WL20000023-0001",
                "menge": 2,
                "artnr": "WS11748"
            }
        ],
        "versandkosten": 480,
        "plz": "42897",
        "erfasst_von": "Webshop",
        "name2": "TESTKAUF!",
        "preis": 858,
        "name1": "Christoph Borgolte",
        "mail": "chris@5711.org",
        "strasse": "Jägerwald 13",
        "guid": "WL20000023"
    }

    #bk = Bookkeeping('admin', 'admin', 'http://api.hudora.biz:8080/bookkeeping/')
    bk = Bookkeeping('admin', 'admin', 'http://localhost:8000/bookkeeping/')
    print bk.create_invoice('hudora', invoice)
    #print bk.invoice('hudora', '51591919', datetime.date.today())
