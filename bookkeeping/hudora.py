#!/usr/bin/env python
# encoding: utf-8
"""
bookkeeping/hudora.py

Created by Maximillian Dornseif on 2010-06-04.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import datetime
import husoftm.kunden
import husoftm.rechnungen


ABSENDER_ADRESSE = u"HUDORA GmbH\nJägerwald 13\nD-42897 Remscheid"


def list_invoices(kdnr, days=None):
    """
    Erzeuge eine Liste mit allen Rechnungsnummern zu der gegebenen Kundennummer.
    
    Ist der Parameter days gesetzt, werden nur die Rechnungen der letzten `days` Tage betrachtet. 
    """
    
    mindate = datetime.date.today() - datetime.timedelta(days=days) if days else None
    return [x for x in husoftm.rechnungen.rechnungen_for_kunde(kdnr, mindate=mindate) if str(x) != '0']


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
        'zahlungsziel': 30,
        'absenderadresse': ABSENDER_ADRESSE,
        'preis': int(rechnungskopf['netto'] * 100),
        'orderlines': [],
    }
    
    guid = str(rechnungskopf['rechnungsnr'])
    if not guid.startswith('RG'):
        guid = 'RG' + guid
    invoice['guid'] = guid
    
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


def kredit_limit(kundennr, consumption=False):
    """Höhe bzw die Ausschöpfung des Kreditlimits für diesen Kunden zurückgeben."""

    op = 0
    if consumption:
        op = offene_posten(kundennr)
    return husoftm.kunden.kredit_limit(kundennr) - op


def offene_posten(kundennr):
    """Offene Posten für diesen Kunden ermitteln.

    Derzeit nur ein Wrapper um husoftm.kunden.offene_posten."""
    return husoftm.kunden.offene_posten(kundennr)

