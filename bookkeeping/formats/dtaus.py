#!/usr/bin/env python
# encoding: utf-8

import datetime
import itertools
import recordbased

DATENSATZ_A = {
               'doc': 'Der Datensatz A enthält den Dateiabsendder und -empfänger, er ist je logische Datei nur einmal vorhanden.',
               'name': 'vorsatz',
               'fields': [
                    dict(length=4, startpos=0, endpos=4, name='record_length', default='0128', fieldclass=recordbased.FixedField),
                    dict(length=1, startpos=4, endpos=5, name='record_type', default='A', fieldclass=recordbased.FixedField),
                    dict(length=2, startpos=5, endpos=7, name='flag', choices=['GK', 'LK']),
                    dict(length=8, startpos=7, endpos=15, name='bankcode'),
                    dict(length=8, startpos=15, endpos=23, name='internal', fieldclass=recordbased.IntegerFieldZeropadded, default=0),
                    dict(length=27, startpos=23, endpos=50, name='sender_name'),
                    dict(length=6, startpos=50, endpos=56, name='file_date', fieldclass=recordbased.DateField, formatstr='%d%m%y'),
                    dict(length=4, startpos=56, endpos=60, name='blank', fieldclass=recordbased.FixedField, default=' ' * 4),
                    dict(length=10, startpos=60, endpos=70, name='account', fieldclass=recordbased.IntegerFieldZeropadded),
                    dict(length=10, startpos=70, endpos=80, name='reference', default=0, fieldclass=recordbased.IntegerFieldZeropadded),
                    dict(length=15, startpos=80, endpos=95, name='reserved', default=' '),
                    dict(length=8, startpos=95, endpos=103, name='execution_date', fieldclass=recordbased.DateField, formatstr='%d%m%Y'),
                    dict(length=24, startpos=103, endpos=127, name='reserved', fieldclass=recordbased.FixedField, default=' ' * 24),
                    dict(length=1, startpos=127, endpos=128, name='currency', fieldclass=recordbased.IntegerField, default=1),
               ]
              }

Vorsatz = recordbased.generate_field_datensatz_class(DATENSATZ_A['fields'], name=DATENSATZ_A['name'], length=128, doc=DATENSATZ_A['doc'])


DATENSATZ_C = {
                 'doc': 'Der Datensatz C enthält Einzelheiten über die auszuführenden Aufträge.',
                 'name': 'zahlungsaustauschsatz',
                 'fields': [
                    dict(length=4, startpos=0, endpos=4, name='record_length', default='0187', fieldclass=recordbased.IntegerFieldZeropadded),
                    dict(length=1, startpos=4, endpos=5, name='record_type', default='C', fieldclass=recordbased.FixedField),
                    dict(length=8, startpos=5, endpos=13, name='xxx_bank_code', default=0, fieldclass=recordbased.IntegerFieldZeropadded),
                    dict(length=8, startpos=13, endpos=21, name='receiver_bankcode', fieldclass=recordbased.IntegerField),
                    dict(length=10, startpos=21, endpos=31, name='receiver_account', fieldclass=recordbased.IntegerFieldZeropadded),
                    dict(length=13, startpos=31, endpos=44, name='customer', default=0, fieldclass=recordbased.IntegerFieldZeropadded),
                    dict(length=2, startpos=44, endpos=46, name='type', choices=['05', '51']),
                    dict(length=3, startpos=46, endpos=49, name='ext', default='000'),
                    dict(length=1, startpos=49, endpos=50, name='reserved', fieldclass=recordbased.FixedField, default=' '),
                    dict(length=11, startpos=50, endpos=61, name='amount_dm', default='0'),
                    dict(length=8, startpos=61, endpos=69, name='sender_bankcode', fieldclass=recordbased.IntegerField),
                    dict(length=10, startpos=69, endpos=79, name='sender_account', fieldclass=recordbased.IntegerFieldZeropadded),
                    dict(length=11, startpos=79, endpos=90, name='amount', fieldclass=recordbased.IntegerFieldZeropadded),
                    dict(length=3, startpos=90, endpos=93, name='reserved', fieldclass=recordbased.FixedField, default=' ' * 3),
                    dict(length=27, startpos=93, endpos=120, name='receiver_name'),
                    dict(length=8, startpos=120, endpos=128, name='reserved', fieldclass=recordbased.FixedField, default=' ' * 8),
                    dict(length=27, startpos=128, endpos=155, name='sender_name'),
                    dict(length=27, startpos=155, endpos=182, name='reason'),
                    dict(length=1, startpos=182, endpos=183, name='currency', default='1'),
                    dict(length=2, startpos=183, endpos=185, name='reserved', fieldclass=recordbased.FixedField, default=' ' * 2),
                    dict(length=2, startpos=185, endpos=187, name='extensions', default=0, fieldclass=recordbased.IntegerFieldZeropadded),
                 ]
                }

