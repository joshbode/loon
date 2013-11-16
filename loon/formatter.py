"""
RAVEn(TM) API data formats.
"""

__all__ = [
    'Formatter', 'SkipSignal',
    'String', 'Base64String',
    'Integer', 'Decimal', 'Hex', 'Date', 'Currency', 'Enumeration',
    'Event', 'Status', 'Boolean', 'MeterType', 'Queue',
    'IntervalChannel', 'IntervalPeriod',
]

import os.path
import datetime
import calendar
import decimal

from collections import OrderedDict

from cgi import escape as cgi_escape
from HTMLParser import HTMLParser

from xml.etree import cElementTree as ElementTree

from .exception import LoonError

unescape = HTMLParser().unescape
api_encoding = 'cp1252'


def escape(x, encoding=api_encoding):
    """Escape string for HTML."""

    return cgi_escape(unicode(x)).encode(encoding, 'xmlcharrefreplace')


def indent(elem, level=0, shift=2):
    """Indent ElementTree in-place."""

    i = '\n' + ' ' * level * shift

    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + ' ' * shift
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1, shift)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


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


class SkipSignal(Exception):
    """Skip the rest of the response."""

    pass


class Formatter(object):
    """RAVEn(TM) XML API argument formatter."""

    def __init__(self, name, required=False, missing=None, skip=False,
                 sequence=False):
        """Initialise formatter."""

        if required and missing is not None and not (skip or sequence):
            raise TypeError("Value cannot be both required and missing.")

        if skip and missing is None:
            raise TypeError("Cannot skip response without missing value.")

        self.name = name
        self.required = required
        self.missing = missing
        self.skip = skip
        self.sequence = sequence

    def __call__(self, value):
        """Create XML API element."""

        element = ElementTree.Element(self.name)
        element.text = self.encode(value)

        return element

    def parse(self, value):
        """Parse XML API value."""

        if not self.sequence and len(value) > 1:
            raise LoonError("Sequence not allowed.")

        # process data and remove missing values
        result = [x for x in value if x != self.missing]
        result = [self._parse(x) for x in result]

        # handle unrequired missing data
        if not result and not (self.sequence and self.required):
            if self.skip:
                raise SkipSignal("Missing {0}".format(self.name))
            else:
                return None

        return result if self.sequence else result[0]

    @classmethod
    def encode(cls, obj):
        """Convert object to XML API format."""

        return escape(obj)

    def _parse(self, value):
        """Convert XML API value to object."""

        return unescape(value)


class String(Formatter):
    """String format."""

    pass


class Base64String(Formatter):
    """Base64 encoded string."""

    @classmethod
    def encode(cls, obj):
        """Convert object to XML API format."""

        return str(obj).encode('base64')

    def _parse(self, value):
        """Convert XML API value to object."""

        return value.decode('base64')


class Integer(Formatter):
    """Format integer for API."""

    def __init__(self, name, required=False, missing=None, skip=False,
                 sequence=False, range=(0, 0xffffffff)):

        self.min, self.max = range

        super(Integer, self).__init__(name, required, missing, skip, sequence)

    def encode(self, obj):
        """Convert object to XML API format."""

        if self.min <= obj <= self.max:
            return "{0:d}".format(obj)
        else:
            raise LoonError(
                "Value is outside allowable range: {0}".format(obj)
            )

    def _parse(self, value):
        """Convert XML API value to object."""

        return int(value)


class Decimal(Formatter):
    """Decimal format."""

    @classmethod
    def encode(cls, obj):
        """Convert object to XML API format."""

        return "{0:.5f}".format(obj)

    def _parse(self, value):
        """Convert XML API value to object."""

        return decimal.Decimal(value)


class Hex(Formatter):
    """Hex format, with optional range."""

    def __init__(self, name, required=False, missing=None, skip=False,
                 sequence=False, range=(0, 0xffffffffffffffff)):

        self.min, self.max = range

        super(Hex, self).__init__(name, required, missing, skip, sequence)

    def encode(self, obj):
        """Convert object to XML API format."""

        if self.min <= obj <= self.max:
            return hex(obj)
        else:
            raise LoonError(
                "Value is outside allowable range: {0}".format(obj)
            )

    def _parse(self, value):
        """Convert XML API value to object."""

        return int(value, base=16)


class Date(Hex):
    """Date format, in local or UTC."""

    EPOCH = calendar.timegm(
        datetime.datetime(2000, 1, 1).utctimetuple()
    )

    def __init__(self, name, required=False, missing=None, skip=False,
                 sequence=False):

        super(Date, self).__init__(
            name, required, missing, skip, sequence, range=(0, 0xffffffff)
        )

    def encode(self, obj):
        """Convert object to XML API format."""

        return super(Date, self).encode(
            calendar.timegm(obj.utctimetuple()) - Date.EPOCH
        )

    def _parse(self, value):
        """Convert XML API value to object."""

        return datetime.datetime.utcfromtimestamp(
            super(Date, self)._parse(value) + Date.EPOCH
        )


