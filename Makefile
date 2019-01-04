.PHONY: all install deploy lambda

all: install deploy

# Using a fresh virtualenv, installs dependencies for the Lambda function as defined in
# requirements.txt. This makes it ready to package up into a zip as required for deployment.
install:
	cd lambda/*/ && \
		virtualenv venv && \
		source venv/bin/activate && \
		pip install --requirement requirements.txt --target . && \
		deactivate && \
		rm -rf venv && \
		rm -rf *.dist-info

# Does a forced deployment of the Alexa Skill and Lambda function. This overrides any changes made
# directly in the Alexa/AWS consoles. Dependencies must be installed first.
#
# Requires the ASK CLI, which will be installed if it isn't already:
# https://developer.amazon.com/docs/smapi/quick-start-alexa-skills-kit-command-line-interface.html
deploy:
	command -v ask || npm install -g ask-cli
	ask deploy --force

# Like the above, but for the Lambda function only.
lambda:
	command -v ask || npm install -g ask-cli
	ask deploy --force --target lambda
