#!/usr/bin/env python
# encoding: utf-8
"""
bookkeeping/hudora.py

Created by Maximillian Dornseif on 2010-06-04.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import husoftm.kunden
import husoftm.rechnungen


ABSENDER_ADRESSE = u"HUDORA GmbH\nJägerwald 13\nD-42897 Remscheid"


def list_invoices(kdnr):
    """Erzeuge eine Liste mit allen Rechnungsnummern zu der gegebenen Kundennummer"""
    return husoftm.rechnungen.rechnungen_for_kunde(kdnr)


def get_invoice(rechnungsnr):
    """Erzeuge eine Rechnung im SimpleInvoiceProtocol aus der Rechnung mit der gegebenen Rechnungsnummer"""
    
    rechnungskopf, rechnungspositionen = husoftm.rechnungen.get_rechnung(rechnungsnr)
    kunde = husoftm.kunden.get_kunde(rechnungskopf['kundennr_warenempfaenger'])
    invoice = {
        'kundennr': rechnungskopf['kundennr_warenempfaenger'],
        'name1': kunde.name1,
        'name2': kunde.name2,
        'strasse': kunde.strasse,
        'ort': kunde.ort,
        'plz': kunde.plz,
        'land': kunde.land,
        'tel': kunde.tel,
        'mail': kunde.mail,
        'iln': kunde.iln,
        'kundenauftragsnr': rechnungskopf['kundenauftragsnr'],
        'guid': rechnungskopf['rechnungsnr'],
        'zahlungsziel': 30,
        'absenderadresse': ABSENDER_ADRESSE,
        'preis': int(rechnungskopf['netto'] * 100),
        'orderlines': [],
    }
    
    if rechnungskopf.get('versand_date', None):
        invoice['leistungszeitpunkt'] = rechnungskopf['versand_date'].strftime('%Y-%m-%d')
    
    
    for index, position in enumerate(rechnungspositionen):
        invoice['orderlines'].append({'guid': '%s-%d' % (invoice['guid'], index),
                                      'menge': int(position['menge']),
                                      'artnr': position['artnr'],
                                      'infotext_kunde': position['text'],
                                      'preis': int(position['wert_netto'] * 100),
                                     })
    return invoice
