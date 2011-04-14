#!/usr/bin/env python
# encoding: utf-8
"""
bookkeeping/cyberlogi.py Konkrete Implementierung der Klasse für cyberlogi
verwended Xero.com als backend

Created by Maximillian Dornseif on 2010-06-04.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import base64
import binascii
import cs.keychain
import datetime
import huTools.unicode
import huTools.hujson
import oauth2 as oauth
import os
import urllib
import warnings
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal
from tlslite.utils import keyfactory
from bookkeeping.struct import make_struct


URL_BASE = 'https://api.xero.com/api.xro/2.0/Invoices'


def get_value(key):
    """Get value from environment or cs.keychain

    Raises RuntimeError if no value can be found.
    """

    value = os.getenv(key)
    if value is None:
        value = getattr(cs.keychain, key, None)
    if value is None:
        raise RuntimeError
    return value


class OAuthSignatureMethod_RSA_SHA1(oauth.SignatureMethod):
    """
    OAuthSignatureMethod_RSA_SHA1, siehe
    http://gdata-python-client.googlecode.com/svn-history/r576/trunk/src/gdata/oauth/rsa.py
    """

    name = "RSA-SHA1"

    def _fetch_public_cert(self, oauth_request):
        raise NotImplementedError

    def _fetch_private_cert(self, oauth_request):
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, consumer, token): # XXX consumer und token ungenutzt?
        sig = (oauth.escape(oauth_request.method),
               oauth.escape(oauth_request.normalized_url),
               oauth.escape(oauth_request.get_normalized_parameters()),
              )
        raw = '&'.join(sig)
        return raw

    def sign(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        base_string = self.build_signature_base_string(oauth_request, consumer, token)
        # Fetch the private key cert based on the request
        cert = self._fetch_private_cert(oauth_request)
        # Pull the private key from the certificate
        privatekey = keyfactory.parsePrivateKey(cert)
        # Sign using the key
        signed = privatekey.hashAndSign(base_string)
        return binascii.b2a_base64(signed)[:-1]

    def check_signature(self, oauth_request, consumer, token, signature):
        decoded_sig = base64.b64decode(signature)
        base_string = self.build_signature_base_string(oauth_request, consumer, token)
        # Fetch the public key cert based on the request
        cert = self._fetch_public_cert(oauth_request)
        # Pull the public key from the certificate
        publickey = keyfactory.parsePEMKey(cert, public=True)
        # Check the signature
        valid = publickey.hashAndVerify(decoded_sig, base_string)
        return valid


class XeroOAuthSignatureMethod_RSA_SHA1(OAuthSignatureMethod_RSA_SHA1):
    def _fetch_public_cert(self, oauth_request):
        return get_value('XERO_RSACERT')

    def _fetch_private_cert(self, oauth_request):
        return get_value('XERO_RSAKEY')


def xero_request(url, method='GET', body='', get_parameters=None, headers=None):
    """Request an xero durchführen"""

    consumer = oauth.Consumer(key=get_value('XERO_CONSUMER_KEY'), secret=get_value('XERO_CONSUMER_SECRET'))
    client = oauth.Client(consumer, token=oauth.Token(key=get_value('XERO_CONSUMER_KEY'),
                                                      secret=get_value('XERO_CONSUMER_SECRET')))
    client.set_signature_method(XeroOAuthSignatureMethod_RSA_SHA1())

    if headers is None:
        headers = {}

    if get_parameters:
        url = "%s?%s" % (url, urllib.urlencode(get_parameters))

    response, content = client.request(url, method, body=body, headers=headers)
    if response['status'] == '404':
        return None
    if response['status'] != '200':
        if content == 'oauth_problem=signature_invalid&oauth_problem_advice=Failed%20to%20validate%20signature':
            # handle occasion server site glitches
            return xero_request(url, method, body, headers=headers)
        if body:
            print body
        raise RuntimeError("Return code %s for %s: %s" % (response['status'], url, content))
    return content


def add_orderline(root, description, qty, price, account_code):
    """Füge Orderline zu XML-Baum hinzu"""
    lineitem = ET.SubElement(root, 'LineItem')
    ET.SubElement(lineitem, 'Description').text = description
    ET.SubElement(lineitem, 'Quantity').text = str(qty)
    ET.SubElement(lineitem, 'UnitAmount').text = str(price)
    ET.SubElement(lineitem, 'AccountCode').text = account_code


def _convert_to_date(data):
    """Assumes a RfC 3339 coded date or a date object, returns a date object."""
    if not hasattr(data, 'strftime'):
        data = data[:10]  # strip timestamp
        return datetime.datetime.strptime(data, '%Y-%m-%d')
    return data

def store_invoice(invoice, tax_included=False, draft=False, xero_should_generate_invoice_number=False):
    """ Erzeugt eine (Ausgangs-) Rechnung anhand des Simple Invoice Protocol.
    Die Methode ist veraltet, da aufgrund des beschraenkten Rate Limitings
    Rechnungen moeglichst im Block mit store_invoices() uebertragen
    werden sollen, nicht mehr einzeln mit dieser Funktion. """
    warnings.warn("store_invoice() is deprecated: use store_invoices() instead",
                  DeprecationWarning)
    return store_invoices([invoice], tax_included, draft, xero_should_generate_invoice_number)


def store_invoices(invoices, tax_included=False, draft=False, xero_should_generate_invoice_number=False):
    """
    Erzeugt eine Liste von (Ausgangs-) Rechnungen anhand des Simple Invoice Protocol. Als Ergebnis 
    wird ein Hash von Rechnungsnummern zu Xero-IDs zurueckgeliefert.

    Siehe https://github.com/hudora/CentralServices/blob/master/doc/SimpleInvoiceProtocol.markdown
    """

    if draft:
        warnings.warn("draft=True is deprecated: SUBMITTED means 'submitted for approval' which is way to go for all auto-generated stuff",
                      DeprecationWarning)
    if len(invoices) == 0:
        return {}

    root = ET.Element('Invoices')
    for raw_invoice in invoices:
        invoice = make_struct(raw_invoice)
        invoice_element = ET.SubElement(root, 'Invoice')
        ET.SubElement(invoice_element, 'Type').text = 'ACCREC'
        ET.SubElement(invoice_element, 'Status').text = 'DRAFT' if draft else 'SUBMITTED'
        ET.SubElement(invoice_element, 'LineAmountTypes').text = 'Inclusive' if tax_included else 'Exclusive'
        if invoice.kundenauftragsnr:
            ET.SubElement(invoice_element, 'Reference').text = invoice.kundenauftragsnr
        else:
            ET.SubElement(invoice_element, 'Reference').text = invoice.guid
        if not xero_should_generate_invoice_number:
            ET.SubElement(invoice_element, 'InvoiceNumber').text = invoice.guid

        leistungsdatum = _convert_to_date(invoice.leistungszeitpunkt)
        if invoice.zahlungsziel:
            leistungszeitpunkt = _convert_to_date(invoice.leistungszeitpunkt)
            timedelta = datetime.timedelta(days=invoice.zahlungsziel)
            ET.SubElement(invoice_element, 'DueDate').text = (leistungsdatum + timedelta).strftime('%Y-%m-%d')
        ET.SubElement(invoice_element, 'Date').text = leistungsdatum.strftime('%Y-%m-%d')

        lineitems = ET.SubElement(invoice_element, 'LineItems')
        if invoice.infotext_kunde:
            add_orderline(lineitems, invoice.infotext_kunde, 0, 0, '')
        for item in invoice.orderlines:
            item = make_struct(item) # XXX rekursives Verhalten mit in make_struct packen
        
            buchungskonto = '8404'  # default
            # wenn wir hier Ersatzteile von Neuware trenen könnten, könnten wir die Neuware auf Konto 8406
            # udn hoogoo Scooter auf Konto 8410 buchen.
            if item.buchungskonto:
                buchungskonto = item.buchungskonto
            text = unicode(item.artnr)
            if item.infotext_kunde:
                text = u"%s - %s" % (item.artnr, item.infotext_kunde)
            add_orderline(lineitems, text, item.menge, cent_to_euro(item.preis), buchungskonto)

        if invoice.versandkosten:
            add_orderline(lineitems, 'Verpackung & Versand', 1, cent_to_euro(invoice.versandkosten), '8402')

        # Adressdaten
        contact = ET.SubElement(invoice_element, 'Contact')
        ET.SubElement(contact, 'Name').text = ' '.join([invoice.name1, invoice.name2])
        ET.SubElement(contact, 'EmailAddress').text = huTools.unicode.deUmlaut(invoice.mail)
        addresses = ET.SubElement(contact, 'Addresses')
        address = ET.SubElement(addresses, 'Address')
        ET.SubElement(address, 'AddressType').text = 'POBOX' # Rechnungsadresse
        #ET.SubElement(address, 'AttentionTo').text = invoice.name1

        if invoice.name2:
            ET.SubElement(address, 'AddressLine1').text = invoice.name2
            ET.SubElement(address, 'AddressLine2').text = invoice.strasse
        else:
            ET.SubElement(address, 'AddressLine1').text = invoice.strasse

        ET.SubElement(address, 'City').text = invoice.ort
        ET.SubElement(address, 'PostalCode').text = invoice.plz
        ET.SubElement(address, 'Country').text = invoice.land

    invoice_ids = {}
    body = ET.tostring(root, encoding='utf-8')
    content = xero_request(URL_BASE, "PUT", body=body, headers={'content-type': 'text/xml; charset=utf-8'})
    tree = ET.fromstring(content)
    for invoice in tree.findall('Invoices/Invoice'):
        invoice_ids[invoice.find('InvoiceNumber').text] = invoice.find('InvoiceID').text
    return invoice_ids


def cent_to_euro(cent_ammount):
    """
    Berechne den Eurobetrag aus dem Centbetrag

    >>> cent_to_euro('2317')
    Decimal('23.17')
    """

    euro_ammount = Decimal(cent_ammount) / 100
    return euro_ammount.quantize(Decimal('.01'))


# Fast komplette Kopie von store_invoice
# Nur die AccountCodes sind unterschiedlich
# TODO: rename to Store inbound_invoice (oder so)
# TODO: store_hudorainvoice) sollte ein Frontend zu  store_invoice() werden.
def store_hudorainvoice(invoice, netto=True):
    """ Uebertragt eine Rechnung von HUDORA nach Xero.com fuer Cyberlogi.
    Die Methode ist veraltet, da aufgrund des beschraenkten Rate Limitings
    Rechnungen moeglichst im Block mit store_hudorainvoices() uebertragen
    werden sollen, nicht mehr einzeln mit dieser Funktion. """
    warnings.warn("store_hudorainvoice() is deprecated: use store_hudorainvoices() instead",
                  DeprecationWarning)
    return store_hudorainvoices([invoice], netto)

def store_hudorainvoices(invoices, netto=True):
    """ Uebertragt eine Liste von Rechnungen von HUDORA nach Xero.com
    fuer Cyberlogi.
    Der Rückgabewert ist die von Xero gelieferte XML-Nachricht zur weiteren
    Auswertung durch den Aufrufer (bspw. nach Fehlermeldungen oder Invoice-IDs).
    """

    SKONTO_ACCOUNT = '3736'
    VERSANDKOSTEN_ACCOUNT = '3801'
    WAREN_ACCOUNT = '3400'

    root = ET.Element('Invoices')
    for raw_invoice in invoices:
        invoice = make_struct(raw_invoice)
        invoice_element = ET.SubElement(root, 'Invoice')
        # Reference-Tag kann nur bei Type == 'ACCREC' gesetzt werden
        # Bei 'ACCPAY' bleibt wohl nur der Weg, die InvoiceNumber zu setzen
        # ET.SubElement(invoice, 'Reference').text = invoice.guid

        ET.SubElement(invoice_element, 'InvoiceNumber').text = "%s %s" % (invoice.guid, invoice.kundenauftragsnr)
        ET.SubElement(invoice_element, 'Type').text = 'ACCPAY'
        ET.SubElement(invoice_element, 'Status').text = 'SUBMITTED'
        if netto:
            ET.SubElement(invoice_element, 'LineAmountTypes').text = 'Exclusive'
        else:
            ET.SubElement(invoice_element, 'LineAmountTypes').text = 'Inclusive'

        if invoice.leistungszeitpunkt:  # das Feld heisst in SoftM "leistungszeitpunkt"
            leistungsdatum = _convert_to_date(invoice.leistungszeitpunkt)
        elif invoice.rechnungsdatum:    # das Feld heisst in EDIhub "rechnungsdatum"
            leistungsdatum = _convert_to_date(invoice.rechnungsdatum)
        else:
            raise Exception('es konnte kein Leistungs-/ Rechnungsdatum gefunden werden!')

        # das Feld heisst in SoftM "zahlungsziel", in EDIhub aber "zahlungstage"
        zahlungstage = invoice.zahlungsziel or invoice.zahlungstage
        if zahlungstage:
            timedelta = datetime.timedelta(days=zahlungstage)
            ET.SubElement(invoice_element, 'DueDate').text = (leistungsdatum + timedelta).strftime('%Y-%m-%d')
        ET.SubElement(invoice_element, 'Date').text = leistungsdatum.strftime('%Y-%m-%d')

        lineitems = ET.SubElement(invoice_element, 'LineItems')
        if invoice.infotext_kunde:
            add_orderline(lineitems, invoice.infotext_kunde, 0, 0, '')
        if invoice.kundenauftragsnr:
            add_orderline(lineitems, "Kundenauftragsnr: %s" % invoice.kundenauftragsnr, 0, 0, '')

        total = Decimal(0)
        for item in invoice.orderlines:
            item = make_struct(item)
            preis = 0
            if item.menge:
                if item.preis:          # das Feld heisst "preis" in den Daten aus SoftM
                    preis = cent_to_euro(item.preis / item.menge)
                elif item.warenwert:    # das Feld heisst "warenwert" in den Daten aus EDIhub
                    preis = cent_to_euro(item.warenwert / item.menge)

            # Versandkosten mit spezieller AccountID verbuchen
            infotext_kunde = item.infotext_kunde or ''
            if 'versandkosten' in infotext_kunde.lower():
                add_orderline(lineitems, 'Paketversand DPD', item.menge, preis, VERSANDKOSTEN_ACCOUNT)
            else:
                add_orderline(lineitems, u"%s - %s" % (item.artnr, infotext_kunde), item.menge, preis, WAREN_ACCOUNT)

            total += preis * item.menge

        # 2 Prozent Skonto innerhalb von 8 Tagen
        add_orderline(lineitems, 'Skonto bis %s' % (datetime.date.today() + datetime.timedelta(days=8)).strftime('%Y-%m-%d'),
                                 '0.02', -total, SKONTO_ACCOUNT)

        contact = ET.SubElement(invoice_element, 'Contact')
        ET.SubElement(contact, 'Name').text = 'HUDORA GmbH'
        ET.SubElement(contact, 'EmailAddress').text = 'a.jaentsch@hudora.de'
        addresses = ET.SubElement(contact, 'Addresses')
        address = ET.SubElement(addresses, 'Address')
        ET.SubElement(address, 'AddressType').text = 'STREET'
        ET.SubElement(address, 'AttentionTo').text = 'Buchhaltung'
        ET.SubElement(address, 'City').text = 'Remscheid'
        ET.SubElement(address, 'PostalCode').text = '42897'
        ET.SubElement(address, 'Country').text = 'DE'

    body = ET.tostring(root, encoding='utf-8')
    content = xero_request(URL_BASE, "PUT", body=body, headers={'content-type': 'text/xml; charset=utf-8'})
    return ET.fromstring(content)

def check_for_hudora_invoices_in_xero(hudora_rechnungsnummern, tage):
    """Ueberprueft fuer eine Liste von HUDORA-Rechnungsnummern der Form
       "RGxxxxxxxx", ob die entsprechende Rechnung nach Xero uebertragen
       wurde. Um die Abfrage zu beschleunigen werden nur die letzten 'tage'
       Tage bei Xero ueberprueft. Als Ergebnis wird ein Set aller der
       Rechnungsnummern zurueckgeliefert, fuer die noch keine passende
       Xero-Rechnung ermittelt werden konnten."""

    # zuerst den Query-Filter fuer Xero aus den Rechnungsnummern zusammenbauen
    numbers = ' || '.join(map(lambda no: 'InvoiceNumber.StartsWith("%s")' % no,
                              hudora_rechnungsnummern))
    filter = 'Status!="DELETED" && (%s)' % numbers

    # jetzt das fruehestmoegliche Datum ermitteln
    min_date = date.today() - timedelta(days=tage)
    if_modified_since = min_date.strftime('%a, %e %b %Y 00:00:00 GMT')

    # und dann mal bei Xero anklopfen
    json = xero_request('https://api.xero.com/api.xro/2.0/Invoices/',
                        get_parameters={'where': filter},
                        headers={'Accept': 'application/json',
                                 'If-Modified-Since': if_modified_since})
    data = huTools.hujson.loads(json)
    if data['Status'] != 'OK':
        raise Exception('Error while querying Xero for invoices!')

    # schliesslich alle die Nummern rausfiltern, die wir bei Xero gefunden haben. Dazu
    # splitten wir zuerst den RGxxxx-Teil aus der Xero-Rechnungsnummer heraus. Diese
    # hat in den Xero-Daten die Form "RGxxxxx webxxxxx ManuellerPostfixNachBezahlung",
    # und wir brauchen nur den ersten Teil zum Vergleich mit urspruenglichen List von
    # HUDORA-Rechnungsnummern, die wir als Parameter bekommen haben.
    found_invoices_nested = map(lambda inv: inv['InvoiceNumber'].split(), data['Invoices'])
    found_invoices = set([item for sublist in found_invoices_nested for item in sublist])
    return set(hudora_rechnungsnummern).difference(found_invoices)  

def get_invoice(lieferscheinnr=None, invoice_id=None):
    """
    Liefert eine Rechnung aus Xero zurück.

    Wenn keine Rechnung zu der Lieferscheinnummer existiert, wird None zurückgegeben.
    """

    if lieferscheinnr:
        warnings.warn("get_invoice(lieferscheinnr=foo) is deprecated: use get_invoice(invoice_id=foo) instead",
                      DeprecationWarning)

    url = URL_BASE
    # the where-Parameter seems only to work when querying lists of objects not vertain IDs
    parameters = ['Status!="DELETED"'] # , 'Status!="VOIDED"']

    if lieferscheinnr is None and invoice_id is None:
        raise ValueError("lieferscheinnr or invoice_id required")

    if lieferscheinnr:
        parameters.append('Reference=="%s"' % lieferscheinnr)
    if invoice_id:
        url += '/%s' % urllib.quote(invoice_id)

    get_parameters = {'where': "&&".join(parameters)}
    content = xero_request(url, get_parameters=get_parameters)
    invoices = []

    if content:
        tree = ET.fromstring(content)
        for element in tree.getiterator('Invoice'):
            invoice = {}
            for attr in '''Reference Date DueDate Status LineAmountTypes SubTotal TotalTax Total UpdatedDateUTC
                           CurrencyCode InvoiceID InvoiceNumber AmountDue AmountPaid'''.split():
                subelement = element.find(attr)
                if not subelement is None:
                    invoice[attr] = subelement.text
            if invoice.get('Status') not in ['DELETED']:
                invoices.append(invoice)
    return invoices


def list_eingangsrechnungen(firma):
    """
    Ermittle die Eingangsrechnungen von Firma mit namen firma
    und gib eine Liste der Reference-Elemente zurück.
    """

    parameters = ['Type="ACCPAY"', 'Contact.Name="%s"' % firma]
    return list_invoices(parameters, xpath='Invoices/Invoice/InvoiceNumber')


def list_invoices(parameters=None, xpath='Invoices/Invoice/InvoiceID'):
    """Return list of invoice id"""
    tmp = ['Status!="DELETED"', 'Status!="VOIDED"']
    if parameters:
        tmp.extend(parameters)
    get_parameters = {'where': "&&".join(tmp)}
    content = xero_request(URL_BASE, get_parameters=get_parameters)
    tree = ET.fromstring(content)
    return [element.text for element in tree.findall(xpath)]
