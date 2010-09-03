#!/usr/bin/env python
# encoding: utf-8
"""
recordbased.py - generation of record based dataformats.

Created by Maximillian Dornseif on 2007-05-11.
Copyright (c) 2007 HUDORA GmbH. BSD licensed.

This is a toolkit to generate and parse fixed record based files. You define the structure of a record by
a list of dictionaries where each dictionary describes a field in the record. This list of dicts is then fed
to generate_field_datensatz_class() which generates a class capable of generating and parsing records of the
type described.

For each field you have to define length of the field, start position, end position and name. Positions are
given in python slice notation which means the field is [startpos:endpos[ - the endpos is the first byte NOT
belonging to the field. Name is used to define the attribute name

The optional parameter 'fieldclass' defines the class of the Field. Check the module contents for the
different *Field classes. All other parameters, e.g. 'precision' are passed to the Fields __init__ method.

With the genrated class you can access all fields by attributes with the names given in their respective
'name' parameters. The serialize() method can convert the record with all it's fields to a stream of bytes.
The parse() method is the opposide of serialize - it reads a stream of bytes and sets the values of the
attributes.

>>> felder = [dict(length=4,  startpos=0,  endpos=4,  name='position'),
...           dict(length=15, startpos=19, endpos=34, name='menge', fieldclass=DecimalField, precision=3),
...           dict(length=15, startpos=4,  endpos=19, name='artikelnummer', fieldclass=RightAdjustedField),
...           dict(length=8,  startpos=34, endpos=42, name='date', fieldclass=DateField,
...                default=datetime.datetime(2006, 7, 8))]
>>> klass = generate_field_datensatz_class(felder, name='test12', length=42)
>>> i = klass()
>>> i.position, i.artikelnummer, i.menge = 9999, '14650/42z', 1234
>>> i.date = datetime.datetime(2006, 7, 8)
>>> i.serialize()
'9999      14650/42z       1234.00020060708'

>>> i = klass()
>>> i.parse('9999      14650/42z       1234.00020060708')
>>> i.position, i.artikelnummer, int(i.menge)
('9999', '14650/42z', 1234)

See docstrings for further explanation.

"""

from pkg_resources import require
require("huTools")

import datetime
import time
from decimal import Decimal
from huTools import checksumming


class RecordBasedProtocolException(Exception):
    """All Exceptions thrown by this module are descendants of this."""
    pass


class InvalidFieldDefinition(RecordBasedProtocolException):
    """Raised when the definition of a field is erroneous."""
    pass


class FieldTooLong(RecordBasedProtocolException, ValueError):
    """Raised when a value is to long to fit in the field."""
    pass


class FieldNoValidChoice(RecordBasedProtocolException):
    """Raised when the value in a field is not listed in the choices array."""
    pass


class FieldImmutable(RecordBasedProtocolException):
    """Raised when attempting tio change the value of a immutable field."""
    pass


class ParseException(RecordBasedProtocolException):
    """Base class for all exceptions raised during parsing."""
    pass


class SizeMismatch(ParseException):
    """Raised during parsing when the data subjected to parsing has not the correct number of bytes."""
    pass


class InvalidData(ParseException, ValueError):
    """Raised during parsing for general parsing errors."""
    pass


class FieldDescriptor(object):
    """Implements descriptor protocol access for Fields."""

    def __init__(self, name, length=5, default='', choices=tuple(), doc=None, **kwargs):
        self.name = name
        self.doc = doc
        self.value = None

    def __str__(self):
        return str(self.value)

    # methods used for the descriptor protocol. See http://docs.python.org/ref/descriptors.html

    def __get__(self, obj, objtype):
        return getattr(obj, self.name + '_field').value

    def __set__(self, obj, value):
        return getattr(obj, self.name + '_field').set(value)


