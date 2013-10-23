"""
RAVEn(TM) API response parsers.
"""

__all__ = [
    'ConnectionStatus', 'DeviceInfo', 'ScheduleInfo',
    'MeterList', 'MeterInfo', 'NetworkInfo',
    'TimeCluster', 'MessageCluster', 'PriceCluster',
    'InstantaneousDemand', 'CurrentSummationDelivered',
    'CurrentPeriodUsage', 'LastPeriodUsage',
    'ProfileData', 'Warning', 'Error',
]


from collections import OrderedDict
from itertools import groupby
from xml.etree import cElementTree as ElementTree
from xml.etree.ElementTree import ParseError

from .formatter import *
from .exception import LoonError


class Parser(object):
    """Parser for RAVEn(TM) XML API responses."""

    TAGS = []

    _result_type = OrderedDict

    @classmethod
    def _parsexml(cls, response):

        # parse XML into ElementTree element
        try:
            return ElementTree.fromstringlist(response)
        except ParseError as e:
            raise LoonError(
                "Unable to parse response: {0}".format(e)
            )

    def __new__(cls, response, options=None):
        """Parse RAVEn(TM) XML API responses."""

        response = cls._parsexml(response)

        def fix_text(text):
            """Replace empty text with empty string."""

            return text.strip() if text is not None else ''

        # group up values with common tags
        data = {
            k: [fix_text(e.text) for e in v]
            for k, v in groupby(
                sorted(response, key=lambda x: x.tag),
                key=lambda x: x.tag
            )
        }

        result = cls._result_type(response_type=response.tag)

        # process tags
        for formatter in cls.TAGS:
            try:
                value = formatter.parse(data.pop(formatter.name))
            except KeyError:
                if formatter.required:
                    raise LoonError(
                        "Missing value: {0}".format(formatter.name)
                    )
            except LoonError as e:
                raise LoonError("Unable to process argument: {0}: {1}".format(
                    formatter.name, e
                ))
            else:
                # don't store empty results
                if value is not None:
                    result[formatter.name] = value

        # check for unparsed data
        if data:
            raise LoonError("Unparsed data: {0}".format(', '.join(data)))

        return result


class Warning(Parser):
    """
    Warning from RAVEn(TM).
    """

    TAGS = [
        String('Text', required=True),
    ]


class Error(Parser):
    """
    Error from RAVEn(TM).
    """

    TAGS = [
        String('Text', required=True),
    ]


class ConnectionStatus(Parser):
    """
    The RAVEn(TM) will send notifications during the start-up sequence and
    during the join/re-join sequence. These notifications are useful for
    diagnostic purposes.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Status('Status', required=True),
        String('Description'),
        Hex('StatusCode', range=(0, 0xff)),
        Hex('ExtPanId', range=(0, 0xffffffffffffffff)),
        Integer('Channel', range=(11, 26)),
        Hex('ShortAddr', range=(0, 0xffff)),
        Hex('LinkStrength', required=True, range=(0, 0x64)),
    ]


class DeviceInfo(Parser):
    """
    DeviceInfo notifications provide some basic information about the
    RAVEn(TM).
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('InstallCode', required=True),
        Hex('LinkKey', required=True),
        String('FWVersion', required=True),
        String('HWVersion', required=True),
        String('ImageType', required=True),
        String('Manufacturer', required=True),
        String('ModelId', required=True),
        String('DateCode', required=True),
    ]


class ScheduleInfo(Parser):
    """
    ScheduleInfo notifications provide the frequency at which a certain event
    is read and if it is at present enabled or disabled.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId',
            required=True, missing='0xffffffffffffffff', skip=True),
        String('Mode', required=True),  # not in API
        Event('Event'),
        Hex('Frequency', required=True, range=(0, 0xfffffffe)),
        Boolean('Enabled', required=True),
    ]


class MeterList(Parser):
    """
    MeterList notifications provide a list of meters the RAVEn(TM) is connected
    to.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId',
            required=True, sequence=True, missing='0xffffffffffffffff'),
    ]


