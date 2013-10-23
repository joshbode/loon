"""
Loon main class.
"""

# TODO
# - Clear line buffer if new tag starts in middle of existing message
# - testing
# - alternative results stores
# - client/server

__all__ = ['Loon']

import re
import time
import types
import logging

from threading import Thread, Event
from collections import deque
from functools import partial

import serial

from .command import *
from .parser import *
from .node import Node
from .exception import LoonError
from formatter import SkipSignal


start_re = re.compile(r'^<([a-zA-Z]+)>$')
end_re = re.compile(r'^</([a-zA-Z]+)>$')


class LoonMeta(type):
    """Loon meta-class to populate parsers and commands."""

    def __new__(cls, name, bases, dict):

        obj = super(LoonMeta, cls).__new__(cls, name, bases, dict)

        # register parsers on class
        obj.PARSERS = {cls.__name__: cls for cls in dict['PARSERS']}

        # add methods for commands to class
        for command in dict['COMMANDS']:
            def command_method(self, command=command, **args):
                self._serial.write(command(defaults=self.defaults, **args))
            command_method.__doc__ = command.__doc__

            setattr(obj, command.__name__, command_method)

        return obj


# main class
class Loon(object):
    """Loon"""

    __metaclass__ = LoonMeta

    PARSERS = [
        ConnectionStatus, DeviceInfo, ScheduleInfo,
        MeterList, MeterInfo, NetworkInfo,
        TimeCluster, MessageCluster, PriceCluster,
        InstantaneousDemand, CurrentSummationDelivered,
        CurrentPeriodUsage, LastPeriodUsage,
        ProfileData, Warning,
    ]

    COMMANDS = [
        initialize,
        restart,
        factory_reset,
        get_connection_status,
        get_device_info,
        get_schedule,
        set_schedule,
        set_schedule_default,
        get_meter_list,
        get_meter_info,
        get_network_info,
        set_meter_info,
        get_time,
        get_message,
        confirm_message,
        get_current_price,
        set_current_price,
        get_instantaneous_demand,
        get_current_summation_delivered,
        get_current_period_usage,
        get_last_period_usage,
        close_current_period,
        set_fast_poll,
        get_profile_data
    ]

    def __init__(self, device, options=None, start_capture=True):
        """Initialise the Loon."""

        self._serial = serial.Serial(
            device, baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=None
        )

        self._defaults = {}
        self._options = Node(options if options else {})

        self.responses = deque()

        self._thread = None
        self._stop = Event()

        if start_capture:
            self.start_capture()

    def _get_line(self):

        line = self._serial.readline()

        return line.lstrip('\0').rstrip()

    def start_capture(self):

        if not self.capturing:
            self.initialize()

            self._stop.clear()
            self._thread = Thread(target=self._get_responses)
            self._thread.daemon = True
            self._thread.start()

    def stop_capture(self):

        self._stop.set()

    @property
    def capturing(self):

        return self._thread and self._thread.is_alive()

    def set_default(self, arg, value=None):

        if value is not None:
            self._defaults[arg] = value
        else:
            del self._defaults[arg]

    def options():
        def fget(self):
            return self._options.copy()
        return locals()
    options = property(**options())

    def defaults():
        def fget(self):
            return self._defaults.copy()
        return locals()
    defaults = property(**defaults())

    def _get_responses(self):

        start_found = False
        response = []

        while not self._stop.is_set():

            line = self._get_line()

            # look for truncated responses
            n = line.rfind('<')
            head, tail = line[:n], line[n:]

            start = start_re.match(tail)
            end = end_re.match(head or tail)

            if start:
                # potentially (and probably) truncated line
                if head:
                    response.append(head)
            else:
                response.append(line)

            if end:
                if start_found:

                    # get the parser for the response-type
                    tag = end.group(1)

                    try:
                        parser = self.PARSERS[tag]
                    except KeyError as e:
                        logging.warn(
                            "Unhandled response type: "
                            "{0}: {1}".format(e, '\n'.join(response))
                        )
                        start_found = False
                        response = []
                        continue

                    try:
                        response = parser(response, self.options)
                    except LoonError as e:
                        logging.error(
                            "Invalid response data: "
                            "{0}: {1!r}".format(e, '\n'.join(response))
                        )
                    except SkipSignal as e:
                        logging.debug(
                            "Skipped response: {0}: {1}".format(tag, e)
                        )
                    else:
                        logging.debug(
                            "Captured response: {0}".format(response)
                        )
                        self.responses.append(response)

                else:
                    logging.warn(
                        "Discarding truncated response (missing start): "
                        "{0!r}".format('\n'.join(response))
                    )

                start_found = False
                response = []

            # check this last in case there was a truncated end record
            if start:
                if response:
                    logging.warn(
                        "Discarding truncated response (missing end): "
                        "{0!r}".format('\n'.join(response))
                    )
                start_found = True
                response = [tail]

    def __del__(self):

        self.stop_capture()
        self._serial.close()