class Field(object):
    """Base Class for (string) fields in fixed length records.

    The parameter 'name' is used for informative purposes.
    'length' demines the length of the field. Shorter velues are padded to length,
    longer values result in an Exception beeing raised.
    'default' sets the default falue for this field. If default == '' this denotes an empty field.
    If default is a callable it is called to get the default value.
    If 'choices' is used, the system enforces that only values present in 'choices' are allowed.
    Attempts to set an other value will result un an Exception.
    """

    def __init__(self, name, length=5, default='', choices=tuple(), doc=None):
        self.name = name
        self.length = length
        self.default = default
        self.value = default
        self.choices = [self.format(x) for x in choices]
        self.doc = doc

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str("<%s: %r>" % (self.name, self.value))

    def get(self):
        """Returns the actual value associated with the field calling callables where needed."""
        return self._resolve(self.value)

    def set(self, value):
        """Validate data for Field and then set the Fields value to it."""
        if self.is_valid(self.format(value)):
            self.value = value
        return self.format(value)

    def formated(self):
        """Return a formatted version of the Field suitable for writing directly to the record datastream."""
        return self.format(self.value)

    def _resolve(self, value):
        """Get the value of value by calling callables or directly returning values =:-)"""
        if callable(value):
            return value()
        return value

    def format(self, value):
        """Formats the data according to the field's length, etc.  - meant to be overwirtten by subclasses."""
        return "%-*s" % (self.length, self._resolve(value))

    def is_valid(self, value):
        """Returns true if value is valid date for Field else raises an Exception."""
        # self.format() should be applied to value before calling is_value()
        if len(value) > self.length:
            raise FieldTooLong("%s has length %d but you trying to assign to it %r (len %d)" % (self.name,
                               self.length, value, len(value)))
        if self.choices and value not in self.choices:
            raise FieldNoValidChoice("%s has limited choices and %r is not one of them" % (self.name, value))
        return True

    def get_parsed(self, data):
        """Do the actual parsing - meant to be overwirtten by subclasses."""
        return data.rstrip()

    def parse(self, data):
        """Check if the data can be parsed and then actually initiate parsing."""
        if len(data) != self.length:
            raise SizeMismatch("%s has length %d but you trying to parse %r (len %d)" % (self.name,
                                self.length, data, len(data)))
        if data.strip() == '': # empty field
            self.set(self._resolve(self.default))
        else:
            self.set(self.get_parsed(data))


class FixedField(Field):
    """Class for immutable fields in fixed length records."""

    def __init__(self, *args, **kwargs):
        super(FixedField, self).__init__(*args, **kwargs)
        if not self.default:
            raise InvalidFieldDefinition('%r: no default value given' % self)
        if len(self._resolve(self.default)) != self.length:
            raise InvalidFieldDefinition('%r: default value %r does not corrospondent to field length (%d)' \
                                           % (self, self._resolve(self.default), self.length))

    def set(self, value):
        """Ensure FixedFields can't be changed after creation."""
        if str(value).strip() != str(self._resolve(self.default)).strip():
            raise FieldImmutable("tried to set %r to %r - but field is immutable."
                    % (str(self.__dict__), value))


class RightAdjustedField(Field):
    """Right adjusted String Field."""

    def format(self, value):
        """Formats the data according to the field's length, etc."""
        return ("%%%ds" % self.length) % self._resolve(value)

    def get_parsed(self, data):
        """Do the actual parsing."""
        return data.lstrip()


class EanField(Field):
    """Field for storing EANs and ILNs (validates checkdigit)."""
    # BTW: we might want to enforce a field with of 13 bytes but actually there are MANY protocols specifying
    # the fieldsize for EAN-13 to 17 or so bytes.

    def get_parsed(self, data):
        """Do the actual parsing."""
        return data.strip()

    def is_valid(self, value):
        """Returns true if value is valid date for Field else raises an Exception."""
        value = value.strip()
        if value:
            if not len(value) in [8, 13, 14]:
                raise SizeMismatch("%s (EAN) has length 8, 13 or 14 but you trying to parse %r (len %d)" % (
                                    self.name, value, len(value)))
            if checksumming.ean_digit(value[:-1]) != value[-1]:
                raise InvalidData("%s: %r no valid checkdigit (%s)" % (self.name, value,
                                                                        checksumming.ean_digit(value[:-1])))
        return super(EanField, self).is_valid(value)


