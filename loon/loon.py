"""

"""

# TODO
# ----
#
# - attributes
#   - per meter? nicknames for meters?
# - fix enumerations
#   - introduce dictionary mapping for non [a-zA-Z]\w* types
# - attach commands on the Loon
#   - per meter invocation?

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


class LoonMeta(type):
    """Loon metaclass to populate parsers."""

    def __new__(cls, name, bases, dict):

        obj = super(LoonMeta, cls).__new__(cls, name, bases, dict)

        obj.PARSERS = {cls.__name__: cls for cls in dict['PARSERS']}

        for command in dict['COMMANDS']:
            def command_method(self, command=command, **args):
                return self._serial.write(command(self, **args))

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

    def __init__(self, device, maxlen=10e3):

        self._serial = Serial(device, timeout=5)

        self._defaults = {}

        self.responses = deque(maxlen=maxlen)

        self._thread = Thread(target=self._get_responses)
        self._thread.daemon = True
        self._thread.start()

    def _get_line(self):

        return self._serial.readline().rstrip()

    def clear_responses(self):

        self.responses.clear()

    def set_default(self, arg, value=None):

        if value:
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

            # get lines until closing tag
            while True:
                line = self._get_line()

                # timed-out
                if not line:
                    logging.warn("Timed out waiting for line.")
                    continue

                response.append(line)

                if line.startswith('</'):
                    break

            try:
                parser = self.PARSERS[tag]
            except KeyError as e:
                logging.warn("Unhandled response type: {0}".format(e))

            try:
                response = parser(response, self)
            except TypeError as e:
                logging.error("Invalid response data: {0}".format(e))
            else:
                self.responses.append(response)
                logging.debug("Captured response: {0}".format(tag))
