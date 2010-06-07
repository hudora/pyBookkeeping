#!/usr/bin/env python
# encoding: utf-8
"""
bookkeeping/hudora.py

Created by Maximillian Dornseif on 2010-06-04.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import husoftm.stapelschnittstelle


class HudoraBookkeeping(bookkeeping.abstract.AbstractBookkeeping):
    
    def store_order(self, order):
        """Auftrag in SoftM Stapelschnittstelle schreiben"""
        vorgangsnr = husoftm.stapelschnittstelle.auftrag2softm(order)
        if not husoftm.stapelschnittstelle.address_transmitted(vorgangsnr):
            raise RuntimeError("Fehler bei Vorgang %s: Die Addresse wurde nicht korrekt uebermittelt." % vorgangsnr)

    def check_order(order):
        pass


def main():
    pass


if __name__ == '__main__':
    main()

