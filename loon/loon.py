"""
Loon main class.
"""

# TODO
# - defaults need to (potentially) be converted
# - capture a response to command (blocking)
#   - repeat until a response received!
# - testing
# - alternative results stores
# - client/server

__all__ = ['Loon']

import os
import re
import time
import types
import logging

from threading import Thread, Event
from collections import deque
from functools import partial

import serial
from serial.tools.list_ports import comports
import yaml

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

    # parser classes for responses
    PARSERS = [
        ConnectionStatus, DeviceInfo, ScheduleInfo,
        MeterList, MeterInfo, NetworkInfo,
        TimeCluster, MessageCluster, PriceCluster,
        InstantaneousDemand, CurrentSummationDelivered,
        CurrentPeriodUsage, LastPeriodUsage,
        ProfileData, Warning, Error,
        Firmware,
    ]

    # XML API commands
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
        get_profile_data,
        image_block_dump,
    ]

    def __init__(self, device=None, start_capture=True,
                 options=None, defaults=None):
        """Initialise the Loon."""

        self._options = Node({
            'use_formatting': True
        })
        if options:
            self._options.update(options)

        self._defaults = defaults if defaults else {}

        self.responses = deque()

        if not device:
            device = self._detect_device()

        self._serial = serial.Serial(device, baudrate=115200)

        self._thread = None
        self._stop = Event()

        if start_capture:
            self.start_capture()

    @classmethod
    def from_config(cls, config, start_capture=True):

        if isinstance(config, basestring):
            config = open(config, 'r')

        if isinstance(config, file):
            config = yaml.load(config)

        return cls(
            options=config.get('options'),
            defaults=config.get('defaults'),
            start_capture=True
        )

    def _detect_device(self):
        """Guess RAVEn device name."""

        devices = comports()

        # TODO improved linux detection by hwid
        if os.name == 'posix':
            pattern = re.compile(r'/dev/tty\.(usbserial|raven)')
        elif os.name == 'nt':
            pattern = re.compile(r'FTDIBUS\\\\VID_0403\+PID_8A28')
        else:
            raise LoonError("Unable to detect device on this platform.")

        devices = [dev for dev, desc, hwid in devices if pattern.match(hwid)]

        if len(devices) == 1:
            return devices[0]
        elif not devices:
            raise LoonError("Unable to determine serial device name.")
        elif len(devices) > 1:
            raise LoonError(
                "Unable to determine unique serial device name: "
                "{0}".format(', '.join(devices))
            )

    def _get_line(self):
        """Get a line of data."""

        line = self._serial.readline()

        return line.lstrip('\0').rstrip()

    def start_capture(self):
        """Start capturing data in background."""

        if not self.capturing:
            self.initialize()

            self._stop.clear()
            self._thread = Thread(target=self._get_responses)
            self._thread.daemon = True
            self._thread.start()

    def stop_capture(self):
        """Stop capturing data in background."""

        self._stop.set()

    @property
    def capturing(self):
        """Return True if background capturing thread is active."""

        return self._thread and self._thread.is_alive()

    def set_default(self, arg, value=None):
        """Set default arguments."""

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
        """Main background process to capture and process data."""

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
                            "{0}: {1}: {2}".format(
                                tag, e, '\n'.join(response)
                            )
                        )
                        start_found = False
                        response = []
                        continue

                    try:
                        response = parser(response, self.options)
                    except LoonError as e:
                        logging.error(
                            "Invalid response data: "
                            "{0}: {1}: {2!r}".format(
                                tag, e, '\n'.join(response)
                            )
                        )
                    except SkipSignal as e:
                        logging.debug(
                            "Skipped response: {0}: {1}".format(tag, e)
                        )
                    else:
                        logging.debug(
                            "Captured response: {0}: {1}".format(tag, response)
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
