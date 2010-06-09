#!/usr/bin/env python
# encoding: utf-8
"""
bookkeeping/cyberlogi.py Konkrete Implementierung der Klasse für cyberlogi
verwended Xero.com als backend

Created by Maximillian Dornseif on 2010-06-04.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

from cs.keychain import XERO_CONSUMER_KEY, XERO_CONSUMER_SECRET, XERO_RSACERT, XERO_RSAKEY
from tlslite.utils import cryptomath
from tlslite.utils import keyfactory
import binascii
import bookkeeping.abstract
import datetime
import oauth2 as oauth
import xml.etree.ElementTree as ET


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

    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (oauth.escape(oauth_request.method),
               oauth.escape(oauth_request.normalized_url),
               oauth.escape(oauth_request.get_normalized_parameters()),
              )
        key = ''
        raw = '&'.join(sig)
        return key, raw

    def sign(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, base_string = self.build_signature_base_string(oauth_request, consumer, token)
        # Fetch the private key cert based on the request
        cert = self._fetch_private_cert(oauth_request)
        # Pull the private key from the certificate
        privatekey = keyfactory.parsePrivateKey(cert)
        # Convert base_string to bytes
        #base_string_bytes = cryptomath.createByteArraySequence(base_string)
        # Sign using the key
        signed = privatekey.hashAndSign(base_string)
        return binascii.b2a_base64(signed)[:-1]

    def check_signature(self, oauth_request, consumer, token, signature):
        decoded_sig = base64.b64decode(signature)
        key, base_string = self.build_signature_base_string(oauth_request, consumer, token)
        # Fetch the public key cert based on the request
        cert = self._fetch_public_cert(oauth_request)
        # Pull the public key from the certificate
        publickey = keyfactory.parsePEMKey(cert, public=True)
        # Check the signature
        ok = publickey.hashAndVerify(decoded_sig, base_string)
        return ok


class XeroOAuthSignatureMethod_RSA_SHA1(OAuthSignatureMethod_RSA_SHA1):
  def _fetch_public_cert(self, oauth_request):
    return XERO_RSACERT

  def _fetch_private_cert(self, oauth_request):
    return XERO_RSAKEY


def xero_request(url, method='GET', body='', getparameters=None):
    """Request an xero durchführen"""
    
    # Xero want Two-legged OAuth which useds the same key in both stages.
    consumer = oauth.Consumer(key=XERO_CONSUMER_KEY, secret=XERO_CONSUMER_SECRET)
    client = oauth.Client(consumer, token=oauth.Token(key=XERO_CONSUMER_KEY, secret=XERO_CONSUMER_SECRET))
    client.set_signature_method(XeroOAuthSignatureMethod_RSA_SHA1())
    if getparameters is None:
        getparameters = {}
    url = "%s?%s" % (url, urllib.urlencode(getparameters))
    response, content = client.request(url, method, body=body, headers={'content-type': 'text/xml; charset=utf-8'})
    if response['status'] != '200':
        raise RuntimeError("Return code %s for %s" % (response['status'], url))
    return content


# siehe http://stackoverflow.com/questions/1305532/convert-python-dict-to-object
class Struct(object):
    def __init__(self, **entries): 
        self.__dict__.update(entries)
        self.default = None

    def __getattr__(self, name):
        return self.default


def make_struct(obj):
    """Converts a dict to an Object, leaves an Object untouched.
    Read Only!
    """
    if not hasattr(obj, '__dict__'):
        return Struct(obj)
    return obj


def add_orderline(root, description, qty, price, account_code):
    """Füge Orderline zu XML-Baum hinzu"""
    lineitem = ET.SubElement(root, 'LineItem')
    ET.SubElement(lineitem, 'Description').text = description
    ET.SubElement(lineitem, 'Quantity').text = str(qty)
    ET.SubElement(lineitem, 'UnitAmount').text = str(price)
    ET.SubElement(lineitem, 'AccountCode').text = account_code


def check_invoice(*args, **kwargs):
    return True


def store_invoice(invoice):
    """
    Erzeugt eine (Ausgangs-) Rechnung anhand des Simple Invoice Protocol.
    Siehe https://github.com/hudora/CentralServices/blob/master/doc/SimpleInvoiceProtocol.markdown
    
    """

    if not check_invoice(invoice) == True:
        raise RuntimeError("Invalid Invoice")
    
    invoice = make_struct(invoice)
    
    root = ET.Element('Invoices')
    invoice = ET.SubElement(root, 'Invoice')
    ET.SubElement(invoice, 'Type').text = 'ACCREC'
    ET.SubElement(invoice, 'Status').text = 'SUBMITTED'
    ET.SubElement(invoice, 'Date').text = invoice.leistungsdatum
    ET.SubElement(invoice, 'InvoiceNumber').text = invoice.guid

    if invoice.zahlungsziel:
        ET.SubElement(invoice, 'DueDate').text = (invoice.leistungsdatum + datetime.timedelta(days=invoice.zahlungsziel)).strftime('%Y-%m-%d')

    if invoice.kundenauftragsnr:
        ET.SubElement(invoice, 'Reference').text = invoice.kundenauftragsnr
    ET.SubElement(invoice, 'LineAmountTypes').text = 'Exclusive'

    # Füge die ConsignmentItems und die Versandkosten hinzu
    lineitems = ET.SubElement(invoice, 'LineItems')
    for item in consignment.consignmentitem_set.all():
        add_orderline(lineitems, u"%s - %s" % (item.artnr, item.text), item.quantity, item.unit_price, '200')
    add_orderline(lineitems, 'Verpackung & Versand', 1, consignment.versandkosten, '201')
    
    # Adressdaten
    contact = ET.SubElement(invoice, 'Contact')
    ET.SubElement(contact, 'Name').text = ' '.join([invoice.name1, invoice.name2])
    ET.SubElement(contact, 'EmailAddress').text = invoice.email
    addresses = ET.SubElement(contact, 'Addresses')
    address = ET.SubElement(addresses, 'Address')
    ET.SubElement(address, 'AddressType').text = 'STREET'
    ET.SubElement(address, 'AttentionTo').text = invoice.name1
    
    if invoice.name2:
        ET.SubElement(address, 'AddressLine1').text = invoice.name2
    
    ET.SubElement(address, 'City').text = invoice.ort   
    ET.SubElement(address, 'PostalCode').text = invoice.plz
    ET.SubElement(address, 'Country').text = invoice.land
    body = ET.tostring(root, encoding='utf-8')
    
    content = xero_request(URL_BASE, "PUT", body=body, headers={'content-type': 'text/xml; charset=utf-8'})
    return content


# Fast komplette Kopie von store_invoice
# Nur die AccountCodes sind unterschiedlich
def store_hudorainvoice(datum, mengen, preise, namen):
    """Erzeuge eingehende Rechnung und übertrage zu xero.com"""
    
    root = ET.Element('Invoices')
    invoice = ET.SubElement(root, 'Invoice')
    ET.SubElement(invoice, 'Reference').text = u'Online_%s' % datum
    ET.SubElement(invoice, 'Type').text = 'ACCPAY'
    ET.SubElement(invoice, 'Status').text = 'SUBMITTED'
    ET.SubElement(invoice, 'LineAmountTypes').text = 'Inclusive'
    ET.SubElement(invoice, 'Date').text = datum.strftime('%Y-%m-%d')
    ET.SubElement(invoice, 'DueDate').text = (datum + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    lineitems = ET.SubElement(invoice, 'LineItems')

    versandkosten = 4.0
    add_orderline(lineitems, 'Paketversand DPD', len(mengen), versandkosten, '4730')

    for artnr in mengen.keys():
        lineitem = ET.SubElement(lineitems, 'LineItem')
        ET.SubElement(lineitem, 'Description').text = "%s - %s" % (artnr, namen.get('artnr', ''))
        ET.SubElement(lineitem, 'Quantity').text = str(mengen[artnr])
        ET.SubElement(lineitem, 'UnitAmount').text = str(preise[artnr]/mengen[artnr])
        ET.SubElement(lineitem, 'AccountCode').text = '3400'

    contact = ET.SubElement(invoice, 'Contact')
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
    return content


def get_invoice(lieferscheinnr):
    """
    Liefert eine Rechnung aus Xero zurück.
    
    Wenn keine Rechnung zu der Lieferscheinnummer existiert, wird None zurückgegeben.
    """

    url = "%s?%s" % (URLBASE, urllib.urlencode({'where': 'Status!="DELETED"&&Status!="VOIDED"&&Reference=="%s"' % lieferscheinnr}))
    content = xero_request(url)
    tree = ET.fromstring(content)
    invoices = []
    for element in xml.getiterator('Invoice'):
        invoice = {}
        for attr in '''Reference Date DueDate Status LineAmountTypes SubTotal TotalTax Total UpdatedDateUTC
                       CurrencyCode InvoiceID InvoiceNumber AmountDue AmountPaid'''.split():
            invoice[attr] = element.find(attr).text
        invoices.append(invoice)
    return invoices
