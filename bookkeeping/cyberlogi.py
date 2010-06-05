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

# OAuthSignatureMethod_RSA_SHA1 is from
# http://gdata-python-client.googlecode.com/svn-history/r576/trunk/src/gdata/oauth/rsa.py


class OAuthSignatureMethod_RSA_SHA1(oauth.SignatureMethod):
    name = "RSA-SHA1"

    def _fetch_public_cert(self, oauth_request):
        raise NotImplementedError

    def _fetch_private_cert(self, oauth_request):
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, consumer, token):
          sig = (
              oauth.escape(oauth_request.method),
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


def xero_request(url, method="GET", body='', getparameters={}):
    # Xero want Two-legged OAuth which useds the same key in both stages.
    consumer = oauth.Consumer(key=XERO_CONSUMER_KEY, secret=XERO_CONSUMER_SECRET)
    client = oauth.Client(consumer, token=oauth.Token(key=XERO_CONSUMER_KEY, secret=XERO_CONSUMER_SECRET))
    client.set_signature_method(XeroOAuthSignatureMethod_RSA_SHA1())
    url = "%s?%s" % (url, urllib.urlencode(getparameters))
    resp, content = client.request(url, Method, body=body, headers={'content-type': 'text/xml; charset=utf-8'})
    if not resp['status'] == '200':
        print url
        print body
        print resp
        print content
        raise RuntimeError
    print content


# siehe http://stackoverflow.com/questions/1305532/convert-python-dict-to-object
class Struct(object):
    def __init__(self, **entries): 
        self.__dict__.update(entries)

    def __getattr__(self, name):
        return None


def make_struct(obj):
    """Converts a dict to an Object, leaves an Object untouched.
    Read Only!
    """
    if not hasattr(obj, '__dict__'):
        return Struct(obv)
    return obj


class CyberlogiBookkeeping(bookkeeping.abstrct.AbsrtactBookkeeping):
    def store_invoice(self, originvoice):
        """Erzeugt eine (Ausgangs-) Rechnung anhand Simvple Incoice Protocol.
        Siehe https://github.com/hudora/CentralServices/blob/master/doc/SimpleInvoiceProtocol.markdown"""

        self.check_invoice(originvoice)
        invoice = make_struct(originvoice)
        root = ET.Element('Invoices')
        invoice = ET.SubElement(root, 'Invoice')
        ET.SubElement(invoice, 'Type').text = 'ACCREC'  # Accounts receivable
        ET.SubElement(invoice, 'Status').text = 'SUBMITTED'
        ET.SubElement(invoice, 'Date').text = invoice.leistungsdatum
        ET.SubElement(invoice, 'InvoiceNumber').text = invoice.guid
        if invoice.zahlungsziel:
            ET.SubElement(invoice, 'DueDate').text = (invoice.leistungsdatum + datetime.timedelta(days=invoice.zahlungsziel)).strftime('%Y-%m-%d')
        if invoice.kundenauftragsnr:
            ET.SubElement(invoice, 'Reference').text = invoice.kundenauftragsnr
        ET.SubElement(invoice, 'LineAmountTypes').text = 'Exclusive'

* *infotext_kunde* - Freitext, der sich an den WarenempfC$nger richtet. Kann z.B. auf der Rechnung
  angedruckt werden. Der Umbruch des Textes kann durch das Backendsystem beliebig erfolgen, deshalb sollte
  der Text keine ZeilenumbrC<che beinhalten. Erscheint mC6glicherweise auch nicht.
* *kundennr* Interne Kundennummer. Kann das [AddressProtocol][2] erweitern. Wenn eine `kundennr`
  angegeben ist und die per [AddressProtocol][2] angegebene Lieferadresse nicht zu der `kundennr` passt,
  handelt es sich um eine abweichende Lieferadresse.
* *absenderadresse* - (mehrzeiliger) String, der die Absenderadresse auf Rechnungen codiert. Solte auch
  die UStID des Absenders enthalten.
* *erfasst_von* - Name der Person oder des Prozesses (bei EDI), der den Auftrag in das System eingespeist hat
* *preis* - Rechnungs-Gesammt-Preis der Orderline in Cent ohne Mehrwertsteuer.

        lineitems = ET.SubElement(invoice, 'LineItems')
        for orderline in invoice['orderlines']:
            lineitem = ET.SubElement(lineitems, 'LineItem')
            ET.SubElement(lineitem, 'Description').text = ' - '.join(orderline.get('artnr'), orderline.get('infotext_kunde'), orderline.get('ean'))
            ET.SubElement(lineitem, 'Quantity').text = orderline['menge']
            ET.SubElement(lineitem, 'UnitAmount').text = str(orderline['preis'])
            ET.SubElement(lineitem, 'AccountCode').text = '200' # Sales
            # orderline/guid
        
        lineitem = ET.SubElement(lineitems, 'LineItem')
        ET.SubElement(lineitem, 'Description').text = 'Verpackung & Versand'
        ET.SubElement(lineitem, 'Quantity').text = '1'
        ET.SubElement(lineitem, 'UnitAmount').text = str(consignment.versandkosten)
        ET.SubElement(lineitem, 'AccountCode').text = '201'
* *versandkosten* - Versandkosten in Cent ohne Mehrwertsteuer
        
        contact = ET.SubElement(invoice, 'Contact')
        ET.SubElement(contact, 'Name').text = ' '.join([c.name1, c.name2])
        ET.SubElement(contact, 'EmailAddress').text = c.email
        addresses = ET.SubElement(contact, 'Addresses')
        address = ET.SubElement(addresses, 'Address')
        ET.SubElement(address, 'AddressType').text = 'STREET'
        ET.SubElement(address, 'AttentionTo').text = c.name1
        if c.name2:
            ET.SubElement(address, 'AddressLine1').text = c.name2
        ET.SubElement(address, 'City').text = c.ort   
        ET.SubElement(address, 'PostalCode').text = c.plz
        ET.SubElement(address, 'Country').text = c.land
        #  <Phones>
        #    <Phone>
        #      <PhoneType>DEFAULT</PhoneType>
        #      <PhoneNumber>07131-1231483</PhoneNumber>
        body = ET.tostring(root, encoding='utf-8')
        
        CONSUMER_KEY = 'OTNMNMQYYJE3NJA3NDA3ZWE0N2IZMG'
        CONSUMER_SECRET = 'CIJBNG9RMALDWJBYCKXIZJ2CQF1TTH'
        
        # Create your consumer with the proper key/secret.
        consumer = oauth.Consumer(key=CONSUMER_KEY, secret=CONSUMER_SECRET)
        # Create our client.
        client = oauth.Client(consumer, token=oauth.Token(key=CONSUMER_KEY, secret=CONSUMER_SECRET))
        client.set_signature_method(XeroOAuthSignatureMethod_RSA_SHA1())
        # The OAuth Client request works just like httplib2 for the most part.
        #resp, content = client.request(REQUEST_TOKEN_URL, "POST")
        urlbase = 'https://api.xero.com/api.xro/2.0/Invoices'
        url = urlbase
        resp, content = client.request(url, "PUT", body=body, headers={'content-type': 'text/xml; charset=utf-8'})
        if not resp['status'] == '200':
            print url
            print body
            print resp
            print content
            raise RuntimeError
        print content



## Per Order

* _kundenauftragsnr_ - Freitext, den der Kunde bei der Bestellung mit angegeben hat, ca. 20 Zeichen.
* *infotext_kunde* - Freitext, der sich an den Warenempfänger richtet. Kann z.B. auf einem Lieferschein angedruckt werden. Der Umbruch des Textes kann durch das Backendsystem beliebig erfolgen, deshalb sollte der Text keine Zeilenumbrüche beinhalten.
* _kundennr_ Interne Kundennummer. Kann das [AddressProtocol][2] erweitern. Wenn eine `kundennr`
  angegeben ist und die per [AddressProtocol][2] angegebene Lieferadresse nicht zu der `kundennr` passt,
  handelt es sich um eine abweichende Lieferadresse.
* _versandkosten_ - Versandkosten in Cent ohne Mehrwertsteuer
* _absenderadresse_ - (mehrzeiliger) String, der die Absenderadresse auf Versandpapieren codiert.
* *erfasst_von* - Name der Person oder des Prozesses (bei EDI), der den Auftrag in das System eingespeist hat.

[2]: http://github.com/hudora/huTools/blob/master/doc/standards/address_protocol.markdown


## Pro Orderline
* **orderline/guid** - Eindeutiger ID der Position. GUID des Auftrags + Positionsnummer funktionieren ganz gut.
* **orderline/menge** - Menge des durch *ean* bezeichneten Artikels, die versendet werden soll.
* **orderline/ean** - EAN des zu versendenen Artikels.
* **orderline/artnr** - Kann als Alternative zur EAN angegeben werden.
* *orderline/infotext_kunde* - Freitext, der sich an den Warenempfänger richtet. Wird nicht bei allen
  Versandwegen angedruckt.
* _orderline/preis_ - Rechnungs-Preis der Orderline in Cent ohne Mehrwertsteuer.

[3]: http://www.ietf.org/rfc/rfc3339.txt
