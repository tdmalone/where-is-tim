#!/usr/bin/env bash

echo
echo "Doing a package and forced deployment of the Lambda function only..."
echo
echo "- If you've made LIVE changes to the Lambda function that you want to keep, press Ctrl+C NOW."
echo "- If you haven't installed new dependencies, press Ctrl+C and run install-dependencies.sh."
echo

ask deploy --force --target lambda

echo
echo "Done."
echo