class IntegerField(Field):
    """Right adjusted Integer Field."""

    def format(self, value):
        """Formats the data according to the field's length, etc."""
        if isinstance(value, int):
            return ("%%%dd" % self.length) % self._resolve(value)
        else:
            return ("%%%ds" % self.length) % self._resolve(value)

    def get_parsed(self, data):
        """Do the actual parsing."""
        try:
            return int(data.strip())
        except ValueError, msg:
            raise InvalidData(msg)


class IntegerFieldZeropadded(IntegerField):
    """Right adjusted zero padded Integer Field."""

    def format(self, value):
        """Formats the data according to the field's length, etc."""
        
        if isinstance(value, (int, long)):
            return "%0*d" % (self.length, self._resolve(value))
        else:
            # return "%*s" % (self.length, self._resolve(value))
            return str(self._resolve(value)).rjust(self.length, '0')


class DecimalField(Field):
    """Field to encode an fixed precision integer.

    This takes an additional parameter to the parameters accepted by Field(), 'precision'.
    'precision' defines the number of digits following the decimal point."""

    def __init__(self, name, length=15, *args, **kwargs):
        self.precision = None
        if 'precision' in kwargs:
            self.precision = kwargs['precision']
            del(kwargs['precision'])
        super(DecimalField, self).__init__(name, length, *args, **kwargs)
        if self.precision and (self.precision + 2 > self.length):
            raise InvalidFieldDefinition("%r: too much precision (%d) for too little length (%d)" %
                    (self, self.precision, self.length, ))

        # need a precision for the formatstring
        precision = 0
        if self.precision:
            precision = self.precision
        self.formatstring = "%%#%d.%df" % (self.length, precision, )

    def _reducetofit(self, value):
        '''When converting a number which has length=self.length e.g. 9000000000.00000 w/ length=15 and precision=5 we get

        '9000000000.00000' which has a length of 16. Reduce this string here until it fits.
         Make sure, it still the same decimal value.'''
        while len(value) > self.length:
            newval = value[:-1]
            if Decimal(newval) != Decimal(value):
                print("Field %r has maxlength of %d but after formating wrote %r to it." %
                        (self, self.length, value))
                raise FieldTooLong("Field %r has maxlength of %d but after formating wrote %r to it." %
                        (self, self.length, value))
            value = newval
        return value

    def format(self, value):
        """Formats the data according to the field's length, etc."""

        value = self._resolve(value)
        if not value:
            return ("%%%ds" % self.length) % ' '
        ret = self.formatstring % Decimal(value)
        ret = self._reducetofit(ret)
        return ret

    def parse(self, data):
        """Check if the data can be parsed and actually parse it."""

        data = data.strip()
        dummy, frac = data, ''
        if '.' in data and self.precision:
            dummy, frac = data.split('.')
            if len(frac) > self.precision:
                raise InvalidData('Field %r has a precision of %d but %r has %d fractional digits' %
                                   (self, self.precision, data, len(frac)))
        if data:
            self.set(Decimal(data.strip()))


class DecimalFieldNoDot(DecimalField):
    """Field representing a decimal value without a dot.

    E.G. 12.32 -> '1232'.
    """

    def __init__(self, name, length=15, *args, **kwargs):
        if 'precision' not in kwargs:
            raise InvalidFieldDefinition("%r: precision not set" % (self))
        super(DecimalFieldNoDot, self).__init__(name, length, *args, **kwargs)

    def format(self, value):
        """Formats the data according to the field's length, etc."""

        if not self.precision:
            raise InvalidFieldDefinition("%r: no precision defined" % (self))
        ret = super(DecimalFieldNoDot, self).format(value).replace('.', '')
        return ("%%%ds" % self.length) % ret.replace('.', '')

    def parse(self, data):
        """Check if the data can be parsed and actually parse it."""

        # insert decimal point
        data = "%s.%s" % (data[:-(self.precision)], data[-(self.precision):])

        if data:
            self.set(Decimal(data.strip()))


