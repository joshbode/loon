"""
RAVEn API commands.
"""

__all__ = [
    'initialize',
    'restart',
    'factory_reset',
    'get_connection_status',
    'get_device_info',
    'get_schedule',
    'set_schedule',
    'set_schedule_default',
    'get_meter_list',
    'get_meter_info',
    'get_network_info',
    'set_meter_info',
    'get_time',
    'get_message',
    'confirm_message',
    'get_current_price',
    'set_current_price',
    'get_instantaneous_demand',
    'get_current_summation_delivered',
    'get_current_period_usage',
    'get_last_period_usage',
    'close_current_period',
    'set_fast_poll',
    'get_profile_data',
]

from xml.etree import cElementTree as ElementTree

from .formatter import *
from .exception import LoonError


class Command(object):
    """RAVEn API Command."""

    ARGS = []

    def __new__(cls, loon=None, **args):
        """Generate XML API command."""

        command = ElementTree.Element('Command')

        name = ElementTree.Element('Name')
        name.text = cls.__name__

        args = {k.lower(): v for k, v in args.items()}

        # add in default arguments
        if loon:
            defaults = loon.defaults
            if defaults:
                args = args.update((
                    (k, v) for k, v in defaults.items()
                    if k.lower() not in args
                ))

        # process and format arguements
        for formatter in reversed(cls.ARGS):
            try:
                command.insert(0, formatter(args[formatter.name.lower()]))
            except KeyError:
                if formatter.required:
                    raise TypeError(
                        "Missing keyword argument: {0}".format(formatter.name)
                    )

        command.insert(0, name)

        return ElementTree.tostring(command)


class initialize(Command):
    """
    Send the INITIALIZE command to have the RAVEn(TM) reinitialize the XML
    parser. Use this command when first connecting to the RAVEn(TM) prior to
    sending any other commands. While initialization is not required, it will
    speed up the initial connection.
    """

    pass


class restart(Command):
    """
    Send the RESTART command to have the RAVEn(TM) go through the start-up
    sequence. This command is useful for capturing any diagnostic information
    sent during the start-up sequence.
    """

    pass


class factory_reset(Command):
    """
    Send the FACTORY_RESET command to decommission the RAVEn(TM).
    This command erases the commissioning data and forces a restart.
    On restart, the RAVEn(TM) will begin the commissioning cycle.
    """

    pass


class get_connection_status(Command):
    """
    Send the GET_CONNECTION_STATUS command to get the RAVEn(TM) connection
    information.
    """

    pass


class get_device_info(Command):
    """
    Send the GET_DEVICE_INFO command to get the RAVEn(TM) configuration
    information.
    """

    pass


class get_schedule(Command):
    """
    Send the GET_SCHEDULE command to get the RAVEn(TM) scheduler information.
    """

    ARGS = [
        Hex('MeterMacId'),
        Event('Event'),
    ]


class set_schedule(Command):
    """
    Send the SET_SCHEDULE command to update the RAVEn(TM) scheduler. The
    command options include setting the frequency of the command in seconds,
    and disabling the event. If the event is disabled the frequency is set to
    0xFFFFFFFF.
    """

    ARGS = [
        Hex('MeterMacId'),
        Event('Event', required=True),
        Hex('Frequency', required=True, range=(0, 0xfffffffe)),
        Boolean('Enabled', required=True),
    ]


class set_schedule_default(Command):
    """
    Send the SET_SCHEDULE_DEFAULT command to reset the RAVEn(TM) scheduler to
    default settings. If the Event field is set, only that schedule item is
    reset to default values; otherwise all schedule items are reset to their
    default values.
    """

    ARGS = [
        Hex('MeterMacId'),
        Event('Event'),
    ]


class get_meter_list(Command):
    """
    Send the GET_METER_LIST command to get the list of meters the RAVEn(TM) is
    connected to.
    """

    pass


class get_meter_info(Command):
    """
    Send the GET_METER_INFO Command to get the meter information.
    """

    ARGS = [
        Hex('MeterMacId'),
    ]


class get_network_info(Command):
    """
    Send the GET_NETWORK_INFO Command to get the status of device on the
    network.
    """

    pass


class set_meter_info(Command):
    """
    Send the SET_METER_INFO Command to set the meter information.
    """

    ARGS = [
        Hex('MeterMacId'),
        String('NickName'),
        String('Account'),
        String('Auth'),
        String('Host'),
        Boolean('Enabled'),
    ]


