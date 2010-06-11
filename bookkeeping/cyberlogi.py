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
import datetime
import oauth2 as oauth
import urllib
import xml.etree.ElementTree as ET
from cs.keychain import XERO_CONSUMER_KEY, XERO_CONSUMER_SECRET, XERO_RSACERT, XERO_RSAKEY
from decimal import Decimal
from tlslite.utils import keyfactory
from bookkeeping.struct import make_struct

URL_BASE = 'https://api.xero.com/api.xro/2.0/Invoices'


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
        return XERO_RSACERT

    def _fetch_private_cert(self, oauth_request):
        return XERO_RSAKEY


def xero_request(url, method='GET', body='', get_parameters=None, headers=None):
    """Request an xero durchführen"""
    
    consumer = oauth.Consumer(key=XERO_CONSUMER_KEY, secret=XERO_CONSUMER_SECRET)
    client = oauth.Client(consumer, token=oauth.Token(key=XERO_CONSUMER_KEY, secret=XERO_CONSUMER_SECRET))
    client.set_signature_method(XeroOAuthSignatureMethod_RSA_SHA1())
    
    if headers is None:
        headers = {}

    if not get_parameters is None:
        url = "%s?%s" % (url, urllib.urlencode(get_parameters))

    response, content = client.request(url, method, body=body, headers={})
    if response['status'] != '200':
        raise RuntimeError("Return code %s for %s" % (response['status'], url))
    return content


def add_orderline(root, description, qty, price, account_code):
    """Füge Orderline zu XML-Baum hinzu"""
    lineitem = ET.SubElement(root, 'LineItem')
    ET.SubElement(lineitem, 'Description').text = description
    ET.SubElement(lineitem, 'Quantity').text = str(qty)
    ET.SubElement(lineitem, 'UnitAmount').text = str(price)
    ET.SubElement(lineitem, 'AccountCode').text = account_code