class DecimalFieldNoDotZeropadded(DecimalFieldNoDot):
    """Field representing a decimal value without a dot."""

    def format(self, value):
        """Formats the data according to the field's length, etc."""
        return super(DecimalFieldNoDotZeropadded, self).format(value).replace(' ', '0')


class DecimalFieldNoDotSigned(DecimalFieldNoDotZeropadded):
    """Field representing a decimal value without a dot and Sinage in the last Byte.

    E.G. 12.32 -> '1232+'.
    """

    def format(self, value):
        """Formats the data according to the field's length, etc."""

        ret = super(DecimalFieldNoDotZeropadded, self).format(abs(value))
        # relace souporflous space at the beginning due to lenght also contianing the sign at the end
        # which the superclass doesn't know about
        ret = ret[1:].replace(' ', '0')
        if value < 0:
            return ret + '-'
        else:
            return ret + '+'

    def parse(self, data):
        """Check if the data can be parsed and actually parse it."""

        # insert decimal point
        # print data, self.name, self.length
        sign = data[-1]
        data = "%s.%s" % (data[:-(self.precision+1)], data[-(self.precision+1):-1])

        if data:
            if sign == '-':
                self.set(Decimal(data.strip()) * -1)
            else:
                self.set(Decimal(data.strip()))


class DateField(Field):
    """Field encoding a date as YYYYMMDD.

    Default value should be a datetime dbject or an callable returning a datetime object.
    """

    def __init__(self, name, length, formatstr='%Y%m%d', **kwargs):
        self.formatstr = formatstr
        super(DateField, self).__init__(name, length, **kwargs)

    def __str__(self):
        if hasattr(self.value, 'strftime'):
            return self.value.strftime('%Y-%m-%d')
        return str(self.value)

    def format(self, value):
        """Formats the data according to the field's length, etc."""
        if hasattr(self._resolve(value), 'strftime'):
            ret = self._resolve(value).strftime(self.formatstr)
        else:
            ret = "%*s" % (self.length, self._resolve(value))
        if len(ret) != self.length:
            raise FieldTooLong("Field %r has maxlength of %d but you tried to write %r to it" %
                                (self, self.length, self._resolve(value)))
        return ret

    def get_parsed(self, data):
        """Do the actual parsing."""

        if data in ['00000000', '99999999']:
            # This would result in an invalid date, return dummy date
            return self._resolve(self.default)
        try:
            return datetime.datetime(data, self.formatstr)
        except ValueError, msg:
            raise InvalidData("%r - %s" % (data, msg))


class DateFieldReverse(DateField):
    """Field encoding a date as DDMMYYYY."""
    formatstr = '%d%m%Y'


class TimeField(Field):
    """Field encoding time as HHMM."""

    def __init__(self, name, length=4, **kwargs):
        if length != 4:
            raise InvalidFieldDefinition("TimeField defined with length != 4 (%s)" % (length, ))
        super(TimeField, self).__init__(name, length, **kwargs)

    def __str__(self):
        if hasattr(self.value, 'strftime'):
            return self.value.strftime('%H:%M')
        return str(self.value)

    def format(self, value):
        """Formats the data according to the field's length, etc."""
        if hasattr(self._resolve(value), 'strftime'):
            ret = self._resolve(value).strftime('%H%M')
        else:
            ret = ("%%%ds" % self.length) % self._resolve(value)
        if len(ret) != self.length:
            raise FieldTooLong("Field %r has maxlength of %d but you tried to write %r to it." % (
                                self, self.length, self._resolve(value)))
        return ret

    def get_parsed(self, data):
        """Do the actual parsing."""
        try:
            return datetime.datetime(*time.strptime(data, "%H%M")[0:6]).time()
        except ValueError, msg:
            raise InvalidData("%r - %s" % (data, msg))


class _FieldDescriptorClass(object):
    """Routes arround descriptors for name+'_field' attributes in generate_field_datensatz_class()."""

    def __init__(self, fieldinstance):
        self.fieldinstance = fieldinstance

    # methods used for the descriptor protocol. See http://docs.python.org/ref/descriptors.html

    def __get__(self, obj, objtype):
        return self.fieldinstance


