.. vim:filetype=rst

Device
------

- `RAVEn™ <https://rainforestautomation.com/raven>`_
- `RAVEn™ API <https://rainforestautomation.com/sites/default/files/download/rfa-z106/raven_xml_api_r127.pdf>`_

Driver
------

- https://rainforestautomation.com/content/drivers-linux-and-other-os

Prerequisites
-------------

- `pySerial <http://pyserial.sourceforge.net/>`_

Usage
-----

::
  >>> import loon
  >>> l = loon.Loon('/dev/tty.raven')
  >>> print l.responses[0]
  OrderedDict([
    ('response_type', 'InstantaneousDemand'),
    ('DeviceMacId', 1234567890), ('MeterMacId', 1234567890),
    ('TimeStamp', datetime.datetime(2013, 10, 21, 11, 51, 49)),
    ('Demand', 0.632), ('DigitsRight', 3), ('DigitsLeft', 15),
    ('SuppressLeadingZero', True)])
  ])
