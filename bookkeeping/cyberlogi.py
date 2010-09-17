#!/usr/bin/env python
# encoding: utf-8
"""
bookkeeping/cyberlogi.py - bookkeeping-Funktionen für Cyberlogi implementiert
verwended Xero.com als backend

Created by Maximillian Dornseif on 2010-06-04.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import base64
import binascii
import datetime
import huTools.unicode
import oauth2 as oauth
import urllib
import xml.etree.ElementTree as ET
#from cs.keychain import XERO_CONSUMER_KEY, XERO_CONSUMER_SECRET, XERO_RSACERT, XERO_RSAKEY
from decimal import Decimal
from huTools.calendar.formats import convert_to_date
from huTools.monetary import cent_to_euro
from huTools.structured import make_struct
from tlslite.utils import keyfactory

# Testing:
from bookkeeping.keychain import XERO_CONSUMER_KEY, XERO_CONSUMER_SECRET, XERO_RSACERT, XERO_RSAKEY


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

    def build_signature_base_string(self, oauth_request, consumer, token):
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
        return XERO_RSACERT

    def _fetch_private_cert(self, oauth_request):
        return XERO_RSAKEY


def xero_request(url, method='GET', body='', get_parameters=None, headers=None):
    """Request an xero ausführen"""

    base_url = 'https://api.xero.com/api.xro/2.0/'
    url = base_url + url

    consumer = oauth.Consumer(key=XERO_CONSUMER_KEY, secret=XERO_CONSUMER_SECRET)
    client = oauth.Client(consumer, token=oauth.Token(key=XERO_CONSUMER_KEY, secret=XERO_CONSUMER_SECRET))
    client.set_signature_method(XeroOAuthSignatureMethod_RSA_SHA1())

    if headers is None:
        headers = {}

    if get_parameters:
        url = "%s?%s" % (url, urllib.urlencode(get_parameters))

    response, content = client.request(url, method, body=body, headers=headers)
    
    if response.status == 404:
        return None
    
    if response.status != 200:
        # handle occasional server side glitches
        if content == 'oauth_problem=signature_invalid&oauth_problem_advice=Failed%20to%20validate%20signature':
            return xero_request(url, method, body, get_parameters, headers)
        raise RuntimeError("Return code %s for %s: %s" % (response.status, url, content))
    return content


def orderline(description, qty, price, account_code):
    """Erzeuge eine Orderline als XML-Baum"""
    
    lineitem = ET.Element('LineItem')
    ET.SubElement(lineitem, 'Description').text = description
    ET.SubElement(lineitem, 'Quantity').text = str(qty)
    ET.SubElement(lineitem, 'UnitAmount').text = str(price)
    ET.SubElement(lineitem, 'AccountCode').text = account_code
    return lineitem


def create_contact(invoice, address_type='POBOX'):
    """
    Erzeuge ein Xero-kompatibles Contact-Element
    
    Der Parameter invoice folgt dem AddressProtocol
    """
    
    contact = ET.Element('Contact')
    
    ET.SubElement(contact, 'Name').text = invoice.name1
    ET.SubElement(contact, 'EmailAddress').text = huTools.unicode.deUmlaut(invoice.mail)
    address = ET.SubElement(ET.SubElement(contact, 'Addresses'), 'Address')
    ET.SubElement(address, 'AddressType').text = address_type
    
    if invoice.name2:
        ET.SubElement(address, 'AddressLine1').text = invoice.name2
        ET.SubElement(address, 'AddressLine2').text = invoice.strasse
    else:
        ET.SubElement(address, 'AddressLine1').text = invoice.strasse
    
    if invoice.attention_to:
        ET.SubElement(address, 'AttentionTo').text = invoice.attention_to

    ET.SubElement(address, 'City').text = invoice.ort
    ET.SubElement(address, 'PostalCode').text = invoice.plz
    ET.SubElement(address, 'Country').text = invoice.land
    
    return contact


def create_invoice(invoice_type, date, tax_included=False, invoice_number=None, reference=None, duedays=None):
    """Erzeuge die "Kopfdaten" einer Xero-Rechnung"""
    
    invoice = ET.Element('Invoice')
    ET.SubElement(invoice, 'Type').text = invoice_type
    ET.SubElement(invoice, 'Status').text = 'SUBMITTED'
    ET.SubElement(invoice, 'LineAmountTypes').text = 'Inclusive' if tax_included else 'Exclusive'
    
    if reference:
        print "setze referenz auf %s" % reference
        ET.SubElement(invoice, 'Reference').text = reference
        
    if invoice_number:
        ET.SubElement(invoice, 'InvoiceNumber').text = invoice_number

    leistungsdatum = convert_to_date(date)
    if duedays:
        timedelta = datetime.timedelta(days=duedays)
        ET.SubElement(invoice, 'DueDate').text = (leistungsdatum + timedelta).isoformat()
    ET.SubElement(invoice, 'Date').text = leistungsdatum.isoformat()
    
    return invoice


def store_invoice(invoice, tax_included=False, xero_should_generate_invoice_number=False):
    """
    Erzeugt eine (Ausgangs-) Rechnung anhand des Simple Invoice Protocol.
    Siehe https://github.com/hudora/CentralServices/blob/master/doc/SimpleInvoiceProtocol.markdown
    """

    VERSANDKOSTEN_ACCOUNT = '8402'
    DEFAULT_ACCOUNT = '8404'

    invoice = make_struct(invoice, default='')
    
    # kwargs sind die Keyword-Parameter für create_invoice
    kwargs = {'reference': invoice.kundenauftragsnr or invoice.guid}
    if not xero_should_generate_invoice_number:
        kwargs['invoice_number'] = invoice.guid
    if invoice.zahlungsziel:
        kwargs['duedays'] = invoice.zahlungsziel
    invoice_element = create_invoice('ACCREC', invoice.leistungszeitpunkt, tax_included=tax_included, **kwargs)
    
    # Orderlines hinzufügen:
    lineitems = ET.SubElement(invoice_element, 'LineItems')
    
    # infotext_kunde als Orderline ohne Wert und Konto hinzufügen
    if invoice.infotext_kunde:
        lineitems.append(orderline(invoice.infotext_kunde, 0, 0, ''))
    
    for item in invoice.orderlines:
        item = make_struct(item)
    
        buchungskonto = DEFAULT_ACCOUNT
        
        # Wenn wir hier Ersatzteile von Neuware trennen könnten, könnten wir die Neuware auf Konto 8406
        # und hoogoo Scooter auf Konto 8410 buchen.
        if item.buchungskonto:
            buchungskonto = item.buchungskonto
        
        text = unicode(item.artnr)
        if item.infotext_kunde:
            text = u"%s - %s" % (item.artnr, item.infotext_kunde)
        lineitems.append(orderline(text, item.menge, cent_to_euro(item.preis), buchungskonto))

    if invoice.versandkosten:
        lineitems.append(orderline('Verpackung & Versand', 1, cent_to_euro(invoice.versandkosten), VERSANDKOSTEN_ACCOUNT))

    # Erzeuge Adressdaten und füge sie hinzu
    invoice_element.append(create_contact(invoice))
    
    root = ET.Element('Invoices')
    root.append(invoice_element)
    body = ET.tostring(root, encoding='utf-8')
    content = xero_request('Invoices', 'PUT', body, headers={'content-type': 'text/xml; charset=utf-8'})
    tree = ET.fromstring(content)
    return tree.findtext('Invoices/Invoice/InvoiceID')


def store_inbound_invoice(invoice, netto=True):
    """
    Übertrage eine Eingangsrechnung an Cyberlogi nach xero.com

    Der Rückgabewert ist die xero.com InvoiceID
    """

    SKONTO_ACCOUNT = '3736'
    VERSANDKOSTEN_ACCOUNT = '3801'
    WAREN_ACCOUNT = '3400'

    invoice = make_struct(invoice)
    
    # Reference-Tag kann nur bei Type == 'ACCREC' gesetzt werden
    # Bei 'ACCPAY' bleibt wohl nur der Weg, die InvoiceNumber zu setzen
    # ET.SubElement(invoice, 'Reference').text = invoice.guid
    
    invoice_element = create_invoice('ACCPAY', invoice.leistungszeitpunkt,
                                     tax_included=netto,
                                     invoice_number="%s %s" % (invoice.guid, invoice.kundenauftragsnr),
                                     duedays=getattr(invoice, 'zahlungsziel', None))
    
    lineitems = ET.SubElement(invoice_element, 'LineItems')
    if invoice.infotext_kunde:
        lineitems.append(orderline(invoice.infotext_kunde, 0, 0, ''))
    if invoice.kundenauftragsnr:
        lineitems.append(orderline('Kundenauftragsnr: %s' % invoice.kundenauftragsnr, 0, 0, ''))
    
    total = Decimal()
    for item in invoice.orderlines:
        item = make_struct(item)
        preis = 0
        if item.preis and item.menge:
            preis = cent_to_euro(item.preis / item.menge)
        # Versandkosten mit spezieller AccountID verbuchen
        if 'ersandkosten' in item.infotext_kunde:
            lineitems.append(orderline('Paketversand DPD', item.menge, preis, VERSANDKOSTEN_ACCOUNT))
        else:
            lineitems.append(orderline('%s - %s' % (item.artnr, item.infotext_kunde), item.menge, preis, WAREN_ACCOUNT))

        total += preis * item.menge

    # 2 Prozent Skonto innerhalb von 8 Tagen
    skonto_date = datetime.date.today() + datetime.timedelta(days=8)
    lineitems.append(orderline('Skonto bis %s' % skonto_date.strftime('%Y-%m-%d'), '0.02', -total, SKONTO_ACCOUNT))
    
    # Kommt das nicht aus der Invoice? TODO: Wo wird store_hudorainvoice überhaupt verwendet?
    contact = {'name1': 'HUDORA GmbH', 'mail': 'a.jaentsch@hudora.de', 'attention_to': 'Buchhaltung',
               'city': 'Remscheid', 'plz': '42897', 'land': 'DE'}
    contact = make_struct(contact, default='')
    
    invoice_element.append(create_contact(contact, address_type='STREET'))

    root = ET.Element('Invoices')
    root.append(invoice_element)
    body = ET.tostring(root, encoding='utf-8')
    content = xero_request('Invoices', 'PUT', body, headers={'content-type': 'text/xml; charset=utf-8'})
    tree = ET.fromstring(content)
    return tree.findtext('Invoices/Invoice/InvoiceID')


def get_invoice(invoice_id):
    """
    Liefert eine Rechnung aus Xero zurück.

    Wenn keine Rechnung zu der Lieferscheinnummer existiert, wird None zurückgegeben.
    """

    url = 'Invoices/%s' % urllib.quote(invoice_id)
    content = xero_request(url, get_parameters={'where': 'Status!="DELETED"'})
    
    if not content:
        return []
    
    invoices = []
    tree = ET.fromstring(content)
    for element in tree.getiterator('Invoice'):
        invoice = {}
        for attr in ('Reference', 'Date', 'DueDate', 'Status', 'LineAmountTypes', 'SubTotal', 'TotalTax', 'Total',
                    'UpdatedDateUTC', 'CurrencyCode' 'InvoiceID' 'InvoiceNumber' 'AmountDue' 'AmountPaid'):
            tmp = element.findtext(attr)
            if not tmp is None:
                invoice[attr] = tmp
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
    """Return list of invoice ids"""
    
    tmp = ['Status!="DELETED"', 'Status!="VOIDED"']
    if parameters:
        tmp.extend(parameters)
    get_parameters = {'where': "&&".join(tmp)}
    content = xero_request('Invoices', get_parameters=get_parameters)
    tree = ET.fromstring(content)
    return [element.text for element in tree.findall(xpath)]


# Zur Vereinheitlichung von SoftM- und Xero-Rechnungen:
# class Invoice(object):
#     """Implementierung der Rechnungsklasse für Xero"""
#     
#     def __init__(self):
#         pass
#     
#     @classmethod
#     def get(cls, invoice_id):
#         instance = cls()
#         
#         invoice = get_invoice(invoice_id=invoice_id)
#         instance. 
#         return instance


def list_creditnotes(parameters=None, xpath='CreditNotes/CreditNote/CreditNoteID'):
    """Return list of creditnote ids"""
    
    tmp = ['Status!="DELETED"', 'Status!="VOIDED"']
    if parameters:
        tmp.extend(parameters)
    get_parameters = {'where': "&&".join(tmp)}
    content = xero_request('CreditNote', get_parameters=get_parameters)
    tree = ET.fromstring(content)
    return [element.text for element in tree.findall(xpath)]


# Gutschriften - Credit Notes
def get_creditnote(creditnote_id):
    """
    Liefert eine Gutschrift aus Xero zurück.

    Wenn keine Gutschrift existiert, wird None zurückgegeben.
    """

    url = 'CreditNotes/%s' % urllib.quote(creditnote_id)
    content = xero_request(url, get_parameters={'where': 'Status!="DELETED"'})
    
    print content
    
    if not content:
        return []
    
    creditnotes = []
    tree = ET.fromstring(content)
    for element in tree.getiterator('CreditNote'):
        creditnote = {}
        for attr in ('Reference', 'Date', 'Status', 'LineAmountTypes', 'SubTotal', 'TotalTax', 'Total',
                    'UpdatedDateUTC', 'CurrencyCode' 'CreditNoteID' 'CreditNoteNumber' 'FullyPaidOnDate'):
            tmp = element.findtext(attr)
            if not tmp is None:
                creditnote[attr] = tmp
        creditnotes.append(creditnote)        
    return creditnotes


def create_creditnote(date, tax_included=False, creditnote_number=None, reference=None):
    """Erzeuge die "Kopfdaten" einer Xero-Rechnung"""
    
    creditnote = ET.Element('CreditNote')
    # ET.SubElement(creditnote, 'Status').text = 'SUBMITTED'
    ET.SubElement(creditnote, 'LineAmountTypes').text = 'Inclusive' if tax_included else 'Exclusive'
    ET.SubElement(creditnote, 'Type').text = 'ACCRECCREDIT'
    
    if reference:
        ET.SubElement(creditnote, 'Reference').text = reference
        
    if creditnote_number:
        ET.SubElement(creditnote, 'CreditNoteNumber').text = creditnote_number

    leistungsdatum = convert_to_date(date)
    ET.SubElement(creditnote, 'Date').text = leistungsdatum.isoformat()
    ET.SubElement(creditnote, 'DueDate').text = leistungsdatum.isoformat()
    
    return creditnote


def store_creditnote(data, autogenerate_number=False, tax_included=False):
    """
    Erzeugt eine Gutschrift
    """
    DEFAULT_ACCOUNT = '710'
    
    data = make_struct(data, default='')
    
    # kwargs sind die Keyword-Parameter für create_creditnote
    kwargs = {'reference': data.kundenauftragsnr or data.guid}
    if not autogenerate_number:
        kwargs['creditnote_number'] = data.guid
    creditnote_element = create_creditnote(data.leistungszeitpunkt, tax_included=tax_included, **kwargs)
    
    # Orderlines hinzufügen:
    lineitems = ET.SubElement(creditnote_element, 'LineItems')
        
    for item in data.orderlines:
        item = make_struct(item)
    
        buchungskonto = DEFAULT_ACCOUNT
        if item.buchungskonto:
            buchungskonto = item.buchungskonto
        
        text = unicode(item.artnr)
        if item.infotext_kunde:
            text = u"%s - %s" % (item.artnr, item.infotext_kunde)
        lineitems.append(orderline(text, item.menge, cent_to_euro(item.preis), buchungskonto))

    # Erzeuge Adressdaten und füge sie hinzu
    creditnote_element.append(create_contact(data))
    #ET.SubElement(ET.SubElement(creditnote_element, 'Contact'), 'Name').text = 'X'
    
    root = ET.Element('CreditNotes')
    root.append(creditnote_element)
    body = ET.tostring(root, encoding='utf-8')
    content = xero_request('CreditNote', 'PUT', body, headers={'content-type': 'text/xml; charset=utf-8'})
    tree = ET.fromstring(content)
    return tree.findtext('CreditNotes/CreditNote/CreditNoteID')