Zahlungsaustauschsatz = recordbased.generate_field_datensatz_class(DATENSATZ_C['fields'],
                                                                   name=DATENSATZ_C['name'],
                                                                   length=256,
                                                                   doc=DATENSATZ_C['doc'])

DATENSATZ_E = {
               'doc': 'Der Datensatz E dient der Abstimmung.',
               'name': 'nachsatz',
               'fields': [
                  dict(length=4, startpos=0, endpos=4, name='record_length', default='0128', fieldclass=recordbased.FixedField),
                  dict(length=1, startpos=4, endpos=5, name='record_type', default='E', fieldclass=recordbased.FixedField),
                  dict(length=5, startpos=5, endpos=10, name='reserved', fieldclass=recordbased.FixedField, default=' ' * 5),
                  dict(length=7, startpos=10, endpos=17, name='num_records', fieldclass=recordbased.IntegerFieldZeropadded),
                  dict(length=13, startpos=17, endpos=30, name='reserved', default=0, fieldclass=recordbased.IntegerFieldZeropadded),
                  dict(length=17, startpos=30, endpos=47, name='sum_account', default=0, fieldclass=recordbased.IntegerFieldZeropadded),
                  dict(length=17, startpos=47, endpos=64, name='sum_bankcode', default=0, fieldclass=recordbased.IntegerFieldZeropadded),
                  dict(length=13, startpos=64, endpos=77, name='sum_amount', default=0, fieldclass=recordbased.IntegerFieldZeropadded),
                  dict(length=51, startpos=77, endpos=128, name='reserved', default=' '),
               ]
              }

Nachsatz = recordbased.generate_field_datensatz_class(DATENSATZ_E['fields'], name=DATENSATZ_E['name'], length=128, doc=DATENSATZ_E['doc'])


class DTAUS(object):
    """Datenträgeraustauschverfahren"""
    
    max_transactions = 10 # Gab's da nicht ne Konstante?
    
    def __init__(self, account_info, transaction_type='GK'):
        
        self.a_record = Vorsatz()
        self.a_record.flag = transaction_type
        self.a_record.account = account_info['account']
        self.a_record.bankcode = account_info['bankcode']
        self.a_record.sender_name = encode_text(account_info['sender'])
        self.a_record.file_date = datetime.date.today()
        self.a_record.execution_date = datetime.date.today()
        
        self.transactions = []
        self.e_record = Nachsatz()
    
    def add_transaction(self, transaction, transaction_type='T'):
        """Add a transaction to the DTAUS file"""
        
        if len(self.transactions) > self.max_transactions:
            raise ValueError('Too many transactions for DTAUS file')
        
        c_record = Zahlungsaustauschsatz()
        c_record.sender_name =  self.a_record.sender_name
        c_record.sender_account  = self.a_record.account
        c_record.sender_bankcode = self.a_record.bankcode
        
        c_record.receiver_name = encode_text(transaction['receiver'])
        c_record.receiver_account = transaction['account']
        c_record.receiver_bankcode = transaction['bankcode']
        c_record.amount = transaction['amount']
        
        if transaction_type == 'T': # debit
            c_record.type = '51'
        elif transaction_type == 'D':
            c_record.type = '05'
        else:
            raise ValueError('Unknown type: %s' % transaction_type)
        
        self.transactions.append(c_record)
    
    def serialize(self):
        for transaction in self.transactions:
            self.e_record.sum_account = transaction.receiver_account
            self.e_record.sum_amount = transaction.amount
            self.e_record.sum_bankcode = transaction.receiver_bankcode            
        self.e_record.num_records = len(self.transactions)
        
        return "".join(record.serialize()
                       for record in itertools.chain([self.a_record], self.transactions, [self.e_record]))


def encode_text(text):
    """Encode text according to DIN 66003"""
    return text


if __name__ == "__main__":
    account_info = {'bankcode': '12345678', 'account': '0123456789', 'sender': 'MANFRED MUSTERMANN'}
    dta = DTAUS(account_info, transaction_type='GK')
    transaction = {'bankcode': '30010044', 'account': '4455667788', 'amount': 10, 'receiver': 'FREIER MARKT'}
    dta.add_transaction(transaction, transaction_type='T')
    print '>%s<' % dta.serialize()
    