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

import serial
from threading import Thread, Event
from collections import deque
from functools import partial

from .command import *
from .parser import *
from .exception import LoonError
from formatter import SkipSignal


start_re = re.compile(r'^<(\w+)>$')
end_re = re.compile(r'^</(\w+)>$')


class LoonMeta(type):
    """Loon meta-class to populate parsers and commands."""

    def __new__(cls, name, bases, dict):

        obj = super(LoonMeta, cls).__new__(cls, name, bases, dict)

        # register parsers on class
        obj.PARSERS = {cls.__name__: cls for cls in dict['PARSERS']}

        # add methods for commands to class
        for command in dict['COMMANDS']:
            def command_method(self, command=command, **args):
                self._serial.write(command(self, **args))
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
        initialize,  # command seems to not work
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

    def __init__(self, device, start_capture=True, queue=None):
        """Initialise the Loon."""

        self._serial = serial.Serial(
            device, baudrate=115200, bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            timeout=None
        )

        self._defaults = {}

        self.responses = queue if queue else deque()

        self._thread = None
        self._stop = Event()

        if start_capture:
            self.start_capture()

    def _get_line(self):

        line = self._serial.readline()

        return line.lstrip('\0').rstrip()

    def start_capture(self):

        if not self.capturing:
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

    def defaults():
        def fget(self):
            return self._defaults.copy()
        return locals()
    defaults = property(**defaults())

    def _get_responses(self):

        #self.initialize()

        response = []
        while not self._stop.is_set():

            line = self._get_line()

            split_line = line.split('<')
            head, tail = '<'.join(split_line[:-1]), '<' + split_line[-1]
            match = start_re.match(tail)

            if match:
                tag = match.groups()[0]
                if head:
                    response.append(head)
                if response:
                    response = '\n'.join(response)
                    logging.warn(
                        "Discarding truncated response: {0!r}".format(
                            response
                        )
                    )
                response = [tail]
            else:
                response.append(line)

            if end_re.match(line):
                # get the parser for the response-type
                try:
                    parser = self.PARSERS[tag]
                except KeyError as e:
                    logging.warn("Unhandled response type: {0}".format(e))
                    response = []
                    continue

                # parse the response
                try:
                    response = parser(response)
                except LoonError as e:
                    logging.error("Invalid response data: {0}".format(e))
                except SkipSignal as e:
                    logging.debug("Skipped response: {0}: {1}".format(tag, e))
                else:
                    logging.debug("Captured response: {0}".format(response))
                    self.responses.append(response)
                finally:
                    response = []