class MeterInfo(Parser):
    """
    MeterInfo notifications provide information about meters that are on the
    network.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId',
            required=True, missing='0xffffffffffffffff', skip=True),
        MeterType('Type', required=True),  # API refers to MeterType
        String('Nickname', required=True),
        String('Account'),
        String('Auth'),
        String('Host'),
        Boolean('Enabled'),
    ]


class NetworkInfo(Parser):
    """
    NetworkInfo notifications provide information about the network that the
    device is on.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('CoordMacId', required=True),
        Status('Status', required=True),
        String('Description'),
        Hex('StatusCode', required=True, range=(0, 0xff)),
        Hex('ExtPanId', required=True, range=(0, 0xffffffffffffffff)),
        Integer('Channel', required=True, range=(11, 26)),
        Hex('ShortAddr', required=True, range=(0, 0xffff)),
        Hex('LinkStrength', required=True, range=(0, 0x64)),
    ]


class TimeCluster(Parser):
    """
    TimeCluster notifications provide the current time reported on the meter in
    both UTC and Local time. The time values are the number of seconds since
    1-Jan-2000 UTC.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Date('UTCTime', required=True),
        Date('LocalTime', required=True),
    ]


class MessageCluster(Parser):
    """
    MessageCluster notifications provide the current text message from the
    meter. If a confirmation is required, the ConfirmationRequired flag is set.
    If the user has already confirmed the message, then the Confirmed flag is
    set to Y. The ID is the reference to a particular message. The message text
    is HTML escape encoded.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Date('TimeStamp', required=True, missing='', skip=True),
        String('TimeStamp', required=True),
        Hex('Id', required=True, range=(0, 0xffffffff)),
        String('Id', required=True),
        String('Text', required=True),
        Boolean('ConfirmationRequired', required=True),
        Boolean('Confirmed', required=True),
        Queue('Queue', required=True),
    ]


