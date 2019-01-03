# Where is Tim?

An experimental Alexa skill that advises my wife when I'm due home from work. All she has to do is say 'Alexa, ask Tim if he's left work yet' or 'Alexa, ask Tim how far away from home he is'.

It runs as a Lambda function on the Python 3.7 runtime, and is powered by the [Alexa Skills Kit (ASK) SDK for Python](https://github.com/alexa/alexa-skills-kit-sdk-for-python) ([full documentation here](https://alexa-skills-kit-python-sdk.readthedocs.io/)).

## Why?

Just as an excuse to learn both Alexa skills and Python, really! And also because I had some of the infrastructure already set up from [previous projects](https://github.com/tdmalone/proximity-events-webhook-parser).

## Can I use this?

Sure! You likely won't be able to use it _as is_ as it's very custom made, but feel free to take whatever parts you like and make something for yourself.

You should know that not all of the required infrastructure is contained within this repo:

- **The Lambda function** was originally set up from the [Alexa Skills Kit (ASK) Sample Fact Skill [Python 3.6]](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:173334852312:applications~alexa-skills-kit-python36-factskill) ([GitHub repo](https://github.com/alexa/skill-sample-python-fact)) via the [AWS Serverless Application Repository](https://aws.amazon.com/serverless/serverlessrepo/) (SAM), with many changes made since then.
  - A number of settings have been manually changed on the Lambda function (I'll add Terraform configuration for this at some stage, since I prefer it over CloudFormation and even with [drift detection](https://aws.amazon.com/blogs/aws/new-cloudformation-drift-detection/), CloudFormation can't tell that I've messed with it).
  - The SAM deployment template adds a [Lambda Layer](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html) holding the ASK SDK, hence `ask-sdk` is not included in the function's [requirements.txt](lambda/us-east-1_alexa-where-is-tim-0a33c80c982c/requirements.txt), but would need to be added if you use/deploy it elsewhere. Otherwise, the layer's ARN is `arn:aws:lambda:us-east-1:173334852312:layer:ask-sdk-for-python-36:1` if you want to add it to your Lambda function manually.

- **The database structure** assumes a DynamoDB backend, populated by geolocation events coming from the [Proximity Events](http://proximityevents.com/) iPhone app.
  - These are parsed by a [this webhook parser](https://github.com/tdmalone/proximity-events-webhook-parser) and forwarded to an SNS topic.
  - They're then inserted into a DynamoDB table by a custom Lambda function, which does a bunch of other custom automation things based on my location (this function is currently private, but I'll make it public when I've fully separated personal configuration from the code).
  - From there, for performance reasons they're then replicated to a DynamoDB table in the same region that this Alexa skill runs from, and the data is enriched at the same time (by [this function](https://github.com/tdmalone/dynamodb-copy))

You should also know that because the original code was licensed under the Amazon Software License, a portion of it is still encumbered by it (see [LICENSE](LICENSE) for more details, specifically clause 3.2). That means this project is **not completely open source**, as clause 3.3 would appear to fall foul of clause 10 of the [Open Source definition](https://opensource.org/osd) (IANAL though - I'm just interested in licenses). This applies to all projects derived from ASL-licensed examples.

Other useful things to know:

  - For ease-of-use in deploying changes, you might like to install the [ASK CLI](https://developer.amazon.com/docs/smapi/quick-start-alexa-skills-kit-command-line-interface.html).
  - The ASK Sample Fact Skill for Python also provides some good [getting started instructions](https://github.com/alexa/skill-sample-python-fact/blob/master/instructions/1-voice-user-interface.md).
  - Train line disruption data works only in Melbourne, Australia. You'll need to rewrite it if you want to support a train service in another city/country.
  - The pronoun used in the responses can be configured with the `PRONOUN` environment variable - by setting it to eg. 'he/him', 'she/her', 'they/their', etc.

## Questions?

If you want to implement something similar and have questions - or if you've had a look at my code and think I could do something better (this is my first Python script, so be gentle), feel free to [log an issue](https://github.com/tdmalone/where-is-tim/issues/new)!

## License

[MIT and ASL](LICENSE).