def store_invoice(invoice):
    """
    Erzeugt eine (Ausgangs-) Rechnung anhand des Simple Invoice Protocol.
    Siehe https://github.com/hudora/CentralServices/blob/master/doc/SimpleInvoiceProtocol.markdown    
    """
    
    invoice = make_struct(invoice)    
    root = ET.Element('Invoices')
    invoice = ET.SubElement(root, 'Invoice')
    ET.SubElement(invoice, 'Type').text = 'ACCREC'
    ET.SubElement(invoice, 'Status').text = 'SUBMITTED'
    ET.SubElement(invoice, 'Date').text = consignment.leistungszeitpunkt
    ET.SubElement(invoice, 'InvoiceNumber').text = consignment.guid

    if consignment.zahlungsziel:
        timedelta = datetime.timedelta(days=consignment.zahlungsziel)
        ET.SubElement(invoice, 'DueDate').text = (consignment.leistungszeitpunkt + timedelta).strftime('%Y-%m-%d')

    if consignment.kundenauftragsnr:
        ET.SubElement(invoice, 'Reference').text = consignment.kundenauftragsnr
    ET.SubElement(invoice, 'LineAmountTypes').text = 'Exclusive'

    # Füge die ConsignmentItems und die Versandkosten hinzu
    lineitems = ET.SubElement(invoice, 'LineItems')
    for item in consignment.orderlines:
        item = make_struct(item) # XXX rekursives Verhalten mit in make_struct packen
        add_orderline(lineitems, u"%s - %s" % (item.artnr, item.guid), item.menge, item.preis, '200')
    add_orderline(lineitems, 'Verpackung & Versand', 1, consignment.versandkosten, '201')
    
    # Adressdaten
    contact = ET.SubElement(invoice, 'Contact')
    ET.SubElement(contact, 'Name').text = ' '.join([consignment.name1, consignment.name2])
    ET.SubElement(contact, 'EmailAddress').text = consignment.email
    addresses = ET.SubElement(contact, 'Addresses')
    address = ET.SubElement(addresses, 'Address')
    ET.SubElement(address, 'AddressType').text = 'STREET'
    ET.SubElement(address, 'AttentionTo').text = consignment.name1
    
    if consignment.name2:
        ET.SubElement(address, 'AddressLine1').text = consignment.name2
    
    ET.SubElement(address, 'City').text = consignment.ort   
    ET.SubElement(address, 'PostalCode').text = consignment.plz
    ET.SubElement(address, 'Country').text = consignment.land
    body = ET.tostring(root, encoding='utf-8')
    
    content = xero_request(URL_BASE, "PUT", body=body, headers={'content-type': 'text/xml; charset=utf-8'})
    tree = ET.fromstring(content)
    return tree.find('Invoices/Invoice/InvoiceID').text


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
def store_hudorainvoice(invoice, netto=True):
    """
    Übertrage eine Eingangsrechnung von HUDORA an Cyberlogi an xero.com
    
    Der Rückgabewert ist die xero.com InvoiceID
    """
    
    invoice = make_struct(invoice)
    
    root = ET.Element('Invoices')
    invoice_element = ET.SubElement(root, 'Invoice')
    # Reference-Tag kann nur bei Type == 'ACCREC' gesetzt werden
    # Bei 'ACCPAY' bleibt wohl nur der Weg, die InvoiceNumber zu setzen
    # ET.SubElement(invoice, 'Reference').text = invoice.guid
    
    # Die bisherigen Rechnungen hatten als InvoiceNumber "Online_%s" % leistungsdatum
    # gesetzt.
    # Das verursacht jedoch Probleme beim Wiederfinden von Rechnungen,
    # d.h. bei der Überprüfung, ob eine Rechnung schon in xero.com ist
    # (wenn z.B. kein Lieferdatum gesetzt ist oder es keine Online-Shop-Rechnung ist)
    
    ET.SubElement(invoice_element, 'InvoiceNumber').text = invoice.guid
    ET.SubElement(invoice_element, 'Type').text = 'ACCPAY'
    ET.SubElement(invoice_element, 'Status').text = 'SUBMITTED'
    ET.SubElement(invoice_element, 'LineAmountTypes').text = 'Exclusive' if netto else 'Inclusive'
    ET.SubElement(invoice_element, 'Date').text = invoice.leistungszeitpunkt
    
    if invoice.zahlungsziel:
        timedelta = datetime.timedelta(days=invoice.zahlungsziel)
    else:
        timedelta = datetime.timedelta(days=30)
    leistungsdatum = datetime.datetime.strptime(invoice.leistungszeitpunkt, '%Y-%m-%d')
    ET.SubElement(invoice_element, 'DueDate').text = (leistungsdatum + timedelta).strftime('%Y-%m-%d')
    
    lineitems = ET.SubElement(invoice_element, 'LineItems')
    
    for item in invoice.orderlines:
        item = make_struct(item)
        # Versandkosten mit spezieller AccountID verbuchen
        if item.infotext_kunde == 'Versandkosten':
            add_orderline(lineitems, 'Paketversand DPD', item.menge, cent_to_euro(item.preis / item.menge), '4730')
        
        add_orderline(lineitems,
                      u"%s - %s" % (item.artnr, item.infotext_kunde),
                      item.menge,
                      cent_to_euro(item.preis / item.menge),
                      '3400')
    
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
    tree = ET.fromstring(content)
    return tree.find('Invoices/Invoice/InvoiceID').text


def get_invoice(lieferscheinnr=None, invoice_id=None):
    """
    Liefert eine Rechnung aus Xero zurück.
    
    Wenn keine Rechnung zu der Lieferscheinnummer existiert, wird None zurückgegeben.
    """
    
    if lieferscheinnr is None and invoice_id is None:
        raise ValueError("lieferscheinnr or invoice_id required")
    
    url = URL_BASE    
    parameters = ['Status!="DELETED"', 'Status!="VOIDED"']
    
    if lieferscheinnr:
        parameters.append('Reference=="%s"' % lieferscheinnr)    
    if invoice_id:
        url += '/%s' % invoice_id
    
    get_parameters = {'where': "&&".join(parameters)}    
    content = xero_request(url, get_parameters=get_parameters)
    tree = ET.fromstring(content)
    
    invoices = []
    for element in tree.getiterator('Invoice'):
        invoice = {}
        for attr in '''Reference Date DueDate Status LineAmountTypes SubTotal TotalTax Total UpdatedDateUTC
                       CurrencyCode InvoiceID InvoiceNumber AmountDue AmountPaid'''.split():
            subelement = element.find(attr)
            if not subelement is None:
                invoice[attr] = subelement.text
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
