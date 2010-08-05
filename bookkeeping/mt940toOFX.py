#!/usr/bin/env python
# encoding: utf-8
"""
mt940toOFX.py - Dieses Progrtamm liesst MT940 SWIFT Kontostände und konvertiert sie in OFX.
OFX wurde mit xero.com getestet.

Created by Maximillian Dornseif on 2010-06-05.
Copyright (c) 2010 HUDORA. All rights reserved.
"""


import datetime
import hashlib
import optparse
import os
import re
import sys
import time
import xml.etree.ElementTree as ET


def parse_mt940(data):
    # See https://www.companyworld.com/en/information_services_2006/download_center/files/mt940.pdf
    # https://mijn.ingbank.nl/ing/downloadables/bestandsformate/5899_handboek_mt940_gb_v6.pdf
    auszuege = {}
    for rawrecord in data.split('\n\n'):
        lines = rawrecord.split('\n')
        while lines:
            nextline = lines.pop(0).strip('\r\n')
            while lines and lines[0] and lines[0][0] != ':':
                nextline = nextline + lines.pop(0).strip('\r\n')
            if not nextline:
                continue
            try:
                dummy, typ = nextline.split(':')[:2]
                data = ':'.join(nextline.split(':')[2:])
            except:
                print repr(nextline)
                raise
            quellblz = quellkonto = ''
            if typ == '20':
                transaction_reference_number = data
            elif typ == '25':
                if len(data.split('/')) == 2:
                    blz, account = data.split('/')
                    account = data
                else:
                    account = data.split('/')[-1]
                if account not in auszuege:
                    auszuege[account] = []
            elif typ == '28C':
                statement_nr = data
            elif typ == '60F':
                # C100531EUR44,9
                sign = data[0]
                date = data[1:7]
                currency = data[7:10]
                amount = data[10:]
            elif typ == '61':
                # 1006020601C8,NMSCNONREF
                date = data[0:6]
                buchungsdatum = data[6:10]
                sign = data[10:11]
                data = data[11:]
                if sign == 'R':
                    sign += data[0]
                    data = data[1:]
                data = list(data)
                currency_type = ''
                c = data.pop(0)
                if not c.isdigit():
                    currency_type = c
                    c = data.pop(0)
                amount = ''
                while c != 'N':
                    amount += c
                    c = data.pop(0)
                euro, cent = amount.split(',')
                cent = (cent + '00')[:2]
                amount = "%s.%s" % (euro, cent)
                if sign in ['D', 'RC']:
                    amount = '-%s' % amount
                data = ''.join(data)
                bookingcode = c + data[:3]
                reference = data[3:]
            elif typ == '86':
                elements = data.split('?')
                transaction_code = elements[0][2:]
                buchungstext = elements[1][2:]
                primanota = elements[2][2:]
                verwendungszweck = ''
                absender = ''
                for element in elements[3:]:
                    subtyp = element[:2]
                    element = element[2:]
                    if element == 'GUTSCHRIFTEN' or element.startswith('DATEI NR ') or subtyp == '34':
                        pass  # ignorieren - uninteressant
                    elif subtyp.startswith('2'):
                        verwendungszweck = ' '.join([verwendungszweck, element])
                    elif subtyp == '30':
                        quellblz = element
                    elif subtyp == '31':
                        quellkonto = element
                    elif subtyp.startswith('3'):
                        absender = ' '.join([absender, element])
                # fix simple typos in WLXXXXXXX
                verwendungszweck = re.sub(r'[Ww][Ll] ?(\d\d\d\d\d\d\d)', r'WL\1', verwendungszweck)
                # remove duplicate spaces
                verwendungszweck = re.sub(r' +', r' ', verwendungszweck)
                guid = ':'.join([transaction_reference_number, statement_nr, quellblz, quellkonto, amount, verwendungszweck])
                guid = hashlib.md5(guid).hexdigest()
                description = "Konto %s, BLZ %s" % (quellkonto, quellblz)
                if not absender:
                    absender = '???'
                auszuege[account].append((float(amount), amount, date, absender, guid, bookingcode, verwendungszweck, quellblz, quellkonto, description))
            elif typ == '62F':
                pass  # we ignore closing balance
            else:
                pass
    return auszuege


