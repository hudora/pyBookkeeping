#!/usr/bin/env python
# encoding: utf-8
"""
bookkeeping/hudora.py

Created by Maximillian Dornseif on 2010-06-04.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import datetime
import husoftm.artikel
import husoftm.auftraege
import husoftm.kunden
import husoftm.rechnungen
import husoftm.sachbearbeiter
import husoftm.stapelschnittstelle
import uuid
from decimal import Decimal

ABSENDER_ADRESSE = u"HUDORA GmbH\nJägerwald 13\nD-42897 Remscheid"


# XXX
def check_order(order):
    return True

def store_invoice(invoice):
    raise NotImplementedError

def store_order(order):
    """
    Schreibe einen Auftrag in die SoftM-Stapelschnittstelle.
    
    Es wird erwartet, dass der Auftrag dem ExtendedOrderProtocol entspricht.
    """
    
    if not check_order(order):
        raise ValueError('Order does not conform to ExtendedOrderProtocol')
    
    vorgangsnr = husoftm.stapelschnittstelle.auftrag2softm(order)
    if not husoftm.stapelschnittstelle.address_transmitted(vorgangsnr):
        raise RuntimeError("Fehler bei Vorgang %s: Die Addresse wurde nicht korrekt uebermittelt." % vorgangsnr)


def list_invoices(kdnr):
    """Erzeuge eine Liste mit allen Rechnungsnummern zu der gegebenen Kundennummer"""
    return husoftm.rechnungen.rechnungen_for_kunde(kdnr)


def read_invoice(kdnr, rechnungsnr):
    """Erzeuge eine Rechnung im SimpleInvoiceProtocol aus der Rechnung mit der gegebenen Rechnungsnummer"""
    
    kunde = husoftm.kunden.get_kunde(kdnr)
    rechnungskopf, rechnungspositionen = husoftm.rechnungen.get_rechnung(rechnungsnr)
    auftragskopf, auftragspositionen = husoftm.auftraege.get_auftrag(rechnungskopf['auftragsnummer'])
    
    invoice = {
        'kundennr': kdnr,
        'name1': kunde.name1,
        'name2': kunde.name2,
        'strasse': kunde.strasse,
        'ort': kunde.ort,
        'plz': kunde.plz,
        'land': kunde.land,
        'tel': kunde.tel,
        'mail': kunde.mail,
        'iln': kunde.iln,
        
        'guid': str(uuid4()),
        'leistungszeitpunkt': datetime.date.today().strftime('%Y-%m-%dT%H:%M:%S'),
        'kundenauftragsnr': auftragskopf['auftragsnr_kunde'],
        'infotext_kunde': "", # XXX
        'versandkosten': int(400 / 1.19), # XXX,
        'absenderadresse': ABSENDER_ADRESSE,
        'erfasst_von': husoftm.sachbearbeiter.name(auftragskopf['sachbearbeiter']),
        'preis': int(rechnungskopf['netto'] * 100),
        'orderlines': [],
    }
    
    for index, position in enumerate(rechnungspositionen):
        artikel = husoftm.artikel.get_artikel(artnr=position['artnr'])
        invoice['orderlines'].append({'guid': '%s-%d' % (invoice['guid'], index),
                                      'menge': position['menge'],
                                      'artnr': position['artnr'],
                                      'ean': artikel.ean,
                                      'infotext_kunde': '',
                                      'preis': int(position['wert_netto'] / Decimal("1.19")),
                                     })
    return invoice


def main():
    pass


if __name__ == '__main__':
    main()

