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

test:
	PYTHONPATH="$(shell pwd)/$(shell find lambda -type d -depth 1 | head -n1)/vendor:${PYTHONPATH}" \
		pytest

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
