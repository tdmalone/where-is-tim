"""
Assorted custom utility functions for Where Is Tim?.

@author Tim Malone <tim@timmalone.id.au>
"""

import json
import requests
import jsonpickle

from os import getenv
from time import time
from datetime import datetime

VALID_EVENT_MAX_AGE_IN_SECONDS = float(getenv('VALID_EVENT_MAX_AGE_IN_SECONDS'))
VALID_EVENT_MAX_ACCURACY_IN_METRES = float(getenv('VALID_EVENT_MAX_ACCURACY_IN_METRES'))

SECONDS_IN_AN_HOUR = 3600
SECONDS_IN_A_MINUTE = 60
MINUTES_IN_AN_HOUR = 60

def alexa_sound_effect(sound_effect_name):
  """@see https://developer.amazon.com/docs/custom-skills/ask-soundlibrary.html"""
  return "<audio src='soundbank://soundlibrary/office/amzn_sfx_" + sound_effect_name + "'/>"

def get_event_suburb(event):
  """
  Returns the second to last comma-separated portion of a Proximity Events address, which basically
  appears to always be the suburb. eg. '20 Main Street, Box Hill, VIC'
  """
  event_address_parts = event['event_address']['S'].split(', ')
  return event_address_parts[len(event_address_parts) - 2] # eg. in 3 part list of 0,1,2, we want 1.

def get_event_timestamp(event):
  event_date = event['event_date']['S']
  event_date_format = '%Y-%m-%dT%H:%M:%S%z'

  # Since event_date comes through with eg. ...+11:00 and %z expects +1100, we remove the colon.
  # @see https://stackoverflow.com/questions/30999230/parsing-timezone-with-colon
  if ':' == event_date[-3:-2]:
    event_date = event_date[:-3] + event_date[-2:]

  return datetime.strptime(event_date, event_date_format).timestamp()

def get_metro_trains_line_data(line_id):
  """
  Returns the most recent status currently set on a Metro Trains line (Melbourne, Australia), along
  with the line name.
  """

  endpoint = "http://www.metrotrains.com.au/api?op=get_healthboard_alerts"
  data = json.loads(requests.get(endpoint).content)

  # Line IDs currently range from 82-98, with some missing, plus 168307. You can find your line ID
  # in the source of metrotrains.com.au.
  if str(line_id) not in data:
    raise ValueError('The Metro Trains line ID ' + str(line_id) + ' could not be found.')

  line_data = data[str(line_id)]
  response = {}

  # We need a fallback for lines that don't have their line_name set.
  if 'line_name' in line_data:
    response['name'] = line_data['line_name']
  else:
    response['name'] = 'train'

  # If `alerts` is a string, it always means good service. Otherwise, the most recent alert is first
  # in a list. `alert_type` (in order of increasing severity) can be 'travel', 'works', 'minor',
  # 'major' or 'suspended'.
  if isinstance(line_data['alerts'], str):
    response['status'] = 'good'
  else:
    response['status'] = line_data['alerts'][0]['alert_type']

  return response

def get_readable_distance_from_metres(distance):
  """We'll generally read distances in kilometres, unless it's less than .95 of a kilometre."""
  if distance < 950:
    return str(round(distance)) + 'm'
  else:
    return str(round(distance / 1000)) + 'km'

def get_readable_time_from_seconds(seconds  ):
  """Make the time nice and readable (speakable)."""

  hours = seconds // SECONDS_IN_AN_HOUR
  minutes = seconds // SECONDS_IN_A_MINUTE - hours * MINUTES_IN_AN_HOUR

  if hours >= 1:

    readable_time = str(hours) + ' ' + maybe_pluralise('hour', hours)
    minutes = round_to_nearest(minutes, 5)

    if minutes > 5:
      readable_time += ' and ' + str(minutes) + ' ' + maybe_pluralise('minute', minutes)

  else:

    if minutes > 10:
      minutes = round_to_nearest(minutes, 5)

    readable_time = str(minutes) + ' ' + maybe_pluralise('minute', minutes)

  return readable_time

def is_event_accurate_enough(event):
  event_accuracy = float(event['event_accuracy_m']['S'])
  if event_accuracy > VALID_EVENT_MAX_ACCURACY_IN_METRES:
    return False
  return True

def is_event_new_enough(event, timestamp):
  if timestamp < time() - VALID_EVENT_MAX_AGE_IN_SECONDS:
    return False
  return True

def json_encode(object):
  """
  Passes custom JSON encoding to an alternative method. Mainly used for compacting log output.
  @see http://jsonpickle.github.io/api.html#customizing-json-output
  """
  return jsonpickle.pickler.encode(object, unpicklable=False)

def maybe_pluralise(word, number):
  if number == 1: return word
  else: return word + 's'

def round_to_nearest(number, nearest=5):
  """@see https://stackoverflow.com/questions/2272149/round-to-5-or-other-number-in-python"""
  return int(nearest * round(float(number) / nearest))
