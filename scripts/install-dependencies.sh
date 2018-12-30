#!/usr/bin/env bash

# Using a fresh virtualenv, installs dependencies for the Lambda function as defined in
# requirements.txt. This makes it ready to package up into a zip as required for Lambda deployment.
#
# @see ./deploy-lambda.sh
# @author Tim Malone <tim@timmalone.id.au>

set -euo pipefail

cd lambda/*/
echo
echo "Creating a virtualenv and installing dependencies in $(pwd)..."
echo

PS1=""
virtualenv venv
source venv/bin/activate

pip install --requirement requirements.txt --target .
deactivate

echo
echo "Removing virtualenv and .dist-info folders..."
echo

rm -rf venv
rm -rf *.dist-info

echo "Done."
echo "You can now run deploy-lambda.sh to package and deploy the Lambda function."
echo