class get_time(Command):
    """
    Send the GET_TIME command to get the current time.
    """

    ARGS = [
        Hex('MeterMacId'),
        Boolean('Refresh'),
    ]


class get_message(Command):
    """
    Send the GET_MESSAGE command to have the RAVEn(TM) get the current text
    message.
    """

    ARGS = [
        Hex('MeterMacId'),
        Boolean('Refresh'),
    ]


class confirm_message(Command):
    """
    Send the CONFIRM_MESSAGE command to have the RAVEn(TM) confirm the message
    as indicated by the ID. To verify that the message confirmation was sent,
    use a GET_MESSAGE command with Refresh=Y.
    """

    ARGS = [
        Hex('MeterMacId'),
        Hex('Id', required=True, range=(0, 0xffffffff)),
    ]


class get_current_price(Command):
    """
    Send the GET_CURRENT_PRICE command to get the price information.
    Set the Refresh element to Y to force the RAVEn(TM) to get the information
    from the meter, not from cache.
    """

    ARGS = [
        Hex('MeterMacId'),
        Boolean('Refresh'),
    ]


class set_current_price(Command):
    """
    Send the SET_CURRENT_PRICE command to set the user-defined price on the
    RAVEn(TM). The Price field is an integer; the Trailing Digits field
    indicates where the decimal place goes (i.e., the divisor). The
    user-defined price will override the meter price. Setting the user-defined
    price to zero will clear the user entered price in the RAVEn(TM), and the
    meter price will be used, if available.
    """

    ARGS = [
        Hex('MeterMacId'),
        Hex('Price', required=True, range=(0, 0xffffffff)),
        Hex('TrailingDigits', required=True, range=(0, 0xff)),
    ]


class get_instantaneous_demand(Command):
    """
    Send the GET_INSTANTANEOUS_DEMAND command to get the demand information
    from the RAVEn(TM). Set the Refresh element to Y to force the RAVEn(TM) to
    get the information from the meter, rather than its local cache.
    """

    ARGS = [
        Hex('MeterMacId'),
        Boolean('Refresh'),
    ]


class get_current_summation_delivered(Command):
    """
    Send the GET_CURRENT_SUMMATION_DELIVERED command to get the summation
    data from the RAVEn(TM). Set the Refresh element to Y to force the
    RAVEn(TM) to get the data from the meter, rather than its local cache.
    """

    ARGS = [
        Hex('MeterMacId'),
        Boolean('Refresh'),
    ]


class get_current_period_usage(Command):
    """
    Send the GET_CURRENT_PERIOD_USAGE command to get the accumulated usage
    information from the RAVEn(TM). Note that this command will not cause the
    current period consumption total to be updated. To do this, send a
    GET_CURRENT_SUMMATION_DELIVERED command with Refresh set to Y.
    """

    ARGS = [
        Hex('MeterMacId'),
    ]


class get_last_period_usage(Command):
    """
    Send the GET_LAST_PERIOD_USAGE command to get the previous period
    accumulation data from the RAVEn(TM).
    """

    ARGS = [
        Hex('MeterMacId'),
    ]


class close_current_period(Command):
    """
    Send the CLOSE_CURRENT_PERIOD command to have the RAVEn(TM) roll over the
    current period to the last period and to initialize the current period.
    """

    ARGS = [
        Hex('MeterMacId'),
    ]


class set_fast_poll(Command):
    """
    Send the SET_FAST_POLL command to have the RAVEn(TM) set the fast poll mode
    on the meter. In fast poll mode, the meter will send Instantaneous Demand
    updates at the frequency requested. This is a ZigBee Smart Energy 1.1
    feature.

    For ZigBee Smart Energy 1.0 meters, the RAVEn(TM) will emulate this
    feature, if possible. For some meters fast poll mode will not be allowed.
    In that case, polling will default to a maximum frequency of every 4
    seconds for up to 15 minutes.
    """

    ARGS = [
        Hex('MeterMacId'),
        Hex('Frequency', required=True, range=(4, 0xffff)),
        Hex('Duration', required=True, range=(0, 900)),
    ]


class get_profile_data(Command):
    """
    Send the GET_PROFILE_DATA command to get the RAVEn(TM) to retrieve the
    interval data information from the meter.
    """

    ARGS = [
        Hex('MeterMacId'),
        Hex('NumberOfPeriods', required=True, range=(0, 12)),
        Hex('EndTime', required=True, range=(0, 0xFFFFFFFF)),
        IntervalChannel('IntervalChannel', required=True),
    ]
