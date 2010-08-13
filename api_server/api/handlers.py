#!/usr/bin/env python
# encoding: utf-8
""" handlers.py --- Describe Tool here äöü---
"""

# handlers.py
# Created by Christoph Borgolte on 12-08-2010 for HUDORA.
# Copyright (c) 2010 HUDORA. All rights reserved.


from django.conf import settings
from piston.handler import BaseHandler
import piston.utils
from django import forms



class SimpleInvoiceForm(forms.Form):
    """
    Hilfsklasse - Form zur Validierung der übergebenen Request Parameter
    """

    guid = forms.CharField()
    name1 = forms.CharField()
    name2 = forms.CharField()
    strasse = forms.CharField()
    land = forms.CharField()
    plz = forms.CharField()
    ort = forms.CharField()
    infotext_kunde = forms.CharField(required=False)
    leistungszeitpunkt = forms.DateField()
    versandkosten = forms.IntegerField()
    zahlungsziel = forms.IntegerField(required=False)
    orderlines = forms.CharField() # ?


class InvoiceHandler(BaseHandler):
    """
    API Handler zur Verwaltung von Artikelpreisen
    """

    allowed_methods = ('GET', 'POST')

    def read(self, request, company=None):
        company = company or request.GET['company']
        kundennr = request.GET.get('kundennr')
        rechnungsnr = request.GET.get('rechnungsnr')
        days = request.GET.get('days')

        # so könnte da aussehen:
        #if 'hudora' == company.lower():
        #    invoices = bookkeeping.hudora.list_invoices(kundennr, days=None)
        #elif 'cyberlogi' == company.lower():
        #    parameters = ['Type="ACCPAY"', 'Contact.Name="%s"' % company]
        #    invoices = bookkeeping.cyberlogi.list_invoices(parameters=None, xpath='Invoices/Invoice/InvoiceID')

        return {'invoices': [{'rechnungsnr': '514444444'}]}


    @piston.utils.validate(SimpleInvoiceForm, 'POST')
    def create(self, request, company=None):

        if request.content_type:
            invoice = dict(request.data)

        print invoice
        form = SimpleInvoiceForm(invoice)
        company = company or request.POST['company']
        return company, invoice
