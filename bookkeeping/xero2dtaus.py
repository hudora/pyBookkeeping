#!/usr/bin/env python
# encoding: utf-8
"""
xero2dtaus.py

Created by Maximillian Dornseif on 2010-06-05.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import formats.DTAUS 

data = """563.65,6828040,34040049 Commerzbank Remscheid,,Notariat Zahn
533.12,770637700,34030049 Commerzbank Remscheid,,HUDORA GmbH
"""

dta = formats.DTAUS.dta('test.dta')
dta.eigeneKonto(konto=dict(blz='36020186', konto='340577043', bank='HVB Essen', name='Cyberlogi GmbH i.G.'))
dta.buchungen('GK', buchungen=[dict(vorname='HUDORA GmbH', nachname='', kundennr='', konto='770637700', blz='34030049', bank='Commerzbank Remscheid',betrag='533.12')])
dta.begleitblatt('begleitblatt')

