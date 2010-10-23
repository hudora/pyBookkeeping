#!/usr/bin/env python
# encoding: utf-8

"""
CCT.py - Create CCT messages

Created by Christian Klein on 2010-08-17.
Copyright (c) 2010 HUDORA GmbH. All rights reserved.
"""

from decimal import Decimal
import datetime
import xml.etree.ElementTree as ET


def create_cct(transactions, guid, debtor, iban, bic):
    """Erzeuge eine XML-Datei"""
    
    root = ET.Element('Document')
    root.attrib['xmlns'] = "urn:iso:std:iso:20022:tech:xsd:pain.001.002.03"
    root.attrib['xmlns:xsi'] = "http://www.w3.org/2001/XMLSchema-instance"
    root.attrib['xsi:schemaLocation'] = "urn:iso:std:iso:20022:tech:xsd:pain.001.002.03 pain.001.002.03.xsd"
    
    ccti = ET.SubElement(root, 'CstmrCdtTrfInitn')
    
    header = ET.SubElement(ccti, 'GrpHdr')    
    ET.SubElement(header, 'MsgId').text = guid # message id - für jede neue pain-Nachricht einen neuen Wert
    ET.SubElement(header, 'CreDtTm').text = datetime.datetime.now().isoformat()
    ET.SubElement(header, 'NbOfTxs').text = str(len(transactions))
    # Optional: Summe der Transaktionen: ET.SubElement(header, 'CtrlSum').text = sum()
    ET.SubElement(ET.SubElement(header, 'InitgPty'), 'Nm').text = debtor
            
    # Payment Instruction Information
    # Satz von Angaben (z.B. Auftraggeberkonto, Ausführungstermin), welcher für alle Einzeltransaktionen gilt.
    # Entspricht einem logischen Sammler innerhalb einer physikalischen Datei.
    # Hinweis: Diese Implementierung unterstützt derzeit nur eine einzelne PII
    
    pii = ET.SubElement(ccti, 'PmtInf')
    ET.SubElement(pii, 'PmtInfId').text = 'PmtInf-%s' % guid
    ET.SubElement(pii, 'PmtMtd').text = 'TRF'
    ET.SubElement(pii, 'NbOfTxs').text = str(len(transactions))
    ET.SubElement(pii, 'CtrlSum').text = "0" # sum([])
    
    # Payment Type Information
    pti = ET.SubElement(pii, 'PmtTpInf')
    ET.SubElement(ET.SubElement(pti, 'SvcLvl'), 'Cd').text = 'SEPA'
    
    # Requested Execution Date
    ET.SubElement(pii, 'ReqdExctnDt').text = datetime.date.today().isoformat() # XXX
    
    # Debtor
    dbtr = ET.SubElement(ET.SubElement(pii, 'Dbtr'), 'Nm').text = debtor
    
    # Debtor Account
    dbtracct = ET.SubElement(pii, 'DbtrAcct')
    ET.SubElement(ET.SubElement(dbtracct, 'Id'), 'IBAN').text = iban
    
    # Debtor Agent
    dbtragt = ET.SubElement(pii, 'DbtrAgt')
    ET.SubElement(ET.SubElement(dbtragt, 'FinInstnId'), 'BIC').text = bic
	
    # Charge Bearer
    ET.SubElement(pii, 'ChrgBr').text = 'SLEV'
    
    for transaction in transactions:
        txinf = ET.SubElement(pii, 'CdtTrfTxInf')
        ET.SubElement(ET.SubElement(txinf, 'PmtId'), 'EndToEndId').text = transaction['guid']
        
        # Amount
        amount = ET.SubElement(ET.SubElement(txinf, 'Amt'), 'InstdAmt', Ccy='EUR').text = "%.2f" % transaction['amount']
        
        # Creditor Agent
        cdtragt = ET.SubElement(txinf, 'CdtrAgt')
        ET.SubElement(ET.SubElement(cdtragt, 'FinInstnId'), 'BIC').text = transaction['bic']
        
        # Creditor
        ET.SubElement(ET.SubElement(txinf, 'Cdtr'), 'Nm').text = transaction['creditor']
        
        # Creditor Account
        dbtracct = ET.SubElement(txinf, 'CdtrAcct')
        ET.SubElement(ET.SubElement(dbtracct, 'Id'), 'IBAN').text = transaction['iban']
        
        # Remittance Info
        ET.SubElement(ET.SubElement(txinf, 'RmtInf'), 'Ustrd').text = transaction['info']

    return root


def validate_cct(document, schema):
    """Validiere CCT-Nachricht mit einem XML-Schema"""
    
    import lxml.etree
    from cStringIO import StringIO
    
    xmlschema = lxml.etree.XMLSchema(file=schema)
    xmlschema.assertValid(lxml.etree.parse(StringIO(document)))


if __name__ == "__main__":
    transaction = {'guid': '1234', 'amount': Decimal('0.11'), 'bic': 'AAAAAAAA', 'iban': 'DE00123456781234567890',
                   'creditor': 'Empfaenger', 'info': 'TESTUEBERWEISUNG'}
    
    tree = create_cct([transaction], "guid-1111", "Absender", "DE00123456781234567890", "BBBBBBBB")
    doc = ET.tostring(tree)
    
    # validate_cct(doc, '/path/to/pain.001.002.03.xsd')