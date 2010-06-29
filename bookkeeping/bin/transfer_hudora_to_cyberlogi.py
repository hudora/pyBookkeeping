#!/usr/bin/env python
# encoding: utf-8

"""
Transferiere die Rechnungen von HUDORA an Cyberlogi zu xero.com

Created by Christian Klein on 2010-06-10.
Copyright (c) 2010 HUDORA GmbH. All rights reserved.
"""

import bookkeeping
import logging
import optparse


def transfer(options):
    """
    Übertrage die Rechnungen zwischen den Buchhaltungssystemen.
    
    Es werden die Ausgangsrechnungen der letzten `options.days` Tage im Buchhaltungssystem
    des Rechnungsstellers betrachtet und diese ggf. in das Buchhaltungssystem des
    Rechnungsempfängers als Eingangsrechnung übertragen.
    """
    
    logger = logging.getLogger('root')
    
    logger.debug('Retrieving invoices by %s' % options.seller)
    eingang = bookkeeping.cyberlogi.list_eingangsrechnungen(options.seller)
    
    logger.debug('Retrieving invoices for %s' % options.buyer)
    ausgang = bookkeeping.hudora.list_invoices(options.buyer, days=options.days)
    
    for rechnungsnr in sorted(ausgang, reverse=True):
        logging.debug('Invoice %s' % rechnungsnr)
                
        if not (rechnungsnr in eingang or 'RG%s' % rechnungsnr in eingang):
            logging.info('Invoice %s not in xero' % rechnungsnr)
            rechnung = bookkeeping.hudora.get_invoice(rechnungsnr)
                        
            if not options.dryrun:
                bookkeeping.cyberlogi.store_hudorainvoice(rechnung)
        else:
            logging.debug('Invoice %s already in xero' % rechnungsnr)


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('--dryrun', action='store_true', default=False, help=u'Nur einen Testlauf durchführen [default: %default]')
    parser.add_option('--buyer', default='66669', help=u'Kundennummer des Rechnungsemfängers in SoftM [default: %default]')
    parser.add_option('--seller', default='HUDORA GmbH', help=u'Name des Rechnungsstellers in Xero [default: %default]')
    parser.add_option('--days', default=7, help=u'Übertrage die Rechnungen der letzten x Tage [default: %default]')
    parser.add_option('-q', '--quiet', default=False, action='store_true', help=u'Möglichst wenig Ausgabe [default: %default]')
    parser.add_option('-v', '--verbose', default=False, action='store_true', help=u'Sehr viel Ausgabe [default: %default]')
    options, args = parser.parse_args()
    
    logger = logging.getLogger('root')
    if options.verbose:
        logger.setLevel(logging.DEBUG)
    elif options.quiet:
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)
    
    transfer(options)