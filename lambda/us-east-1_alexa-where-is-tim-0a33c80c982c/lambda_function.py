"""
Advises whether Tim has left work, providing his current location relative to home.
Depends on the particular structure of geo events placed by the Proximity Events app on the iPhone.

@see https://alexa-skills-kit-python-sdk.readthedocs.io/en/latest/api/core.html
@see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html
@author Tim Malone <tim@timmalone.id.au>
"""

import json
import random
import logging
import requests
import jsonpickle

from os import getenv
from time import time
from pytz import timezone
from boto3 import client
from datetime import datetime
from ask_sdk_core import skill_builder, dispatch_components, utils

DYNAMODB_TABLE = getenv('DYNAMODB_TABLE')
EXCEPTION_MESSAGE = getenv('EXCEPTION_MESSAGE')
FALLBACK_MESSAGE = getenv('FALLBACK_MESSAGE')
FALLBACK_REPROMPT = getenv('FALLBACK_REPROMPT')
METRO_TRAINS_LINE_ID = int(getenv('METRO_TRAINS_LINE_ID'))
PRONOUN = getenv('PRONOUN').split('/')
TIMEZONE = getenv('TIMEZONE')
VALID_EVENT_MAX_AGE_IN_SECONDS = float(getenv('VALID_EVENT_MAX_AGE_IN_SECONDS'))
VALID_EVENT_MAX_ACCURACY_IN_METRES = float(getenv('VALID_EVENT_MAX_ACCURACY_IN_METRES'))

# @see https://docs.python.org/3/library/logging.html#logging-levels
LOGGING_LEVEL = getenv('LOGGING_LEVEL', 'INFO')

SECONDS_IN_AN_HOUR = 3600
SECONDS_IN_A_MINUTE = 60
MINUTES_IN_AN_HOUR = 60

skill = skill_builder.SkillBuilder()
logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)

dynamodb = client('dynamodb')

def maybe_get_invalid_date_response(now):
  """Checks the current day & time, returning appropriate speech if it's not the right moment."""

  speech = False

  if now.isoweekday() > 5:
    speech = PRONOUN[0] + "'s not at work today, so I'm not really sure!"

  elif now.hour <= 13:
    speech = "It's too early for " + PRONOUN[1] + " to have left work yet. " + \
      "Check back with me later."

  elif now.hour <= 15:
    speech = "It's a bit too early for " + PRONOUN[1] + " to have left work yet."

  return speech

def get_newest_valid_event():
  """
  Gets most recent location from DynamoDB.
  Note that as a scan is done on this table, for best performance it should only contain the
  most recent entries - i.e. a TTL attribute should be used to clean it out regularly.
  """

  newest_valid_event = None
  newest_valid_event_timestamp = 0

  for event in dynamodb.scan(TableName=DYNAMODB_TABLE)['Items']:
    timestamp = get_event_timestamp(event)

    if not is_event_accurate_enough(event) or not is_event_new_enough(event, timestamp):
      continue

    if timestamp > newest_valid_event_timestamp:
      newest_valid_event = event
      newest_valid_event_timestamp = timestamp
      logger.debug('Event ' + event['eventId']['S'] + ' is the newest so far')

  return newest_valid_event

def is_event_accurate_enough(event):
  event_accuracy = float(event['event_accuracy_m']['S'])
  if event_accuracy > VALID_EVENT_MAX_ACCURACY_IN_METRES:
    return False
  return True

def is_event_new_enough(event, timestamp):
  if timestamp < time() - VALID_EVENT_MAX_AGE_IN_SECONDS:
    return False
  return True

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

