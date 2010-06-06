#!/usr/bin/env python
# encoding: utf-8

# from http://python.lickert.net/dtaus/DTAUS.txt
############################################################
######  DTAUS-erzeugen zur Abrechnung
############################################################
#
# Achtung!
# Die Nutzung dieses Programms erfolgt auf eigene Gefahr!
# Ich übernehmen keinerlei Garantie auf Richtigkeit und Funktionstüchtigkeit dieses Programms.
#
# Dieses Programm ist frei - aber auf eigene Gefahr - nutzbar.
# Das Programm wird von einem mir nahestehenden Verein erfolgreich genutzt,
# der Praxistest hat das Programm zumindest bestanden.
#
# Sollte jemand dieses Programm nutzen, würde ich mich über eine Postkarte freuen:
#               Knut Lickert
#               Franziskanergasse 15
#               D-73728 Esslingen
#
#       Eine Anleitung und aktuelle Version findet sich unter
#               http://www.lickert.net/Dev/Python/DTA
#
#
# Hinweis: Zur Erstellung des Begleitblattes ist LaTeX notwendig.
# Informationen zu TeX und LaTeX findet sich unter http://www.dante.de
#
import string
import re
import time
import types
import sys
import os

class dta:
    def __init__(self, filename='DTAUS0.TXT', \
                             datum = time.localtime(time.time()) ):
        """Erstelle eine DTAUS-Datei.
        Typ ist 'LK' (Lastschrift Kunde) oder 'GK' (Gutschrift Kunde)
        Infos zu DTAUS: http://www.infodrom.org/projects/dtaus/dtaus.php3
        Die Methoden müssen in der Reihenfolge:
        - eigeneKonto
        - buchungen
        - begleitblatt
        abgearbeitet werden.
        """
        self.filename = filename
        if type(datum) == type(time):
            self.datum              = datum
        elif type(datum) == type("sting"):      # Datum im Format yyyy-mm-dd
            dat = datum.split('-')
            self.datum = (int(dat[0]), int(dat[1]), int(dat[2]), 0, 0, 0, 0, 0, 0)
            print self.datum
        else:
            self.datum              = time.localtime(time.time())
        self.konto    = {}
        self.sum      = { 'konto': 0L, 'blz': 0L, 'euro': 0L } #Prüfsummen
    def check_typ(self, typ):
        if typ == 'LK':
            self.typText = 'Sammeleinziehungsauftrag'
        elif typ == 'GK':
            self.typText = 'Sammel-Überweisung'
        else:
            raise 'Unbekannte Auftragsart ' + self.mode
    def eigeneKonto(self, konto={} ):
        """Übergabe der eigenen Kontodaten in einem Dictionary mit den Feldern:
        - blz
        - konto
        - bank
        - name
        - zweck [optional]"""
        self.konto = konto
        if not self.konto.has_key('blz'):
            raise 'BLZ fehlt'
        if not self.konto.has_key('konto') or self.konto['konto'] == 0:
            raise 'Kontonummer fehlt'
        if not self.konto.has_key('name'):
            raise 'Name fehlt'
        if not self.konto.has_key('bank'):
            raise 'Name der Bank fehlt'
        if not self.konto.has_key('zweck'):
            self.konto['zweck'] = 'Abbuchung/Gutschrift von %s' % self.konto['name']
    def buchungen(self, typ = 'LK', buchungen=[ {} ]):
        """Für die übergebenen Buchungen wird eine DTA-Datei erstellt.
        Die Buchungen sind eine Liste von Dictionaries mit den folgenen Feldern:
        - vorname
        - nachname
        - kunnr         interne Kundennummer
        - konto
        - blz
        - bank          Name der Bank
        - betrag        positiver Betrag in Euro
        - zweck         (optional) abweichender Text zu Kontodaten"""
        self.file = open(self.filename, 'w')
        self.sum  = { 'konto': 0, 'blz': 0, 'euro': 0 } #Prüfsummen
        self.check_typ(typ)
        self.dataA(typ)    #Lastschriften Kunde/Gutschrift Kunde
        self.buchungen = buchungen      #aufbewahren für Begleitpapier
        eintrag = 0
        for buchung in buchungen:
            if buchung['konto'] == 0:
                raise 'Konto ungültig'
            if buchung['betrag'] < 0:       #nur positive Werte erlaubt
                buchung['betrag'] *= -1
                raise 'negativer Betrag'
            if typ == 'LK':
                self.dataC( buchung, '05000' ) #Lastschrift des Einzugsermächtigungsverfahren
                eintrag += 1
            elif typ == 'GK':
                self.dataC( buchung, '51000' ) #Überweisungs-Gutschrift
                eintrag += 1
            else:
                raise 'unbekannter Buchungs-Typ'
                ignoriert += 1
        self.dataE(len(buchungen))
        self.file.close()
        print "DTAUS '%s' erstellt , %i Einträge (%s)" % (typ, eintrag, self.typText)
    def convert_text(self, zweck):
        "Zeichen umsetzen gemäss DTA-Norm"
        text = string.upper(zweck)
        text = re.sub('Ä', 'AE', text)
        text = re.sub('Ü', 'UE', text)
        text = re.sub('Ö', 'OE', text)
        text = re.sub('ä', 'AE', text)
        text = re.sub('ü', 'UE', text)
        text = re.sub('ö', 'OE', text)
        text = re.sub('ß', 'SS', text)
        return text

    def dataA(self, typ):
        """Erstellen A-Segment der DTAUS-Datei
Aufbau des Segments:
Nr.     Start   Länge          Beschreibung
1       0               4 Zeichen       Länge des Datensatzes, immer 128 Bytes, also immer "0128"
2       4               1 Zeichen       Datensatz-Typ, immer 'A'
3       5               2 Zeichen       Art der Transaktionen
                                        "LB" für Lastschriften Bankseitig
                                        "LK" für Lastschriften Kundenseitig
                                        "GB" für Gutschriften Bankseitig
                                        "GK" für Gutschriften Kundenseitig
4       7               8 Zeichen       Bankleitzahl des Auftraggebers
5       15      8 Zeichen       CST, "00000000", nur belegt, wenn Diskettenabsender Kreditinstitut
6       23      27 Zeichen  Name des Auftraggebers
7       50      6 Zeichen       aktuelles Datum im Format DDMMJJ
8       56      4 Zeichen       CST, "    " (Blanks)
9       60      10 Zeichen  Kontonummer des Auftraggebers
10      70      10 Zeichen  Optionale Referenznummer
11a 80          15 Zeichen  Reserviert, 15 Blanks
11b 95          8 Zeichen       Ausführungsdatum im Format DDMMJJJJ. Nicht jünger als Erstellungsdatum (A7), jedoch höchstens 15 Kalendertage später. Sonst Blanks.
11c 103         24 Zeichen  Reserviert, 24 Blanks
12      127     1 Zeichen       Währungskennzeichen
                                        " " = DM
                                        "1" = Euro
Insgesamt 128 Zeichen
        """
        konto = self.konto
        data = '0128'
        data = data + 'A'
        data = data + typ  #Lastschriften Kunde
        data = data + '%8i' % int(konto['blz']) #BLZ
        data = data + '%08i' % 0                 #belegt, wenn Bank
        data = data + '%-27.27s' % self.convert_text(konto['name'])
        data = data + time.strftime('%d%m%y', self.datum)       #aktuelles Datum im Format DDMMJJ
        data = data + 4*'\x20'  #bankinternes Feld
        data = data + '%010i' % int(konto['konto'])
        data = data + '%010i' % 0 #Referenznummer
        data = data + 15 * '\x20'   #Reserve
        data = data + '%8s' % ' '   #Ausführungsdatum (ja hier 8 Stellen, Erzeugungsdat. hat 6 Stellen)
        data = data + 24 * '\x20'   #Reserve
        data = data + '1'   #Kennzeichen Euro
        if len(data) <> 128: print 'DTAUS: Längenfehler A'
        self.file.write(data + '\n')
    def dataC(self, buchung, zahlungsart):
        """Erstellen C-Segmente (Buchungen mit Texten) der DTAUS-Datei
Aufbau:
Nr.     St      Länge          Beschreibung
1       0       4 Zeichen       Länge des Datensatzes, 187 + x * 29 (x..Anzahl Erweiterungsteile)
2       4       1 Zeichen       Datensatz-Typ, immer 'C'
3       5       8 Zeichen       Bankleitzahl des Auftraggebers (optional)
4       13  8 Zeichen   Bankleitzahl des Kunden
5       21  10 Zeichen  Kontonummer des Kunden
6       31  13 Zeichen  Verschiedenes
                1. Zeichen: "0"
                2. - 12. Zeichen: interne Kundennummer oder Nullen
                13. Zeichen: "0"
                Die interne Nummer wird vom erstbeauftragten Institut zum endbegünstigten Institut weitergeleitet. Die Weitergabe der internenen Nummer an den Überweisungsempfänger ist der Zahlstelle freigestellt.
7       44  5 Zeichen  Art der Transaktion (7a: 2 Zeichen, 7b: 3 Zeichen)
                "04000" Lastschrift des Abbuchungsauftragsverfahren
                "05000" Lastschrift des Einzugsermächtigungsverfahren
                "05005" Lastschrift aus Verfügung im elektronischen Cash-System
                "05006" Wie 05005 mit ausländischen Karten
                "51000" Überweisungs-Gutschrift
                "53000" Überweisung Lohn/Gehalt/Rente
                "5400J" Vermögenswirksame Leistung (VL) ohne Sparzulage
                "5400J" Vermögenswirksame Leistung (VL) mit Sparzulage
                "56000" Überweisung öffentlicher Kassen
                Die im Textschlüssel mit J bezeichnete Stelle, wird bei Übernahme in eine Zahlung automatisch mit der jeweils aktuellen Jahresendziffer (7, wenn 97) ersetzt.
8       49  1 Zeichen  Reserviert, " " (Blank)
9       50  11 Zeichen  Betrag
10      61  8 Zeichen  Bankleitzahl des Auftraggebers
11      69  10 Zeichen  Kontonummer des Auftraggebers
12      79  11 Zeichen  Betrag in Euro einschließlich Nachkommastellen, nur belegt, wenn Euro als Währung angegeben wurde (A12, C17a), sonst Nullen
13      90  3 Zeichen  Reserviert, 3 Blanks
14a 93  27 Zeichen  Name des Kunden
14b 120  8 Zeichen  Reserviert, 8 Blanks
Insgesamt 128 Zeichen

15 128  27 Zeichen  Name des Auftraggebers
16 155  27 Zeichen  Verwendungszweck
17a 182  1 Zeichen  Währungskennzeichen
                " " = DM
                "1" = Euro
17b 183  2 Zeichen  Reserviert, 2 Blanks
18 185  2 Zeichen  Anzahl der Erweiterungsdatensätze, "00" bis "15"
19 187  2 Zeichen  Typ (1. Erweiterungsdatensatz)
                "01" Name des Kunden
                "02" Verwendungszweck
                "03" Name des Auftraggebers
20 189  27 Zeichen  Beschreibung gemäß Typ
21 216  2 Zeichen  wie C19, oder Blanks (2. Erweiterungsdatensatz)
22 218  27 Zeichen  wie C20, oder Blanks
23 245  11 Zeichen  11 Blanks
Insgesamt 256 Zeichen, kann wiederholt werden (max 3 mal)
        """
        #Erweiterungsteile für lange Namen...
        erweiterungen = []  #('xx', 'inhalt') xx: 01=Name 02=Verwendung 03=Name
        # 1. Satzabschnitt
        #data1 = '%4i' % ?? #Satzlänge kommt später
        data1 = 'C'
        data1 = data1 + '%08i' % 0  #freigestellt
        if type(buchung['blz']) == types.IntType:
            data1 = data1 + '%08i' % buchung['blz']
        else:
            print 'DTAUS: überspringe %s (BLZ)' % buchung['nachname']
            return 4
        if type(buchung['kto']) == types.LongType:
            data1 = data1 + '%010i' % buchung['kto']
        else:
            print 'DTAUS: überspringe %s (Konto)' % buchung['nachname']
            return 4
        data1 = data1 + '0%011i0' % int(buchung.get('kunnr', 0))   #interne Kundennummer
        data1 = data1 + zahlungsart
        data1 = data1 + '0' #bankintern
        data1 = data1 + 11 * '0'    #Reserve
        data1 = data1 + '%08i' % int(self.konto['blz'])
        data1 = data1 + '%010i' % int(self.konto['konto'])
        data1 = data1 + '%011i' % int(buchung['betrag'] * 100 ) #Betrag in Euroeinschl. Nachkomme
        data1 = data1 + 3 * '\x20'
        #Name unseren Mitgliedes = Begünstigte/Zahlungspflichtiger
        mitglied = self.convert_text(buchung['kontoinhaber'])
        if mitglied == "":
            mitglied = self.convert_text(buchung['nachname'] + ' ' + buchung['vorname'])
        data1 = data1 + '%27.27s' % mitglied
        if len(mitglied) > 27:
            erweiterungen.append( ('01', mitglied[27:]) )
        data1 = data1 + 8 * '\x20'
        self.sum['konto']   = self.sum['konto'] + buchung['kto']
        self.sum['blz']     = self.sum['blz'] + buchung['blz']
        self.sum['euro']    = self.sum['euro'] + int(buchung['betrag'] * 100 )

        # 2. Satzabschnitt
        wir = self.convert_text(self.konto['name'])
        data2 = '%-27.27s' % wir
        if len(wir) > 27:
            erweiterungen.append( ('03', wir[27:]) )
        #Zweck kommt aus Einzelbuchung, alternativ aus Konto
        if buchung.has_key('zweck'):
            zweck = buchung['zweck']
        else:
            zweck = self.konto['zweck']
        zweck = self.convert_text(zweck)
        data2 = data2 + '%-27.27s' % zweck
        zweck = zweck[27:]
        while len(zweck) > 0 and len(erweiterungen) < 13:
            erweiterungen.append( ('02', zweck[:27]) )
            zweck = zweck[27:]
        data2 = data2 + '1'     #Währungskennzeichen
        data2 = data2 + 2 * '\x20'
        # Gesamte Satzlänge ermitteln ( data1(+4) + data2 + Erweiterungen )
        data1 = '%04i' % (len(data1)+4 + len(data2)+2 + len(erweiterungen) * 29 ) + data1
        if len(data1) <> 128: print 'DTAUS: Längenfehler C/1 %i, %s' % (len(data1), buchung['mnr'])
        self.file.write(data1 + '\n')
        #Anzahl Erweiterungen anfügen
        data2 = data2 + '%02i' % len(erweiterungen)  #Anzahl Erweiterungsteile
        #Die ersten zwei Erweiterungen gehen in data2,
        #Satz 3/4/5 à 4 Erweiterungen  -> max. 14 Erweiterungen (ich ignoriere möglichen Satz 6)
        erweiterungen = erweiterungen + \
                                        (14 - len(erweiterungen)) * [('00', "")]
        #print len(erweiterungen), erweiterungen
        for erw in erweiterungen[:2]:
            data2 = data2 + '%2.2s%27.27s' % erw
        data2 = data2 + 11 * '\x20'
        if len(data2) <> 128: print 'DTAUS: Längenfehler C/2', len(data2)
        self.file.write(data2 + '\n')
        # fixme : data4...
        data3 = ''
        for erw in erweiterungen[2:6]:
            data3 = data3 + '%2.2s%27.27s' % erw
        data3 = data3 + 12 * '\x20'
        if data3[:2] <> '00':
            if len(data3) <> 128: print 'DTAUS: Längenfehler C/3'
            self.file.write(data3 + '\n')

    def dataE(self, anzBuchungen):
        """Erstellen E-Segment (Prüfsummen) der DTAUS-Datei
Aufbau:
Nr.     Start Länge    Beschreibung
1       0       4 Zeichen       Länge des Datensatzes, immer 128 Bytes, also immer "0128"
2       4       1 Zeichen       Datensatz-Typ, immer 'E'
3       5       5 Zeichen       "     " (Blanks)
4       10  7 Zeichen   Anzahl der Datensätze vom Typ C
5       17  13 Zeichen  Kontrollsumme Beträge
6       30  17 Zeichen  Kontrollsumme Kontonummern
7       47  17 Zeichen  Kontrollsumme Bankleitzahlen
8       64  13 Zeichen  Kontrollsumme Euro, nur belegt, wenn Euro als Währung angegeben wurde (A12, C17a)
9       77  51 Zeichen  51 Blanks
Insgesamt 128 Zeichen
        """
        data = '0128'
        data = data + 'E'
        data = data + 5 * '\x20'
        data = data + '%07i' % anzBuchungen
        data = data + 13 * '0'  #Reserve
        data = data + '%017i' % self.sum['konto']
        data = data + '%017i' % self.sum['blz']
        data = data + '%013i' % self.sum['euro']
        data = data + 51 * '\x20'   #Abgrenzung Datensatz
        if len(data) <> 128: print 'DTAUS: Längenfehler E'
        self.file.write(data + '\n')

    def begleitblatt(self, filename = 'Begleitblatt' ):
        """
Jede dem Geldinstitut gelieferte Diskette muß einen
Begleitzettel mit folgenden Mindestangaben enthalten.
Bei mehreren Disketten ist für jede Diskette ein
Begleitzettel auszuschreiben.

-Begleitzettel
-Belegloser Datenträgeraustausch
-Sammel-Überweisung-/-einziehungsauftrag
-Vol-Nummer der Diskette
-Erstellungsdatum
-Anzahl der Datensätze C (Stückzahl)
-Summe DM der Datensätze C
-Kontrollsumme der Kontonummern der
-Überweisungsempfänger/Zahlungspflichtigen
-Kontrollsumme der Bankleitzahlen der endbegünstigten
-Kreditinstitute/Zahlungsstellen
-Bankleitzahl/Kontonummer des Absenders
-Name, Bankleitzahl/Kontonummer des Empfängers
-Ort, Datum
-Firma, Unterschrift

Sie haben die Pflicht, die Disketten zusätzlich
durch Klebezettel mit folgenden Angaben zu kennzeichnen:
-Name und Bankleitzahll/Kontonummer des Diskettenabsenders.
-Diskettennummer (VOL-Nummer).
-Dateiname: DTAUS0.TXT 5.25 -und 3.5 Diskette.
        """
        blatt = open( filename + '.txt', 'w')
        blatt.write('Begleitzettel, Belegloser Datenträgeraustausch\n')
        blatt.write(self.typText + '\n')