def _get_length(felder):
    """Check that fields in the list 'felder' do not overlap. And returns the minimum length of a record."""
    posarray = []
    for feld in felder:
        if feld['endpos']-feld['startpos'] != feld['length']:
            raise InvalidFieldDefinition(("Länge bei Field %s stimmt nicht: len=%d end-start=%d"
                                          " start=%d end=%d") % (feld['name'], feld['length'],
                                                                 feld['endpos']-feld['startpos'],
                                                                 feld['startpos'], feld['endpos']))
        # resize positionarray on demand
        while len(posarray) < feld['endpos']:
            posarray.append('_')
        for i in range(feld['startpos'], feld['endpos']):
            if posarray[i] != '_':
                raise InvalidFieldDefinition("Field %s überschneidet sich mit %s an Position %d" %
                                             (feld['name'], posarray[i], i))
            posarray[i] = feld['name'] # store name
    return len(posarray)


class DatensatzBaseClass(object):
    """This is the base which will be sublassed for Records - collection of Fields."""
    length = None

    def __init__(self):
        self.fielddict = {}
        for feld in self.feldsource:
            self._feldgen(**feld)

    def __repr__(self):
        return "<%s: %s>" % (self.__name__, ', '.join([repr(x) for x in self.fielddict.values()]))

    def pretty(self):
        """Returns a nicely formated string representation suitable for debugging"""
        return "<%s: %s>" % (self.__name__,
                             ', '.join([repr(x) for x in self.fielddict.values() if str(x).strip()]))

    def _feldgen(self, name=None, length=None, startpos=None, endpos=None, fieldclass=Field, **kwargs):
        """Generate field descriptor for a single field and validate Field description."""
        
        try:
            fieldinstance = fieldclass(name, length, **kwargs)
        except:
            print fieldclass, name, length, kwargs
            raise
        # setattr(self, name, fieldinstance)
        # setattr(self, name + '_field', _FieldDescriptorClass(fieldinstance))
        setattr(self, name + '_field', fieldinstance)
        self.fielddict[startpos] = fieldinstance

    def fields(self):
        """Equivalent of vars() but beeing able to handle descriptor accessed fields."""
        return dict([(x.name, x.get()) for x in self.fielddict.values()])

    def serialize(self):
        """Return a string representation of the Datensatz (Record)."""
        data = [' '] * self.length
        for startpos, field in sorted(self.fielddict.items()):
            try:
                fielddata = field.formated()
            except Exception, e:
                raise ValueError("Error serializing %r: %s" % (field, str(e)))
            data[startpos:startpos+field.length] = list(fielddata)
        return ''.join(data)

    def parse(self, data):
        """Initiate parsing for all fields."""
        if len(data) != self.length:
            raise SizeMismatch("tried to parse %d bytes with %r - which excepts %d bytes." % (
                                len(data), self, self.length))
        # cut data in chunks fitting to our fields and the the fields parse them
        for startpos, field in sorted(self.fielddict.items()):
            # print startpos,
            field.parse(data[startpos:startpos+field.length])
            # print


def generate_field_datensatz_class(felder, name=None, length=None, doc=None):
    """Dynamicaly generate a class based on field description."""
    # keep in mind, that we are operating on a class, not on an instance.

    def klass_feldgen(klass, name=None, length=None, startpos=None, endpos=None, fieldclass=Field, **kwargs):
        """Generate field descriptor for a single field and validate Field description."""
        setattr(klass, name, FieldDescriptor(name, length, **kwargs))

    if not name:
        name = 'AnonymousDatensatzBase'

    klass = type(name, (DatensatzBaseClass, ), {'__name__': name, '__doc__': doc})
    klass.feldsource = felder
    reallength = _get_length(felder)
    klass.length = length or reallength
    if klass.length < reallength:
        raise InvalidFieldDefinition(
              "Gesamtlänge der Felder überschreitet die definierte Länge für den Datensatz %d|%d" % (
              klass.length, reallength))
    # add descriptors
    for feld in klass.feldsource:
        klass_feldgen(klass, **feld)
    return klass


if __name__ == '__main__':
    import doctest
    doctest.testmod()
