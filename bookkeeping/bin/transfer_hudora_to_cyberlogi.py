#!/usr/bin/env python
# encoding: utf-8

"""
Transferiere die Rechnungen von HUDORA an Cyberlogi zu xero.com

Created by Christian Klein on 2010-06-10.
Copyright (c) 2010 HUDORA GmbH. All rights reserved.
"""

import bookkeeping
import optparse

def transfer(dryrun=False):    
    eingangsrechnungen = bookkeeping.cyberlogi.list_eingangsrechnungen("HUDORA GmbH")
    
    rechnungen = bookkeeping.hudora.list_invoices('66669')
    for rechnungsnr in rechnungen:
        rechnung = bookkeeping.hudora.get_invoice(rechnungsnr)
        if not rechnung in eingangsrechnungen:
            print "Rechnung noch nicht bei Xero.com:", rechnung['guid'], rechnung.get('leistungszeitpunkt', 'kein Lieferdatum'), rechnung['kundenauftragsnr']
            if not dryrun:
                bookkeeping_url.cyberlogi.store_hudorainvoice(rechnung)


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option('--dryrun', action="store_true", default=False)
    
    options, args = parser.parse_args()
    
    transfer(optins.dryrun)