# -*- coding: utf-8 -*-
"""Output module that saves data into a JSON line format.

JSON line format is a single JSON entry or event per line instead
of grouping all the output into a single JSON entity.
"""

from __future__ import unicode_literals

import json
import pytz

from plaso.lib import errors
from plaso.output import interface
from plaso.output import manager
from plaso.serializer import json_serializer
from datetime import datetime, timedelta


class SplunkOutputModule(interface.LinearOutputModule):
  """Output module for the JSON line format."""

  NAME = 'splunk'
  DESCRIPTION = 'Saves the events into a JSON line format with Splunk corrections.'

  _JSON_SERIALIZER = json_serializer.JSONAttributeContainerSerializer

  def MicrosecToSec(self, ts):
    if ts > 0:
      epoch = datetime(1970, 1, 1, tzinfo=pytz.utc)
      corrected_datetime = epoch + timedelta(microseconds=ts)
      return corrected_datetime.strftime('%s')
    else:
      return 0

  def WriteEventBody(self, event):
    """Writes the body of an event object to the output.

    Args:
      event (EventObject): event.
    """
    inode = getattr(event, 'inode', None)
    if inode is None:
      event.inode = 0

    try:
      message, _ = self._output_mediator.GetFormattedMessages(event)
    except errors.WrongFormatter:
      message = None

    if message:
      event.message = message

    json_dict = self._JSON_SERIALIZER.WriteSerializedDict(event)
    ts = self.MicrosecToSec(json_dict['timestamp'])
    json_dict['timestamp'] = ts
    json_string = json.dumps(json_dict, sort_keys=True)
    self._output_writer.Write(json_string)
    self._output_writer.Write('\n')


manager.OutputManager.RegisterOutput(SplunkOutputModule)
