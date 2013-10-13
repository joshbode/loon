"""
Loon main class.
"""

# TODO
# ----
#

__all__ = ['Loon']

import time
import types
import logging

from serial import Serial
from threading import Thread
from collections import deque
from functools import partial

from .command import *
from .parser import *
from .exception import LoonError


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

    def __init__(self, device, queue=None):
        """Initialise the Loon."""

        self._serial = Serial(device, timeout=5)

        self._defaults = {}

        self.responses = queue if queue else deque()

        self._thread = Thread(target=self._get_responses)
        self._thread.daemon = True
        self._thread.start()

    def _get_line(self):

        return self._serial.readline().lstrip('\0').rstrip()

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

        while True:
            response = []

            # chew lines until a start tag is found
            while True:
                line = self._get_line()

                if line.startswith('<') and not line.startswith('</'):
                    response.append(line)
                    tag = line.replace('<', '').replace('>', '')
                    break

                if line:
                    logging.warn("Unexpected line found: {0!r}".format(line))

            # get lines until closing tag
            while True:
                line = self._get_line()

                # timed-out
                if not line:
                    logging.warn("Timed out waiting for next line.")
                    continue

                response.append(line)

                if line.startswith('</'):
                    break

            # get the parser for the response-type
            try:
                parser = self.PARSERS[tag]
            except KeyError as e:
                logging.warn("Unhandled response type: {0}".format(e))

            # parse the response
            try:
                response = parser(response)
            except LoonError as e:
                logging.error("Invalid response data: {0}".format(e))
            except SkipSignal as e:
                logging.debug("Skipped response: {0}: {1}".format(tag, e))
            else:
                logging.debug("Captured response: {0}".format(tag))
                self.responses.append(response)
