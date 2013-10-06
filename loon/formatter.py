"""
RAVEn(TM) API data formats.
"""

__all__ = [
    'Formatter',
    'String', 'Integer', 'Decimal', 'Hex', 'Date', 'Currency', 'Enumeration',
    'Event', 'Status', 'Boolean', 'MeterType', 'Queue', 'IntervalChannel',
]

import os.path
import datetime
import calendar
import decimal

from cgi import escape
from HTMLParser import HTMLParser
from xml.etree import cElementTree as ElementTree

from .exception import LoonError

unescape = HTMLParser().unescape
encoding = 'cp1252'

# load currencies (ISO 4217)
currencies = ElementTree.parse(
    os.path.join(os.path.dirname(__file__), 'currency.xml')
).find('CcyTbl')

currency_code = {
    int(e.find('CcyNbr').text): e.find('Ccy').text
    for e in currencies if e.find('CcyNbr') is not None
}

currency_number = {
    e.find('Ccy').text: int(e.find('CcyNbr').text)
    for e in currencies if e.find('CcyNbr') is not None
}


class Formatter(object):
    """RAVEn(TM) XML API argument formatter."""

    def __init__(self, name, required=False, default=None):
        """Initialise formatter."""

        self.name = name
        self.required = required
        self.default = default

    def __call__(self, text):
        """Create conformant XML API element."""

        element = ElementTree.Element(self.name)
        element.text = self.to(text)

        return element

    @classmethod
    def to(cls, obj):
        """Convert to XML API format."""

        return escape(unicode(obj)).encode(encoding, 'xmlcharrefreplace')

    @classmethod
    def convert(cls, s):
        """Convert to python object."""

        return unescape(s)


class String(Formatter):
    """String format."""

    pass


class Integer(Formatter):
    """Format integer for API."""

    def __init__(self, name, required=False, default=None,
                 range=(0, 0xffffffff)):

        super(Integer, self).__init__(name, required, default)

        self.min, self.max = range

    def to(self, obj):

        if self.min <= obj <= self.max:
            return "{0:d}".format(obj)
        else:
            raise LoonError(
                "Value is outside allowable range: {0}".format(obj)
            )

    @classmethod
    def convert(cls, s):

        return int(s)


class Decimal(Formatter):
    """Decimal format."""

    @classmethod
    def to(cls, obj):

        return "{0:.5f}".format(obj)

    @classmethod
    def convert(cls, s):

        return decimal.Decimal(s)


class Hex(Formatter):
    """Hex format, with optional range."""

    def __init__(self, name, required=False, default=None,
                 range=(0, 0xffffffffffffffff)):

        super(Hex, self).__init__(name, required, default)

        self.min, self.max = range

    def to(self, obj):

        if self.min <= obj <= self.max:
            return hex(obj)
        else:
            raise LoonError(
                "Value is outside allowable range: {0}".format(obj)
            )

    @classmethod
    def convert(cls, s):

        return int(s, base=16)


class Date(Hex):
    """Date format, in local or UTC."""

    def __init__(self, name, required=False, default=None):

        super(Date, self).__init__(
            name, required, default, range=(0, 0xffffffff)
        )

    def to(self, obj):

        return super(Date, self).to(calendar.timegm(obj.utctimetuple()))

    @classmethod
    def convert(cls, s):

        return datetime.datetime.utcfromtimestamp(super(Date, cls).convert(s))


class Currency(Hex):
    """Currency format."""

    def __init__(self, name, required=False, default=None):

        super(Currency, self).__init__(
            name, required, default, range=(0, 0xffffffff)
        )

    def to(self, obj):

        try:
            return super(Currency, self).to(currency_number[obj])
        except KeyError:
            raise LoonError("Unknown currency code: {0}".format(obj))

    @classmethod
    def convert(cls, s):

        try:
            return currency_code[super(Currency, cls).convert(s)]
        except KeyError:
            raise LoonError("Unknown currency number: {0}".format(s))


class EnumerationMeta(type):
    """Enumeration metaclass to populate attributes."""

    def __new__(cls, name, bases, dict):

        obj = super(EnumerationMeta, cls).__new__(cls, name, bases, dict)

        for i, level in enumerate(dict['LEVELS']):
            setattr(obj, level, i)

        return obj


class Enumeration(Formatter):
    """Enumeration format."""

    __metaclass__ = EnumerationMeta

    LEVELS = []

    @classmethod
    def to(cls, obj):

        try:
            return cls.LEVELS[obj]
        except (IndexError, TypeError):
            raise LoonError("Unknown/invalid level: {0}".format(obj))

    @classmethod
    def convert(cls, s):

        return getattr(cls, s)


# specific enumerations
class Event(Enumeration):
    """Scheduled event."""

    LEVELS = ['time', 'price', 'demand', 'summation', 'message']


class Status(Enumeration):
    """RAVEn(TM) status."""

    LEVELS = [
        'Initializing...', 'Network',
        'Joining', 'Join: Fail', 'Join: Success',
        'Authenticating', 'Authenticating: Success', 'Authenticating: Fail',
        'Connected', 'Disconnected', 'Rejoining'
    ]


class Boolean(Enumeration):
    """Boolean."""

    LEVELS = ['Y', 'N']


class MeterType(Enumeration):
    """Smart meter type."""

    LEVELS = ['electric', 'gas', 'water', 'other']


class Queue(Enumeration):
    """Message queue status."""

    LEVELS = ['Active', 'Cancel Pending']


class IntervalChannel(Enumeration):
    """Interval channel."""

    LEVELS = ['Delivered', 'Received']
