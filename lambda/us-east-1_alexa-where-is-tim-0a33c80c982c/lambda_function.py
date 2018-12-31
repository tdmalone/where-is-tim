"""
Advises whether Tim has left work, providing his current location relative to home.
Depends on the particular structure of geo events placed by the Proximity Events app on the iPhone.

@see https://alexa-skills-kit-python-sdk.readthedocs.io/en/latest/api/core.html
@see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html
@author Tim Malone <tim@timmalone.id.au>
"""

import random
import logging
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
TIMEZONE = getenv('TIMEZONE')
VALID_EVENT_MAX_AGE_IN_SECONDS = float(getenv('VALID_EVENT_MAX_AGE_IN_SECONDS'))
VALID_EVENT_MAX_ACCURACY_IN_METRES = float(getenv('VALID_EVENT_MAX_ACCURACY_IN_METRES'))

skill = skill_builder.SkillBuilder()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # TODO: Make this configurable via environment variable.

dynamodb = client('dynamodb')

def maybe_get_invalid_date_response(now):
  """Checks the current day & time, returning appropriate speech if it's not the right moment."""

  speech = False

  if now.isoweekday() > 5:
    speech = "He's not at work today, so I'm not really sure!"

  elif now.hour <= 13:
    speech = "It's too early for him to have left work yet. Check back with me later on."

  elif now.hour <= 15:
    speech = "It's a bit too early for him to have left work yet."

  return speech

def get_newest_valid_event():
  """
  Gets Tim's most recent location from DynamoDB.
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
  speech = maybe_get_invalid_date_response(now)
  if speech is not False: return speech

  # Return early if there's no new enough event. Too old, we can't trust it's current.
  event = get_newest_valid_event()
  logger.info(event)
  if event is None: return "I'm sorry, I'm not sure where he is at the moment."

  # We'll generally read distances in kilometres, unless it's less than .95 of a kilometre.
  if event['distance_from_home'] < 950:
    readable_distance_from_home = str(round(event['distance_from_home'])) + 'm'
  else:
    readable_distance_from_home = str(round(event['distance_from_home'] / 1000)) + 'km'
  if event['distance_from_work'] < 950:
    readable_distance_from_work = str(round(event['distance_from_work'])) + 'm'
  else:
    readable_distance_from_work = str(round(event['distance_from_work'] / 1000)) + 'km'

  logger.debug(
    "Currently " + readable_distance_from_home + " from home " +
    "and " + readable_distance_from_work + " from work."
  )

  if event['distance_from_work'] <= 50:

    if now.hour < 17:
      speech_choices = [
        "He hasn't left work yet." + \
          "<audio src='soundbank://soundlibrary/office/amzn_sfx_typing_medium_01'/>",
        "He's still at work. " + \
          "<audio src='soundbank://soundlibrary/office/amzn_sfx_typing_medium_01'/>"
      ]
      speech = random.choice(speech_choices)

    else:
      speech_choices = [
        "<audio src='soundbank://soundlibrary/human/amzn_sfx_clear_throat_ahem_01'/> " + \
          "I don't think he's left work yet.",
        "I'm pretty sure he's still in the office."
      ]
      speech = random.choice(speech_choices)

  elif event['distance_from_work'] <= 200:
    # TODO: Determine the minutes of travel from the current location to home.
    speech = "He's just left work! <audio src='soundbank://soundlibrary/human/amzn_sfx_crowd_cheer_med_01'/> He should be home in about X minutes."

  elif event['distance_from_home'] <= 50:
    speech_choices = [
      "I think he's at home already!",
      "Looks like he's already home!"
    ]
    speech = random.choice(speech_choices)

  elif event['distance_from_home'] <= 200:
    # TODO: Determine the minutes of travel from the current location to home.
    speech_choices = [
      "He's almost home! About X minutes away, depending on how the bus goes.",
      "He's not far - around X minutes to go, depending on the bus."
    ]
    speech = random.choice(speech_choices)

  else:
    # TODO: Determine the minutes of travel from the current location to home.
    suburb = get_event_suburb(event)
    speech_choices = [
      "He's on his way - he should be home in around X minutes.",
      "He's about X minutes from home.",
      "He's currently in " + suburb + ", about X minutes away."
    ]
    speech = random.choice(speech_choices)

    # TODO: Check for active train disruptions on the Lilydale line.
      # If active disruption...
        #speech += " There's a disruption on the Lilydale line though, which may slow him down a little."
        #speech += " But, there's a disruption on the Lilydale line, so he might take a little  longer."

  suburb = get_event_suburb(event)
  speech += " (in " + suburb + ")."
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

############################
# Built-in intent handlers
# The following blocks of code derive from alexa/skill-sample-python-fact and are ASL licensed.
# @see ../../LICENSE
# @see https://github.com/alexa/skill-sample-python-fact/blob/master/lambda/py/lambda_function.py
############################

class GetTimLocationHandler(dispatch_components.AbstractRequestHandler):
  """Handler for Skill Launch and GetTimLocation Intent."""

  def can_handle(self, handler_input):
    # type: (HandlerInput) -> bool
    return \
      utils.is_request_type("LaunchRequest")(handler_input) \
      or utils.is_intent_name("GetTimLocation")(handler_input)

  def handle(self, handler_input):
    # type: (HandlerInput) -> Response
    logger.info("In GetTimLocationHandler")
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
skill.add_request_handler(GetTimLocationHandler())
skill.add_request_handler(FallbackIntentHandler())
skill.add_request_handler(SessionEndedRequestHandler())

# Register exception handlers.
skill.add_exception_handler(CatchAllExceptionHandler())

# Uncomment the following lines for request & response logs.
skill.add_global_request_interceptor(RequestLogger())
skill.add_global_response_interceptor(ResponseLogger())

# Handler name that is used on AWS lambda.
lambda_handler = skill.lambda_handler()