##-Vol-Nummer der Diskette
        blatt.write('Erstellungsdatum:\n\t%s\n' % time.strftime('%d.%m.%y',time.localtime(time.time())) )
        blatt.write('Überweisungsempfänger/Zahlungspflichtigen\n\t%s\n' % self.konto['name'])
        blatt.write('Kontonummer des Absenders:\n\t%s\n' % self.konto['konto'])
        blatt.write('Bankleitzahl des Absenders:\n\t%s\n' % self.konto['blz'])
        blatt.write('Bank:\n\t%s\n' % self.konto['bank'])
        blatt.write('Anzahl der Datensätze C (Stückzahl):\n\t%i\n' % len(self.buchungen))
        summe = float(self.sum['euro']) / 100
        blatt.write('Summe Euro der Datensätze C:\n\t%.2f\n' % summe  )
        blatt.write('Kontrollsumme der Kontonummern:\n\t%017i\n' % self.sum['konto'])
        blatt.write('Kontrollsumme der Bankleitzahlen der Endbegünstigten:\n\t%017i\n' % self.sum['blz'])
##-Ort, Datum
##-Firma, Unterschrift
        blatt.write('\n\nBuchungsübersicht\n')
        for buchung in self.buchungen:
            if buchung['betrag_float'] = float(buchung['betrag'])
            blatt.write('\t%(betrag_float)6.2f Euro\t%(konto)s\t%(blz)s\t%(nachname)s %(vorname)s\n'
                                    % buchung)
        blatt.close()
    def begleitblatt_tex(self, file):
        """
Jede dem Geldinstitut gelieferte Diskette muß einen
Begleitzettel mit folgenden Mindestangaben enthalten.
Bei mehreren Disketten ist für jede Diskette ein
Begleitzettel auszuschreiben.

-Begleitzettel
-Belegloser Datenträgeraustausch
-Sammel-Überweisung-/-einziehungsauftrag
-Vol-Nummer der Diskette
-Erstellungsdatum
-Anzahl der Datensätze C (Stückzahl)
-Summe DM der Datensätze C
-Kontrollsumme der Kontonummern der
-Überweisungsempfänger/Zahlungspflichtigen
-Kontrollsumme der Bankleitzahlen der endbegünstigten
-Kreditinstitute/Zahlungsstellen
-Bankleitzahl/Kontonummer des Absenders
-Name, Bankleitzahl/Kontonummer des Empfängers
-Ort, Datum
-Firma, Unterschrift

Sie haben die Pflicht, die Disketten zusätzlich
durch Klebezettel mit folgenden Angaben zu kennzeichnen:
-Name und Bankleitzahll/Kontonummer des Diskettenabsenders.
-Diskettennummer (VOL-Nummer).
-Dateiname: DTAUS0.TXT 5.25 -und 3.5 Diskette.
        """
        self.konto['time'] = time.strftime('%d.%m.%y',time.localtime(time.time()))
        self.konto['typText'] = self.typText
        file.write(r"""
\begin{letter}{ %(bank)s}
\title{Begleitzettel, Belegloser Datenträgeraustausch %(typText)s}
\opening{~}
\begin{description}
\item[Erstellungsdatum:]
%(time)s
\item[Überweisungsempfänger/Zahlungspflichtigen]
%(name)s
\item[Kontonummer des Absenders:]
%(konto)s
\item[Bankleitzahl des Absenders:]
%(blz)s
\item[Bank:]
%(bank)s
\item[Zweck:]
%(zweck)s"""    % self.konto )
        self.sum['anzbuch'] = len(self.buchungen)
        self.sum['summe'] = float(self.sum['euro']) / 100
        file.write(r"""
\item[Anzahl der Datensätze C (Stückzahl):]
%(anzbuch)i
\item[Summe Euro der Datensätze C:]
%(summe).2f
\item[Kontrollsumme der Kontonummern:]
%(konto)017i
\item[Kontrollsumme der Bankleitzahlen der Endbegünstigten:]
%(blz)017i
\end{description}
\closing{~}
\end{letter}
""" % self.sum )
##-Ort, Datum
##-Firma, Unterschrift
        file.write(r"""
\newpage
\nexthead{}\begin{longtable}{p{6cm}llr}
\multicolumn{4}{c}{\textbf{Buchungsübersicht %s}}\\
Name & Konto & BLZ & Betrag\\\hline\endhead
\multicolumn{4}{r}{Fortsetzung nächste Seite}\endfoot
""" % self.typText )
        #Sort nach?
        for buchung in self.buchungen:
            file.write('\hyperlink{MNr:%(kunnr)s}{%(nachname)s %(vorname)s} & \t \t%(kto)s\t& %(blz)s\t & \\euros{%(betrag)6.2f}\\\\\n'
                                    % buchung)
        file.write('\hline\nSumme & \t \t%(konto)s\t& %(blz)s\t & \\euros{%(summe)6.2f}\\\\\n'
                                        % self.sum)
        file.write("\\end{longtable}\n")
    def diskette(self, text=None):
        if text == None:
            text = self.typText
        answer = raw_input('Diskette in A: einlegen (%s)' % text )
        os.system('copy %s a:\DTAUS0.TXT' % self.filename)

