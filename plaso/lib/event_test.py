#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2012 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This file contains a unit test for the EventObject and EventContainer.

This is an implementation of an unit test for EventObject and EventContainer
storage mechanism for plaso.

The test consists of creating three EventContainers, and 6 EventObjects.

There is one base container. It contains the two other containers, and
they store the EventObjects.

The tests involve:
 + Read attributes, both set in the container level and event object.
 + Read in all the first/last timestamps of containers.

Error handling. The following tests are performed for error handling:
 + Access attributes that are not set.
"""
# Shut up pylint
# * R0924: EventContainer: Badly implemented Container
# pylint: disable=R0924

import unittest

from plaso.lib import errors
from plaso.lib import event
from plaso.proto import plaso_storage_pb2
from plaso.proto import transmission_pb2


class TestEvent1(event.EventObject):
  """A test event object."""
  DATA_TYPE = 'test:event1'

  def __init__(self, timestamp, attributes):
    """Initializes the test event object."""
    super(TestEvent1, self).__init__()
    self.timestamp = timestamp
    self.timestamp_desc = 'Some time in the future'
    self.attributes.update(attributes)


class TestEvent2(event.EventObject):
  """A test event object."""
  DATA_TYPE = 'test:event2'

  def __init__(self):
    """Initializes the test event object."""
    super(TestEvent2, self).__init__()
    self.timestamp = 1234124
    self.timestamp_desc = 'Written'

    self.empty_string = u''
    self.zero_integer = 0
    self.integer = 34
    self.string = 'Normal string'
    self.unicode_string = u'And I\'m a unicorn.'
    self.my_list = ['asf', 4234, 2, 54, 'asf']
    self.my_dict = {'a': 'not b', 'c': 34, 'list': ['sf', 234], 'an': [234, 32]}
    self.a_tuple = ('some item', [234, 52, 15], {'a': 'not a', 'b': 'not b'},
                    35)
    self.null_value = None


class FailEvent(event.EventObject):
  """An test event object without the minimal required initialization."""


class TestEventContainer(event.EventContainer):
  def __init__(self):
    """Initializes the test event container."""
    super(TestEventContainer, self).__init__()

    self.hostname = 'MYHOSTNAME'

    # A sub event container that contains 3 event objects.
    container = event.EventContainer()
    container.username = 'joesmith'
    container.filename = 'c:/Users/joesmith/NTUSER.DAT'

    event_object = event.WinRegistryEvent(
        u'MY AutoRun key', {u'Run': u'c:/Temp/evil.exe'},
        timestamp=1334961526929596)
    container.Append(event_object)

    event_object = event.WinRegistryEvent(
        u'//HKCU/Secret/EvilEmpire/Malicious_key',
        {u'Value': u'REGALERT: send all the exes to the other world'},
        timestamp=1334966206929596)
    container.Append(event_object)

    event_object = event.WinRegistryEvent(
        u'//HKCU/Windows/Normal', {u'Value': u'run all the benign stuff'},
        timestamp=1334940286000000)
    container.Append(event_object)

    self.Append(container)

    # A sub event container that contains 4 event objects.
    container = event.EventContainer()
    container.filename = 'c:/Temp/evil.exe'

    container.Append(TestEvent1(1335781787929596, {
        'text': 'This log line reads ohh so much.'}))

    container.Append(TestEvent1(1335781787929596, {
        'text': 'Nothing of interest here, move on.'}))

    container.Append(TestEvent1(1335791207939596, {
        'text': 'Mr. Evil just logged into the machine and got root.'}))

    text_dict = {'body': (
        'This is a line by someone not reading the log line properly. And '
        'since this log line exceeds the accepted 80 chars it will be '
        'shortened.'), 'hostname': 'nomachine', 'username': 'johndoe'}
    event_object = event.TextEvent(1338934459000000, text_dict)
    event_object.text = event_object.body
    container.Append(event_object)

    self.Append(container)


class PlasoEventUnitTest(unittest.TestCase):
  """The unit test for plaso storage."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    self.container = TestEventContainer()

  def testAllCount(self):
    """Test if we have all the events inside the container."""
    self.assertEquals(len(self.container), 7)

  def testContainerTimestamps(self):
    """Test first/last timestamps of containers."""

    self.assertEquals(self.container.first_timestamp, 1334940286000000)
    self.assertEquals(self.container.last_timestamp, 1338934459000000)

    serialized = self.container.ToProtoString()
    container = event.EventContainer()
    container.FromProtoString(serialized)

    self.assertEquals(container.first_timestamp, 1334940286000000)
    self.assertEquals(container.last_timestamp, 1338934459000000)
    # The container should have two sub containers:
    #   One with three events.
    #   One with four events.
    self.assertEquals(len(container), 7)
    self.assertEquals(len(container.containers), 2)
    # The parent container set one attribute, the hostname.
    self.assertEquals(len(container.attributes), 1)
    self.assertTrue('hostname' in container.attributes)
    self.assertEquals(len(container.containers[0].attributes), 2)

    first_array = []
    last_array = []
    for c in self.container.containers:
      first_array.append(c.first_timestamp)
      last_array.append(c.last_timestamp)

    first = set(first_array)
    last = set(last_array)

    self.assertIn(1334966206929596, last)
    self.assertIn(1334940286000000, first)
    self.assertIn(1335781787929596, first)
    self.assertIn(1338934459000000, last)
    self.assertIn(1334940286000000, first)
    self.assertIn(1334966206929596, last)
    self.assertIn(1335781787929596, first)
    self.assertIn(1338934459000000, last)
    self.assertIn(1334940286000000, first)
    self.assertIn(1334966206929596, last)
    self.assertIn(1335781787929596, first)
    self.assertIn(1338934459000000, last)

  def testSameEvent(self):
    """Test the EventObject comparison."""
    event_a = event.EventObject()
    event_b = event.EventObject()
    event_c = event.EventObject()
    event_d = event.EventObject()
    event_e = event.EventObject()

    event_a.timestamp = 123
    event_a.timestamp_desc = 'LAST WRITTEN'
    event_a.data_type = 'mock:nothing'
    event_a.inode = 124
    event_a.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_a.another_attribute = False

    event_b.timestamp = 123
    event_b.timestamp_desc = 'LAST WRITTEN'
    event_b.data_type = 'mock:nothing'
    event_b.inode = 124
    event_b.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_b.another_attribute = False

    event_c.timestamp = 123
    event_c.timestamp_desc = 'LAST UPDATED'
    event_c.data_type = 'mock:nothing'
    event_c.inode = 124
    event_c.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_c.another_attribute = False

    event_d.timestamp = 14523
    event_d.timestamp_desc = 'LAST WRITTEN'
    event_d.data_type = 'mock:nothing'
    event_d.inode = 124
    event_d.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_d.another_attribute = False

    event_e.timestamp = 123
    event_e.timestamp_desc = 'LAST WRITTEN'
    event_e.data_type = 'mock:nothing'
    event_e.inode = 623423
    event_e.filename = 'c:/afrit/onnurskra.txt'
    event_e.another_attribute = False

    self.assertEquals(event_a, event_b)
    self.assertNotEquals(event_a, event_c)
    self.assertEquals(event_a, event_e)
    self.assertNotEquals(event_c, event_d)

  def testEqualityString(self):
    """Test the EventObject EqualityString."""
    event_a = event.EventObject()
    event_b = event.EventObject()
    event_c = event.EventObject()
    event_d = event.EventObject()
    event_e = event.EventObject()
    event_f = event.EventObject()

    event_a.timestamp = 123
    event_a.timestamp_desc = 'LAST WRITTEN'
    event_a.data_type = 'mock:nothing'
    event_a.inode = 124
    event_a.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_a.another_attribute = False

    event_b.timestamp = 123
    event_b.timestamp_desc = 'LAST WRITTEN'
    event_b.data_type = 'mock:nothing'
    event_b.inode = 124
    event_b.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_b.another_attribute = False

    event_c.timestamp = 123
    event_c.timestamp_desc = 'LAST UPDATED'
    event_c.data_type = 'mock:nothing'
    event_c.inode = 124
    event_c.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_c.another_attribute = False

    event_d.timestamp = 14523
    event_d.timestamp_desc = 'LAST WRITTEN'
    event_d.data_type = 'mock:nothing'
    event_d.inode = 124
    event_d.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_d.another_attribute = False

    event_e.timestamp = 123
    event_e.timestamp_desc = 'LAST WRITTEN'
    event_e.data_type = 'mock:nothing'
    event_e.inode = 623423
    event_e.filename = 'c:/afrit/öñṅûŗ₅ḱŖūα.txt'
    event_e.another_attribute = False

    event_f.timestamp = 14523
    event_f.timestamp_desc = 'LAST WRITTEN'
    event_f.data_type = 'mock:nothing'
    event_f.inode = 124
    event_f.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_f.another_attribute = False
    event_f.weirdness = 'I am a potato'

    self.assertEquals(event_a.EqualityString(), event_b.EqualityString())
    self.assertNotEquals(event_a.EqualityString(), event_c.EqualityString())
    self.assertEquals(event_a.EqualityString(), event_e.EqualityString())
    self.assertNotEquals(event_c.EqualityString(), event_d.EqualityString())
    self.assertNotEquals(event_d.EqualityString(), event_f.EqualityString())

  def testEqualityPfileStatParserMissingInode(self):
    """Test that PfileStatParser files with missing inodes are distinct"""
    event_a = event.EventObject()
    event_b = event.EventObject()

    event_a.timestamp = 123
    event_a.timestamp_desc = 'LAST WRITTEN'
    event_a.data_type = 'mock:nothing'
    event_a.parser = 'PfileStatParser'
    event_a.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_a.another_attribute = False

    event_b.timestamp = 123
    event_b.timestamp_desc = 'LAST WRITTEN'
    event_b.data_type = 'mock:nothing'
    event_b.parser = 'PfileStatParser'
    event_b.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_b.another_attribute = False

    self.assertNotEquals(event_a, event_b)

  def testEqualityStringPfileStatParserMissingInode(self):
    """Test that PfileStatParser files with missing inodes are distinct"""
    event_a = event.EventObject()
    event_b = event.EventObject()

    event_a.timestamp = 123
    event_a.timestamp_desc = 'LAST WRITTEN'
    event_a.data_type = 'mock:nothing'
    event_a.parser = 'PfileStatParser'
    event_a.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_a.another_attribute = False

    event_b.timestamp = 123
    event_b.timestamp_desc = 'LAST WRITTEN'
    event_b.data_type = 'mock:nothing'
    event_b.parser = 'PfileStatParser'
    event_b.filename = 'c:/bull/skrytinmappa/skra.txt'
    event_b.another_attribute = False

    self.assertNotEquals(event_a.EqualityString(), event_b.EqualityString())

  def testDoesNotExist(self):
    """Calls to a non-existing attribute should result in an exception."""
    events = list(self.container)

    self.assertRaises(AttributeError, getattr, events[0], 'doesnotexist')

  def testExistsInEventObject(self):
    """Calls to an attribute that is stored within the EventObject itself."""
    events = list(self.container.GetSortedEvents())

    self.assertEquals(events[0].keyname, '//HKCU/Windows/Normal')

  def testExistsRegalert(self):
    """Calls to the attribute that stores the regalert."""
    events = list(self.container.GetSortedEvents())

    self.assertEquals(events[2].regalert, True)

  def testExistsInParentObject(self):
    """Call to an attribute that is contained within the parent object."""
    events = list(self.container.GetSortedEvents())

    self.assertEquals(events[0].filename, 'c:/Users/joesmith/NTUSER.DAT')

  def testNotInEventAndNoParent(self):
    """Call to an attribute that does not exist and no parent container ."""
    event_object = TestEvent1(0, {})

    self.assertRaises(AttributeError, getattr, event_object, 'doesnotexist')

  def testFailEvent(self):
    """Calls to format_string_short that has not been defined."""
    e = FailEvent()
    self.assertRaises(AttributeError, getattr, e, 'format_string_short')

  def testFailAddContainerEvent(self):
    """Add an EventContainer that is isn't an EventContainer."""
    self.assertRaises(errors.NotAnEventContainerOrObject,
                      self.container.Append, 'asd')
    self.assertRaises(errors.NotAnEventContainerOrObject,
                      self.container.Append, FailEvent())

  def testGetAttributes(self):
    """Test the GetAttributes function."""
    # get the last event
    for e in self.container:
      my_event = e

    attr = my_event.GetAttributes()

    self.assertEquals(len(attr), 8)

    self.assertEquals(sorted(attr), [
        'body', 'data_type', 'filename', 'hostname', 'text', 'timestamp',
        'timestamp_desc', 'username'])

  def testSerialization(self):
    """Test serialize event and attribute saving."""
    evt = TestEvent2()

    proto = evt.ToProto()
    proto_ser = evt.ToProtoString()

    self.assertEquals(len(list(proto.attributes)), 7)
    attributes = dict(
        event.AttributeFromProto(a) for a in proto.attributes)

    # An empty string should not get stored.
    self.assertFalse('empty_string' in attributes)

    # An integer value containing 0 should get stored.
    self.assertTrue('zero_integer' in attributes)

    self.assertEquals(len(attributes.get('my_list', [])), 5)
    self.assertEquals(attributes.get('string'), 'Normal string')
    self.assertEquals(len(attributes.get('a_tuple')), 4)

    # A None (or Null) value should not get stored.
    self.assertFalse('null_value' in attributes)

    # Go back
    evt2 = event.EventObject()
    evt2.FromProtoString(proto_ser)

    self.assertEquals(evt2.timestamp, evt.timestamp)
    self.assertEquals(evt.my_dict, evt2.my_dict)
    self.assertEquals(evt.my_list, evt2.my_list)
    self.assertEquals(evt.string, evt2.string)
    self.assertFalse('empty_string' in evt2.attributes)
    self.assertFalse('null_value' in evt2.attributes)


