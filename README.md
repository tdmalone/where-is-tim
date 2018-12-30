# Where Is Tim?

An experimental Alexa skill that advises my wife when I'm due home from work. All she has to do is say 'Alexa, ask Tim if he's left work yet' or 'Alexa, ask Tim how far away from home he is'.

It runs as a Lambda function on the Python 3.7 runtime, and is powered by the [Alexa Skills Kit (ASK) SDK for Python](https://github.com/alexa/alexa-skills-kit-sdk-for-python) ([full documentation here](https://alexa-skills-kit-python-sdk.readthedocs.io/)).

## Why?

Just as an excuse to learn both Alexa skills and Python, really! And also because I had some of the infrastructure set up already from [previous projects](https://github.com/tdmalone/proximity-events-webhook-parser).

## Can I use this?

Sure! You likely won't be able to use it _as is_ as it's very custom made, but feel free to take whatever parts you like and make something for yourself.

You should know that not all of the required infrastructure is contained within this repo:

- Settings applied to the Lambda function are currently done manually (I'll add Terraform configuration for this at some stage)
- The database structure assumes a DynamoDB backend, populated by geolocation events coming from the [Proximity Events](http://proximityevents.com/) iPhone app. These are:
  - parsed by a [custom webhook parser](https://github.com/tdmalone/proximity-events-webhook-parser) and forwarded to an SNS topic,
  - then inserted into the DynamoDB table by another custom Lambda function, which does a bunch of other custom automation things based on my location (this function is currently private, but I'll make it public when I've fully separated personal configuration from the code).

For ease-of-use, you might also want to install the [ASK CLI](https://developer.amazon.com/docs/smapi/quick-start-alexa-skills-kit-command-line-interface.html).

## Questions?

If you want to implement something similar and have questions - or if you've had a look at my code and think I could do something better (this is my first Python script, so be gentle), feel free to [log an issue](https://github.com/tdmalone/where-is-tim/issues/new)!

## License

[MIT](LICENSE).
