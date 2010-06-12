#!/usr/bin/env python
# encoding: utf-8
"""
bookkeeping/abstract.py - Abstract implementation of bookkeeping functionality.

Created by Maximillian Dornseif on 2010-06-04.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

class AbstractBookkeeping(object):
    def store_invoice(self, invoice):
        """Erzeugt eine (Ausgangs-) Rechnung anhand Simple Invoice Protocol.
        Siehe https://github.com/hudora/CentralServices/blob/master/doc/SimpleInvoiceProtocol.markdown"""
        raise NotImplementedError()
        
    def check_invoice(self, invoice):
        # Pflichtfelder prüfen
        pflichtfelder = 'name1 guid'
        for pflichtfeld in pflichtfelder.split():
            if not getattr(invoice, pflichtfeld, False):
                raise RuntimeError('Feld %s fehlt - %r' % (pflichtfeld, invoice))