class PriceCluster(Parser):
    """
    PriceCluster notification provides the current price in effect on the
    meter, or the user-defined price set on the RAVEn(TM). If the user-defined
    price is set, the meter price is ignored. If the user- defined price is not
    set and the meter price is not set, then the price returned is zero. Either
    the TierLabel or the RateLabel, or neither, may be provided; for now,
    consider these labels as substitutes. The label provided is a RAVEn(TM)
    firmware compile option that is set to match the configuration of the smart
    meter.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Date('TimeStamp', required=True),
        Hex('Price', required=True, range=(0, 0xffffffff)),
        Currency('Currency', required=True),
        Hex('TrailingDigits', required=True),
        Hex('Tier', required=True, range=(0, 0xff)),
        # either TierLabel or RateLabel will be present
        String('TierLabel', missing=''),
        String('RateLabel', missing=''),
    ]


class ScaleParser(Parser):

    NUMBERS = []

    @staticmethod
    def _scalar(x):

        return float(x) if x else 1.0

    def __new__(cls, response, options=None):

        result = super(ScaleParser, cls).__new__(cls, response, options)

        divisor = ScaleParser._scalar(result.pop('Divisor'))
        multiplier = ScaleParser._scalar(result.pop('Multiplier'))

        # pull the formatting hints
        right = result.pop('DigitsRight')
        left = result.pop('DigitsLeft') + right + 1
        zero = '' if result.pop('SuppressLeadingZero') else '0'

        for number in cls.NUMBERS:
            result[number] *= multiplier / divisor
            if options and options.get('use_formatting'):
                result[number] = '{0:{zero}{left}.{right}f}'.format(
                    result[number], zero=zero, left=left, right=right
                ).lstrip()

        return result


class InstantaneousDemand(ScaleParser):
    """
    InstantaneousDemand notification provides the current consumption rate as
    recorded by the meter.
    """

    NUMBERS = ['Demand']
    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Date('TimeStamp', required=True),
        Hex('Demand', required=True, range=(0, 0xffffff)),
        Hex('Multiplier', required=True, range=(0, 0xffffffff)),
        Hex('Divisor', required=True, range=(0, 0xffffffff)),
        Hex('DigitsRight', required=True, range=(0, 0xff)),
        Hex('DigitsLeft', required=True, range=(0, 0xff)),
        Boolean('SuppressLeadingZero', required=True),
    ]


class CurrentSummationDelivered(ScaleParser):
    """
    CurrentSummationDelivered notification provides the total consumption to
    date as recorded by the meter.
    """

    NUMBERS = ['SummationDelivered', 'SummationReceived']
    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Date('TimeStamp', required=True),
        Hex('SummationDelivered', required=True, range=(0, 0xffffffff)),
        Hex('SummationReceived', required=True, range=(0, 0xffffffff)),
        Hex('Multiplier', required=True, range=(0, 0xffffffff)),
        Hex('Divisor', required=True, range=(0, 0xffffffff)),
        Hex('DigitsRight', required=True, range=(0, 0xff)),
        Hex('DigitsLeft', required=True, range=(0, 0xff)),
        Boolean('SuppressLeadingZero', required=True),
    ]


class CurrentPeriodUsage(ScaleParser):
    """
    CurrentPeriodUsage notification provides the total consumption for the
    current accumulation period, as calculated by the RAVEn(TM). The Multiplier
    and Divisor are used to calculate the actual decimal value from the
    CurrentPeriod, which is an integer. If the Multiplier and Divisor are Zero,
    then ignore them for calculation purposes (i.e., treat them as a value of
    one). The DigitsRight and DigitsLeft are formatting hints for the data.
    These indicate what the recommended formatting is for the value. The
    SuppressLeadingZero flag overrides the DigitsLeft formatting hint.
    StartDate is a UTC timestamp indicating when the current period started.
    """

    NUMBERS = ['CurrentUsage']
    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Date('TimeStamp', required=True),
        Hex('CurrentUsage', required=True, range=(0, 0xffffffff)),
        Hex('Multiplier', required=True, range=(0, 0xffffffff)),
        Hex('Divisor', required=True, range=(0, 0xffffffff)),
        Hex('DigitsRight', required=True, range=(0, 0xff)),
        Hex('DigitsLeft', required=True, range=(0, 0xff)),
        Boolean('SuppressLeadingZero', required=True),
        Date('StartDate', required=True),
    ]


class LastPeriodUsage(ScaleParser):
    """
    LastPeriodUsage notification provides the total consumption for the
    previous accumulation period as calculated by the RAVEn(TM). The Start Date
    and End Date are UTC timestamps indicating the start and end times that
    define the previous period.
    """

    NUMBERS = ['LastUsage']
    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Hex('LastUsage', required=True, range=(0, 0xffffffff)),
        Hex('Multiplier', required=True, range=(0, 0xffffffff)),
        Hex('Divisor', required=True, range=(0, 0xffffffff)),
        Hex('DigitsRight', required=True, range=(0, 0xff)),
        Hex('DigitsLeft', required=True, range=(0, 0xff)),
        Boolean('SuppressLeadingZero', required=True),
        Date('StartDate', required=True),
        Date('EndDate', required=True),
    ]


class ProfileData(Parser):
    """
    The RAVEn(TM) sends the ProfileData notification in response to the
    GET_PROFILE_DATA command. It provides a series of interval data as recorded
    by the meter. The interval data was captured with a periodicity specified
    by the ProfileIntervalPeriod field. The content of the interval data
    depends on the type of information requested using the IntervalChannel
    field in the GET_PROFILE_DATA command. Data is organized in reverse
    chronological order: the most recent interval is transmitted first and the
    oldest interval is transmitted last.
    """

    TAGS = [
        Hex('DeviceMacId', required=True),
        Hex('MeterMacId', required=True),
        Date('EndTime', required=True),
        Hex('Status', required=True, range=(0, 0x05)),
        IntervalPeriod('ProfileIntervalPeriod', required=True),
        Hex('NumberOfPeriodsDelivered', required=True, range=(0, 0xff)),
        Hex('IntervalData',
            required=True, missing='0xffffff', sequence=True,
            range=(0, 0xffffff)),
    ]