class EventTaggingUnitTest(unittest.TestCase):
  """The unit test for the EventTag object."""

  def testEventTag(self):
    """Test the serialization and deserialization of EventTagging."""
    proto = plaso_storage_pb2.EventTagging()
    proto.store_number = 234
    proto.store_index = 18
    proto.comment = 'My first comment.'
    proto.color = 'Red'
    tag1 = proto.tags.add()
    tag1.value = 'Malware'
    tag2 = proto.tags.add()
    tag2.value = 'Common'

    event_tag = event.EventTag()
    event_tag.FromProto(proto)

    self.assertEquals(event_tag.color, 'Red')
    self.assertEquals(event_tag.comment, 'My first comment.')
    self.assertEquals(event_tag.store_index, 18)
    self.assertEquals(len(event_tag.tags), 2)

    serialized1 = proto.SerializeToString()
    serialized2 = event_tag.ToProtoString()

    self.assertEquals(serialized1, serialized2)

    event_tag_2 = event.EventTag()
    event_tag_2.FromProtoString(serialized2)
    self.assertEquals(event_tag.tags, event_tag_2.tags)

    # Test setting an 'illegal' attribute.
    self.assertRaises(
        AttributeError, setattr, event_tag_2, 'notdefined', 'Value')


class EventPathSpecUnitTest(unittest.TestCase):
  """The unit test for the PathSpec object."""

  def testEventPathSpec(self):
    """Test serialize/deserialize EventPathSpec event."""
    proto = transmission_pb2.PathSpec()
    proto.file_path = '/tmp/nowhere'
    proto.type = 0

    evt = event.EventPathSpec()
    evt.FromProto(proto)

    self.assertEquals(evt.type, 'OS')

    nested_proto = transmission_pb2.PathSpec()
    nested_proto.container_path = 'SomeFilePath'
    nested_proto.type = 2
    nested_proto.file_path = 'My.zip'
    nested_proto.image_offset = 35
    nested_proto.image_inode = 6124543

    proto.nested_pathspec.MergeFrom(nested_proto)
    proto_str = proto.SerializeToString()

    evt2 = event.EventPathSpec()
    evt2.FromProtoString('P' + proto_str)

    self.assertEquals(evt2.file_path, '/tmp/nowhere')
    self.assertTrue(hasattr(evt2, 'nested_pathspec'))
    nested_evt = evt2.nested_pathspec

    self.assertEquals(nested_evt.image_offset, 35)
    self.assertEquals(nested_evt.image_inode, 6124543)
    self.assertEquals(nested_evt.type, 'ZIP')

    proto_evt2 = evt2.ToProto()

    self.assertEquals(proto_evt2.file_path, '/tmp/nowhere')