def get_speech_text_response():
  now = datetime.today().astimezone(timezone(TIMEZONE))

  # Return early if it's not a valid day of the week or time of day.
  # TODO: You can comment this out to avoid the date/time checks, if desired.
  speech = maybe_get_invalid_date_response(now)
  if speech is not False: return speech

  # Return early if there's no new enough event. Too old, we can't trust it's current.
  event = get_newest_valid_event()
  logger.info(event)
  if event is None: return "I'm sorry, I'm not sure where " + PRONOUN[0] + " is at the moment."

  suburb = get_event_suburb(event)

  distance_from_home = float(event['distance_from_home']['N'])
  distance_from_work = float(event['distance_from_work']['N'])

  # We'll generally read distances in kilometres, unless it's less than .95 of a kilometre.
  if distance_from_home < 950:
    readable_distance_from_home = str(round(distance_from_home)) + 'm'
  else:
    readable_distance_from_home = str(round(distance_from_home / 1000)) + 'km'
  if distance_from_work < 950:
    readable_distance_from_work = str(round(distance_from_work)) + 'm'
  else:
    readable_distance_from_work = str(round(distance_from_work / 1000)) + 'km'

  # TODO: Work out the best framework for accessing alternative time values here, rather than just
  #       always `time_from_home_public_transport`.
  time_from_home = int(event['time_from_home_public_transport']['N'])

  # Make the time nice and readable (speakable).
  seconds = time_from_home
  hours = seconds // SECONDS_IN_AN_HOUR
  minutes = seconds // SECONDS_IN_A_MINUTE - hours * MINUTES_IN_AN_HOUR
  if hours >= 1:
    readable_time_from_home = str(hours) + ' ' + maybe_pluralise('hour', hours)
    minutes = round_to_nearest(minutes, 5)
    if minutes > 5:
      readable_time_from_home += ' and ' + str(minutes) + ' ' + maybe_pluralise('minute', minutes)
  else:
    if minutes > 10:
      minutes = round_to_nearest(minutes, 5)
    readable_time_from_home = str(minutes) + ' ' + maybe_pluralise('minute', minutes)

  logger.debug(
    'Currently in ' + suburb + ', ' + readable_distance_from_home + ' (' + \
    readable_time_from_home + ') from home and ' + readable_distance_from_work + ' from work.'
  )

  # Work out what to say based on distance from work/home or time to home.
  if distance_from_work <= 50:

    if now.hour < 17:
      speech_choices = [
        PRONOUN[0] + " hasn't left work yet." + alexa_sound_effect('typing_medium_01'),
        PRONOUN[0] + "'s still at work." + alexa_sound_effect('typing_medium_01')
      ]
      speech = random.choice(speech_choices)

    else:
      speech_choices = [
        alexa_sound_effect('clear_throat_ahem_01') + \
          "I don't think " + PRONOUN[0] + "'s left work yet.",
        "I'm pretty sure " + PRONOUN[0] + "'s still in the office."
      ]
      speech = random.choice(speech_choices)

  elif distance_from_work <= 500:
    speech = \
      PRONOUN[0] + "'s just left work!" + alexa_sound_effect('crowd_cheer_med_01') + \
      PRONOUN[0] + " should be home in about " + readable_time_from_home + "."

  elif distance_from_home <= 50:
    speech_choices = [
      "I think " + PRONOUN[0] + "'s at home already!",
      "Looks like " + PRONOUN[0] + "'s already home!"
    ]
    speech = random.choice(speech_choices)
    return speech # No need for optional data to be added on to this.

  elif minutes == 1:
    speech = PRONOUN[0] + "'ll be here any minute!"
    return speech # No need for optional data to be added on to this.

  elif minutes < 3:
    speech = PRONOUN[0] + "'s just around the corner."
    return speech # No need for optional data to be added on to this.

  elif minutes <= 5:
    speech = PRONOUN[0] + "'ll be home in less than 5 minutes."
    return speech # No need for optional data to be added on to this.

  elif distance_from_home <= 200:
    speech_choices = [
      PRONOUN[0] + "'s almost here! Around " + readable_time_from_home + " away.",
      "Not much longer - about " + readable_time_from_home + " to go."
    ]
    speech = random.choice(speech_choices)
    return speech # No need for optional data to be added on to this.

  elif distance_from_home <= 1800:
    speech_choices = [
      PRONOUN[0] + "'s almost home! About " + readable_time_from_home + " away, " + \
        "depending on how the bus goes.",
      PRONOUN[0] + "'s not far - around " + readable_time_from_home + " to go, " + \
        "depending on the bus."
    ]
    speech = random.choice(speech_choices)
    return speech # No need for optional data to be added on to this.

  else:
    speech_choices = [
      PRONOUN[0] + "'s on his way - " + PRONOUN[0] + " should be home " + \
        "in around " + readable_time_from_home + ".",
      PRONOUN[0] + "'s about " + readable_time_from_home + " from home.",
      PRONOUN[0] + "'s currently in " + suburb + ", about " + readable_time_from_home + " away."
    ]
    speech = random.choice(speech_choices)

  # Potentially add some notes on train line performance.

  line_data = get_metro_trains_line_data(METRO_TRAINS_LINE_ID)
  line_name = line_data['name']

  train_speech_choices = {
    "travel": [
      "Metro have adjusted some services today though, " + \
        "so " + PRONOUN[0] + " may be a little longer than usual."
    ],
    "works": [
      "Metro are currently doing works on the " + line_name + " line though, " + \
        "so this may delay " + PRONOUN[1] + "."
    ],
    "minor": [
      "There's a disruption on the " + line_name + " line though, " + \
        "which may slow " + PRONOUN[1] + " down a little.",
      "But, there's a disruption on the " + line_name + " line, " + \
        "so " + PRONOUN[0] + " might take a little longer."
    ],
    "major": [
      "There are major delays on the " + line_name + " line though, " + \
        "so " + PRONOUN[0] + " might take longer.",
      "But, there's major issues on the " + line_name + " line at the moment, " + \
        "which might slow " + PRONOUN[1] + " down."
    ],
    "suspended": [
      "However, Metro tells me the " + line_name + " line is suspended, " + \
        "so " + PRONOUN[0] + " could be a lot later."
    ]
  }

  if line_data['status'] in train_speech_choices:
    speech += " " + random.choice(train_speech_choices[line_data['status']])

  return speech

