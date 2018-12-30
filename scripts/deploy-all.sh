#!/usr/bin/env bash

echo
echo "Doing a forced deployment of the Alexa Skill and Lambda function..."
echo
echo "- If you've made any LIVE changes that you want to keep, press Ctrl+C NOW."
echo "- If you haven't installed new dependencies, press Ctrl+C and run install-dependencies.sh."
echo "- If you've only made changes to the Lambda function, using deploy-lambda.sh will be quicker."
echo

ask deploy --force

echo
echo "Done."
echo
