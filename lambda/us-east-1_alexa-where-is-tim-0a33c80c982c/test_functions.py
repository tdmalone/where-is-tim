
import json

from os import environ, getenv
from time import time
from pytest import fixture, mark
from datetime import datetime
from dateutil.tz import tzoffset

environ['VALID_EVENT_MAX_AGE_IN_SECONDS'] = '86400'
environ['VALID_EVENT_MAX_ACCURACY_IN_METRES'] = '65'
environ['METRO_TRAINS_ENDPOINT'] = 'http://localhost/metrotrains'

import functions

@mark.skip(reason="TODO: Need to add mocking of the API endpoint for this")
def test_alexa_sound_effect():
  # TODO: functions.alexa_sound_effect()
  assert True

def test_get_event_suburb():
  fake_event = {'event_address': {'S': '123 Main Street, Suburb, STATE'}}
  assert functions.get_event_suburb(fake_event) == 'Suburb'

def test_get_event_timestamp():
  _test_get_event_timestamp(0)   # Correct timestamp returned with GMT
  _test_get_event_timestamp(+10) # Correct timestamp returned with positive offset
  _test_get_event_timestamp(-10) # Correct timestamp returned with negative offset
  _test_get_event_timestamp(+9)  # Correct timestamp returned with single digit

def _test_get_event_timestamp(offset):
  year = 2018; month = 12; date = 30
  hour = 17; minute = 58; second = 37

  maybe_positive = '+' if offset >= 0 else ''
  pretty_offset = maybe_positive + '{0:02d}:00'.format(offset) # eg. -10:00, +00:00, +09:00, +10:00
  timezone = tzoffset(None, offset * 60 * 60)

  fake_date = '{}-{}-{}T{}:{}:{}{}'.format(2018, month, date, hour, minute, second, pretty_offset)
  fake_event = {'event_date': {'S': fake_date}}
  fake_timestamp = datetime(year, month, date, hour, minute, second, tzinfo=timezone).timestamp()

  assert functions.get_event_timestamp(fake_event) == fake_timestamp

@mark.skip(reason="TODO: Need to add mocking of the API endpoint for this")
def test_get_metro_trains_line_data():
  pass

def test_get_readable_distance_from_metres():
  testable = functions.get_readable_distance_from_metres

  assert testable(949) == '949m' # Expressed in metres below 950m.
  assert testable(950) == '1km'  # Rounded to nearest kilometre at 950m.
  assert testable(1499) == '1km' # Rounded down to nearest kilometre.
  assert testable(1500) == '2km' # Rounded up to nearest kilometre.

def test_get_readable_time_from_seconds():
  testable = functions.get_readable_time_from_seconds

  assert testable(0) == "0 minutes"    # Exact minute, with correct pluralisation for zero.
  assert testable(50) == "0 minutes"   # Rounds down to current minute.
  assert testable(60) == "1 minute"    # Exact minute, with correct pluralisation for single.
  assert testable(110) == "1 minute"   # Rounds down to current minute.
  assert testable(120) == "2 minutes"  # Exact minute, with correct pluralisation for plural.
  assert testable(540) == "9 minutes"  #  9 min : Uses current minute when below 10.
  assert testable(720) == "10 minutes" # 12 min : Rounds down to nearest 5 minutes when above 10.
  assert testable(780) == "15 minutes" # 13 min : Rounds up to nearest 5 minutes when above 10.
  assert testable(3600) == "1 hour"    # Exact hour, with correct pluralisation for single.
  assert testable(3900) == "1 hour"                # 1 hr  5 min : Rounds to hour when <= 5 min.
  assert testable(6660) == "1 hour and 50 minutes" # 1 hr 51 min : Rounds to nearest 5.
  assert testable(7200) == "2 hours"   # Exact hour, with correct pluralisation for plural.

def test_is_event_accurate_enough():
  fake_event = {'event_accuracy_m': {'S': ''}}
  valid_accuracy = getenv('VALID_EVENT_MAX_ACCURACY_IN_METRES')
  testable = functions.is_event_accurate_enough

  # Returns false for low accuracy
  fake_event['event_accuracy_m']['S'] = str(float(valid_accuracy) + 10)
  assert testable(fake_event) == False

  # Returns true for high accuracy
  fake_event['event_accuracy_m']['S'] = str(float(valid_accuracy) - 10)
  assert testable(fake_event) == True

  # Returns true for spot-on accuracy
  fake_event['event_accuracy_m']['S'] = valid_accuracy
  assert testable(fake_event) == True

def test_is_timestamp_new_enough():

  # Really old timestamp is old
  assert functions.is_timestamp_new_enough(0) == False

  # Really new timestamp (20th Nov 2286!) is new
  assert functions.is_timestamp_new_enough(9999999999) == True

  # Slightly old timestamp is old
  slightly_old_timestamp = time() - float(getenv('VALID_EVENT_MAX_AGE_IN_SECONDS')) - 100
  assert functions.is_timestamp_new_enough(slightly_old_timestamp) == False

  # Recent timestamp is new
  slightly_recent_timestamp = time() - 300
  assert functions.is_timestamp_new_enough(slightly_recent_timestamp) == True

def test_json_encode():

  sample_object = {'sample': 12345}
  encoded_object = functions.json_encode(sample_object)

  # json_encode returns a string
  assert isinstance(encoded_object, str)

  # Returned string can be successfully loaded (and validated)
  assert sample_object['sample'] == json.loads(encoded_object)['sample']

def test_maybe_pluralise():
  assert functions.maybe_pluralise('test', 0) == 'tests'  # Pluralises on 0
  assert functions.maybe_pluralise('test', 1) == 'test'   # Does not pluralise on 1
  assert functions.maybe_pluralise('test', 2) == 'tests'  # Pluralises on 2
  assert functions.maybe_pluralise('test', 11) == 'tests' # Pluralises on 11 (no confusion on the 1)

def test_round_to_nearest():
  assert functions.round_to_nearest(1) == 0    # Rounds down correctly with default increment
  assert functions.round_to_nearest(3) == 5    # Rounds up correctly with default increment
  assert functions.round_to_nearest(5) == 5    # Does not round when default increment matches
  assert functions.round_to_nearest(1, 3) == 0 # Rounds down correctly when increment specified
  assert functions.round_to_nearest(2, 3) == 3 # Rounds up correctly when increment specified
  assert functions.round_to_nearest(3, 3) == 3 # Does not round when specified increment matches