class EventPathBundleTest(unittest.TestCase):
  """The unit test for the PathBundle protobuf."""

  def testEventBundle(self):
    """Test the serialize/deserialize EventBundle event."""
    pattern = '/tmp/.+'

    proto = transmission_pb2.PathBundle()
    proto.pattern = pattern

    p1_proto = transmission_pb2.PathSpec()
    p1_proto.file_path = '/tmp/nowhere'
    # Type 0 = OS.
    p1_proto.type = 0

    first_pathspec = proto.pathspecs.add()
    first_pathspec.MergeFrom(p1_proto)

    nested_proto = transmission_pb2.PathSpec()
    nested_proto.container_path = 'SomeFilePath'
    nested_proto.type = 2
    nested_proto.file_path = 'My.zip'
    nested_proto.image_offset = 35
    nested_proto.image_inode = 6124543

    p1_proto.nested_pathspec.MergeFrom(nested_proto)

    second_pathspec = proto.pathspecs.add()
    second_pathspec.MergeFrom(p1_proto)

    p2_proto = transmission_pb2.PathSpec()
    # Type 1 = TSK.
    p2_proto.type = 1
    p2_proto.container_path = 'myimage.raw'
    p2_proto.image_inode = 124
    p2_proto.image_offset = 12345

    third_pathspec = proto.pathspecs.add()
    third_pathspec.MergeFrom(p2_proto)

    bundle = event.EventPathBundle()
    bundle.FromProto(proto)

    # pylint: disable=W0212
    self.assertEquals(len(bundle._pathspecs), 3)
    self.assertEquals(len(list(bundle.ListFiles())), 3)
    self.assertEquals(bundle.pattern, pattern)

    nested_hash = u'-:-:-:-:/tmp/nowhere:SomeFilePath:35:-:6124543:My.zip:'
    nested_pathspec = bundle.GetPathspecFromHash(nested_hash)

    self.assertEquals(
        nested_pathspec.ToProtoString(), 'P' + p1_proto.SerializeToString())


if __name__ == '__main__':
  unittest.main()