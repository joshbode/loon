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
import logging

from serial import Serial
from threading import Thread
from collections import deque

from .command import *
from .parser import *


class LoonMeta(type):
    """Loon metaclass to populate parsers."""

    def __new__(cls, name, bases, dict):

        obj = super(LoonMeta, cls).__new__(cls, name, bases, dict)

        obj.PARSERS = {cls.__name__: cls for cls in dict['PARSERS']}
        #obj.COMMANDS = {cls.__name__: cls for cls in dict['COMMANDS']}

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

    ]

    def __init__(self, device, maxlen=10e3):

        self._serial = Serial(device, timeout=5)

        self.responses = deque(maxlen=maxlen)

        self._thread = Thread(target=self._get_responses)
        self._thread.daemon = True
        self._thread.start()

        # attributes, meters?

    def _get_line(self):

        return self._serial.readline().rstrip()

    def clear_responses(self):

        self.responses.clear()

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
                response = self.PARSERS[tag](response)
            except KeyError as e:
                logging.warn("Unhandled response type: {0}".format(e))
            except TypeError as e:
                logging.error("Invalid response data: {0}".format(e))
            else:
                self.responses.append(response)
                logging.debug("Captured response: {0}".format(tag))