def write_ofx(account, vorgaenge, inputname):
    transaction_guid = '%s-%s' % (account, inputname)
    root = ET.Element('OFX')
    signonmsgsrsv1 = ET.SubElement(root, 'SIGNONMSGSRSV1')
    sonrs = ET.SubElement(signonmsgsrsv1, 'SONRS')
    status = ET.SubElement(signonmsgsrsv1, 'STATUS')
    ET.SubElement(status, 'CODE').text = '0'
    ET.SubElement(status, 'SEVERITY').text = 'INFO'
    ET.SubElement(sonrs, 'DTSERVER').text =  datetime.datetime.now().strftime('%Y%m%d')
    ET.SubElement(sonrs, 'LANGUAGE').text = 'ENG'
    
    bankmsgsrsv1 = ET.SubElement(root, 'BANKMSGSRSV1')
    stmttrnrs = ET.SubElement(bankmsgsrsv1, 'STMTTRNRS')
    ET.SubElement(stmttrnrs, 'TRNUID').text = transaction_guid
    status = ET.SubElement(stmttrnrs, 'STATUS')
    ET.SubElement(status, 'CODE').text = '0'
    ET.SubElement(status, 'SEVERITY').text = 'INFO'
    
    stmtrs = ET.SubElement(stmttrnrs, 'STMTRS')
    ET.SubElement(stmtrs, 'CURDEF').text = 'EUR'
    bankacctfrom = ET.SubElement(stmtrs, 'BANKACCTFROM')
    ET.SubElement(bankacctfrom, 'BANKID').text = account.split('/')[0]
    ET.SubElement(bankacctfrom, 'ACCTID').text = account.split('/')[-1]
    ET.SubElement(bankacctfrom, 'ACCTTYPE').text = 'CHECKING'
    banktranlist = ET.SubElement(stmtrs, 'BANKTRANLIST')
    deduper = set()
    for line in sorted(vorgaenge, reverse=True):
        sortkey, amount, date, absender, guid, bookingcode, verwendungszweck, quellblz, quellkonto, description = line
        if guid in deduper:
            continue
        deduper.add(guid)
        stmttrn = ET.SubElement(banktranlist, 'STMTTRN')
        ET.SubElement(stmttrn, 'TRNTYPE').text = 'CREDIT'  # CREDIT DEBIT
        # DtPosted Date item was posted, datetime
        ET.SubElement(stmttrn, 'DTPOSTED').text = "20%s" % date
        # Amount, mit '.' getrennt
        ET.SubElement(stmttrn, 'TRNAMT').text = unicode(amount)
        # That is, the <FITID> value must be unique within the account and Financial Institution
        # (independent of the service provider).
        ET.SubElement(stmttrn, 'FITID').text = guid.replace('*', '.')
        verwendungszweck = verwendungszweck.strip()
        # extract references like WL0000000 SFYX0000
        m = re.search(r'(WL\d\d\d\d\d\d\d|SFYX\d\d\d\d)', verwendungszweck)
        if m:
            checknum = m.group(0)
            print checknum
            # reference/Check number, A-12
            ET.SubElement(stmttrn, 'CHECKNUM').text = checknum
        # PAYEE
        ET.SubElement(stmttrn, 'NAME').text = absender.strip()
        # Format: A-255 for <MEMO>, used in V1 message sets A <MEMO> provides additional information
        # about a transaction.
        ET.SubElement(stmttrn, 'MEMO').text = (' '.join([verwendungszweck, description]))[:254]
    
    header = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

"""
    body = ET.tostring(root, encoding='utf-8')
    fname = 'auszug_%s_%s_%s.ofx' % (datetime.date.today(), inputname, account.replace('/','.'))
    print "writing %s" % fname
    fd = open(fname, 'w')
    fd.write(header)
    fd.write(body)
    fd.close()


def write_gdata(account, vorgaenge, inputname):
    """Stores Transaction Information in google Docs"""

    import gdata.spreadsheet.service
    email = options.google_email
    password = options.google_password
    
    spr_client = gdata.spreadsheet.service.SpreadsheetsService()
    spr_client.email = email
    spr_client.password = password
    spr_client.source = 'mt940toOFX'
    spr_client.ProgrammaticLogin()
    
    docs= spr_client.GetSpreadsheetsFeed()
    spreads = [i.title.text for i in docs.entry]
    try:
        spread_number = spreads.index('Kontoauszuege')
    except ValueError:
        print "Spreadsheet 'Kontoauszuege' not found"
        raise

    spreadsheet_key = docs.entry[spread_number].id.text.rsplit('/', 1)[1]
    feed = spr_client.GetWorksheetsFeed(spreadsheet_key)
    worksheet_id = feed.entry[0].id.text.rsplit('/', 1)[1]

    deduper = set()
    for line in sorted(vorgaenge, reverse=True):
        sortkey, amount, date, absender, guid, bookingcode, verwendungszweck, quellblz, quellkonto, description = line
        guid = guid.replace('*', ':')
        if guid in deduper:
            continue
        deduper.add(guid)
        query = gdata.spreadsheet.service.ListQuery()
        query.sq = 'guid="%s"' % guid
        list_feed = spr_client.GetListFeed(spreadsheet_key, worksheet_id, query=query)
        if not int(list_feed.total_results.text):
            d = {}
            d['konto'] = account
            d['betrag'] = unicode(amount)
            d['datum'] = "20%s-%s-%s" % (date[:2], date[2:4], date[4:])
            d['absender'] = absender
            d['verwendugnszweck'] = verwendungszweck.strip()
            d['quellblz'] = quellblz
            d['quellkonto'] = quellkonto
            #d['text'] = description.strip()
            d['guid '] = guid

            entry = spr_client.InsertRow(d, spreadsheet_key, worksheet_id)
            if not isinstance(entry, gdata.spreadsheet.SpreadsheetsList):
              print "Insert row failed."


if __name__ == '__main__':

    parser = optparse.OptionParser()
    parser.add_option('-m', '--google-email', help=u'Ihre Google-Apps E-Mail Adresse')
    parser.add_option('-p', '--google-password', help=u'Ihre Google-Apps')
    options, args = parser.parse_args()

    path = './'
    if len(args):
        path = args[0]

    for fname in [x for x in os.listdir(path) if x.lower().endswith('.sta')]:
        data = []
        print 'processing %s' % os.path.join(path, fname)
        data.append(open(os.path.join(path, fname)).read())
        data = '\n\n'.join(data)

        if not data:
            print "nothing found matching %s" % os.path.join(path, '*.sta')
            sys.exit(1)

        auszuege = parse_mt940(data)
        fname, extension = os.path.splitext(fname)

        for account in auszuege:
            write_ofx(account, auszuege[account], fname)
            if options.google_password and options.google_email:
                write_gdata(account, auszuege[account], fname)
