.PHONY: all install test deploy lambda

all: install deploy

# Using a fresh virtualenv, installs dependencies for the Lambda function as defined in
# requirements.txt. This makes it ready to package up into a zip as required for deployment.
install:
	cd lambda/*/ && \
		virtualenv venv && \
		. venv/bin/activate && \
		mkdir -p vendor && \
		pip install --requirement requirements.txt --target vendor && \
		deactivate && \
		rm -rf venv && \
		rm -rf vendor/*.dist-info

# Runs tests, installing relevant dependencies if they're not already present.
test:
	pip list | grep -E '^pytest\s' || pip install pytest
	pip list | grep -E '^pytest-cov\s' || pip install pytest-cov
	pip list | grep -E '^boto3\s' || pip install boto3
	pip list | grep -E '^ask_sdk_core\s' || pip install ask_sdk_core
	PYTHONPATH="$(shell pwd)/$(shell find lambda/* -maxdepth 0 -type d | head -n1)/vendor:${PYTHONPATH}" \
		pytest

# Submits coverage to coveralls. Requires COVERALLS_REPO_TOKEN to be available in the environment,
# if not being run in Travis CI or Circle CI.
coverage:
	pip list | grep -E '^coveralls\s' || pip install coveralls
	coveralls

# Prepares for packaging and deployment by removing unneeded folders, and installing the ASK CLI if
# it is not already present.
prepare-deploy:
	cd lambda/*/ && \
		rm -rf __pycache__
	command -v ask || npm install -g ask-cli

# Does a forced deployment of the Alexa Skill and Lambda function. This overrides any changes made
# directly in the Alexa/AWS consoles. Dependencies must be installed first.
#
# Requires the ASK CLI, which will be installed if it isn't already:
# https://developer.amazon.com/docs/smapi/quick-start-alexa-skills-kit-command-line-interface.html
deploy: prepare-deploy
	ask deploy --force

# Like the above, but for the Lambda function only.
lambda: prepare-deploy
	ask deploy --force --target lambda