############################
# Assorted helper functions
############################

def json_encode(object):
  """
  Passes custom JSON encoding to an alternative method. Mainly used for compacting log output.
  @see http://jsonpickle.github.io/api.html#customizing-json-output
  """
  return jsonpickle.pickler.encode(object, unpicklable=False)

def alexa_sound_effect(sound_effect_name):
  """@see https://developer.amazon.com/docs/custom-skills/ask-soundlibrary.html"""
  return "<audio src='soundbank://soundlibrary/office/amzn_sfx_" + sound_effect_name + "'/>"

# @see https://stackoverflow.com/questions/2272149/round-to-5-or-other-number-in-python
def round_to_nearest(number, nearest=5):
  return int(nearest * round(float(number) / nearest))

def maybe_pluralise(word, number):
  if number == 1: return word
  else: return word + 's'

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

############################
# Built-in intent handlers
# The following blocks of code derive from alexa/skill-sample-python-fact and are ASL licensed.
# @see ../../LICENSE
# @see https://github.com/alexa/skill-sample-python-fact/blob/master/lambda/py/lambda_function.py
############################

class GetLocationHandler(dispatch_components.AbstractRequestHandler):
  """Handler for Skill Launch and GetLocation Intent."""

  def can_handle(self, handler_input):
    # type: (HandlerInput) -> bool
    return \
      utils.is_request_type("LaunchRequest")(handler_input) \
      or utils.is_intent_name("GetLocation")(handler_input)

  def handle(self, handler_input):
    # type: (HandlerInput) -> Response
    logger.info("In GetLocationHandler")
    speech = get_speech_text_response()
    handler_input.response_builder.speak(speech).set_should_end_session(True)
    return handler_input.response_builder.response

class FallbackIntentHandler(dispatch_components.AbstractRequestHandler):
  """Handler for Fallback Intent."""

  def can_handle(self, handler_input):
    # type: (HandlerInput) -> bool
    return utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

  def handle(self, handler_input):
    # type: (HandlerInput) -> Response
    logger.info("In FallbackIntentHandler")
    handler_input.response_builder \
      .speak(FALLBACK_MESSAGE) \
      .ask(FALLBACK_REPROMPT) \
      .set_should_end_session(True)
    return handler_input.response_builder.response

class SessionEndedRequestHandler(dispatch_components.AbstractRequestHandler):
  """Handler for Session End."""

  def can_handle(self, handler_input):
    # type: (HandlerInput) -> bool
    return utils.is_request_type("SessionEndedRequest")(handler_input)

  def handle(self, handler_input):
    # type: (HandlerInput) -> Response
    logger.info("In SessionEndedRequestHandler")
    logger.debug("Session end: " + json_encode(handler_input.request_envelope.request.reason))
    return handler_input.response_builder.response

class CatchAllExceptionHandler(dispatch_components.AbstractExceptionHandler):
  """Catch all exception handler: logs exceptions and responds with a custom message."""

  def can_handle(self, handler_input, exception):
    # type: (HandlerInput, Exception) -> bool
    return True

  def handle(self, handler_input, exception):
    # type: (HandlerInput, Exception) -> Response
    logger.info("In CatchAllExceptionHandler")
    logger.error(exception, exc_info=True)
    handler_input.response_builder.speak(EXCEPTION_MESSAGE)
    return handler_input.response_builder.response

class RequestLogger(dispatch_components.AbstractRequestInterceptor):
  """Log the Alexa requests."""

  def process(self, handler_input):
    # type: (HandlerInput) -> None
    logger.debug("Alexa Request: " + json_encode(handler_input.request_envelope.request))

class ResponseLogger(dispatch_components.AbstractResponseInterceptor):
  """Log the Alexa responses."""

  def process(self, handler_input, response):
    # type: (HandlerInput, Response) -> None
    logger.debug("Alexa Response: " + json_encode(response))

# Register intent handlers.
skill.add_request_handler(GetLocationHandler())
skill.add_request_handler(FallbackIntentHandler())
skill.add_request_handler(SessionEndedRequestHandler())

# Register exception handlers.
skill.add_exception_handler(CatchAllExceptionHandler())

# Uncomment the following lines for request & response logs.
skill.add_global_request_interceptor(RequestLogger())
skill.add_global_response_interceptor(ResponseLogger())

# Handler name that is used on AWS lambda.
lambda_handler = skill.lambda_handler()