class Currency(Hex):
    """Currency format."""

    def __init__(self, name, required=False, missing=None, skip=False,
                 sequence=False):

        super(Currency, self).__init__(
            name, required, missing, skip, sequence, range=(0, 0xffffffff)
        )

    def encode(self, obj):
        """Convert object to XML API format."""

        try:
            return super(Currency, self).encode(currency_number[obj])
        except KeyError:
            raise LoonError("Unknown currency code: {0}".format(obj))

    def _parse(self, value):
        """Convert XML API value to object."""

        try:
            return currency_code[super(Currency, self)._parse(value)]
        except KeyError:
            raise LoonError("Unknown currency number: {0}".format(value))


class Boolean(Formatter):
    """Boolean format."""

    _MAP = {'N': False, 'Y': True}

    @classmethod
    def encode(cls, obj):
        """Convert object to XML API format."""

        return 'Y' if obj else 'N'

    def _parse(self, value):
        """Convert XML API value to object."""

        return Boolean._MAP[value]


class EnumerationMeta(type):
    """Enumeration metaclass to populate attributes."""

    def __new__(cls, name, bases, d):

        obj = super(EnumerationMeta, cls).__new__(cls, name, bases, d)

        obj.LEVELS = OrderedDict(
            (x, x) if isinstance(x, basestring) else x
            for x in d['LEVELS']
        )

        for i, level in enumerate(obj.LEVELS):
            setattr(obj, level.upper(), i)

        return obj


class Enumeration(Formatter):
    """Enumeration format."""

    __metaclass__ = EnumerationMeta

    LEVELS = []

    @classmethod
    def encode(cls, obj):
        """Convert object to XML API format."""

        try:
            if isinstance(obj, (int, long)):
                return cls.LEVELS.values()[obj]
            else:
                return cls.LEVELS[obj]
        except (IndexError, KeyError):
            raise LoonError("Unknown/invalid level: {0}".format(obj))

    def _parse(self, value):
        """Convert XML API value to object."""

        try:
            return self.LEVELS.values().index(value)
        except IndexError:
            raise LoonError("Unknown/invalid level: {0}".format(value))


# specific enumerations
class Event(Enumeration):
    """Scheduled event."""

    LEVELS = [
        'time', 'price', 'demand', 'summation', 'message',
        # following not mentioned in API documentation
        'scheduled_prices', 'profile_data'
    ]


class Status(Enumeration):
    """RAVEn(TM) status."""

    LEVELS = [
        ('initializing', "Initializing..."),
        ('network', "Network"),
        ('joining', "Joining"),
        ('join_fail', "Join: Fail"),
        ('join_success', "Join: Success"),
        ('authenticating', "Authenticating"),
        ('auth_success', "Authenticating: Success"),
        ('auth_fail', "Authenticating: Fail"),
        ('connected', "Connected"),
        ('disconnected', "Disconnected"),
        ('rejoining', "Rejoining")
    ]


class MeterType(Enumeration):
    """Smart meter type."""

    # Zigbee Smart Energy specification, page 184
    LEVELS = [
        ('electric', '0x0000'),
        ('gas', '0x0001'),
        ('water', '0x0002'),
        ('thermal', '0x0003'),
        ('pressure', '0x0004'),
        ('heat', '0x0005'),
        ('cooling', '0x0006'),
    ]


class Queue(Enumeration):
    """Message queue status."""

    LEVELS = [
        ('active', "Active"),
        ('cancel_pending', "Cancel Pending")
    ]


class IntervalChannel(Enumeration):
    """Interval channel."""

    LEVELS = [
        ('delivered', 'Delivered'),
        ('received', 'Received')
    ]


class IntervalPeriod(Formatter):
    """Interval period."""

    INTERVALS = OrderedDict([
        (86400, "Daily"),
        (3600, "60 minutes"),
        (1800, "30 minutes"),
        (900, "15 minutes"),
        (600, "10 minutes"),
        (450, "7.5 minutes"),
        (300, "5 minutes"),
        (150, "2.5 minutes"),
    ])

    @classmethod
    def encode(cls, obj):
        """Convert object to XML API format."""

        try:
            return str(IntervalPeriod.INTERVALS.index(int(obj)))
        except IndexError:
            raise LoonError("Unknown/invalid interval: {0}".format(obj))

    @staticmethod
    def _parse(value):
        """Convert XML API value to object."""

        try:
            return IntervalPeriod.INTERVALS.keys()[int(value)]
        except IndexError:
            raise LoonError("Unknown/invalid interval: {0}".format(value))