def tex_start(file, TeXclass='scrlttr2'):
    file.write( \
r"""\documentclass[10pt,german]{%s}
%%\usepackage{booktabs}%%leider nicht mit longtable
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{units}
\usepackage{times}
\usepackage{isodate}
\usepackage[right,eurosym]{eurofont}

\newlength{\betragsbreite}%%Breite des Endsummen (Fahrten/EP)
\setlength{\betragsbreite}{15mm}

%%\nexthead{\fromname -\thepage-}%%scrlettr
\nexthead{\usekomavar{fromname} -\thepage-}%%scrlettr2

\begin{document}
""" % TeXclass )

if __name__ == '__main__':
    """dtaus.py -kKonto -bBuchungen
    Konto:\tDatei mit eigenem Konten
    Buchungen:\tDatei mit Buchungen,
    """
    if len(os.sys.argv) <> 4:
        raise 'DTAUS.py Kontodaten Buchungen Zieldatei'
    filename = os.sys.argv[3]
    DTA = dta(filename + '.dta')
    #lese Daten zum eigene Konto
    konto = open(os.sys.argv[1])
    for line in konto.readlines():
        [was, inhalt] = string.split(line, ':')
        DTA.konto[string.lower(was)] = string.strip(inhalt)
        print was, inhalt
    konto.close()
    DTA.eigeneKonto( DTA.konto )
    #Lese Buchungen
    buchungen = []
    file  = open(os.sys.argv[2])
    for line in file.readlines():
        if line[0] == '#':      #Kommentar
            continue
        value = string.split(string.strip(line), ':')
        buchung = {}
        buchung['nachname'] = value[0]
        buchung['vorname'] = value[1]
        buchung['kontoinhaber'] = value[1] + ' ' + value[0]
        if value[2] <> '':
            buchung['kunnr'] = value[2]
        else:
            buchung['kunnr'] = 0    #default
        buchung['kto'] = long(value[3])
        buchung['blz'] = int(value[4])
        buchung['bank'] = value[5]
        buchung['betrag'] = float(value[6])             #       positiver Betrag in Euro
        if len(value) > 7 and value[7] <> '':
            buchung['zweck'] = value[7]     #(optional) abweichender Text zu Kontodaten
        buchungen.append(buchung)
    file.close()
    DTA.buchungen(DTA.konto['typ'], buchungen)
    #Begleitblatt ASCII
    DTA.begleitblatt( filename )
    # Begleitblatt als TeX-File
    tex = open(filename + '.tex', 'w')
    print DTA.konto.get('texclass', 'scrxxxx')
    print DTA.konto
    tex_start(tex, DTA.konto.get('texclass', 'scrlettr'))
    DTA.begleitblatt_tex(tex)
    tex.write('\\end{document}')
    tex.close
