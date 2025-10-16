#!/bin/bash

# Create the wrapper directory if it doesn't exist
mkdir -p gradle/wrapper

# Download the gradle-wrapper.jar
curl -L -o gradle/wrapper/gradle-wrapper.jar https://raw.githubusercontent.com/gradle/gradle/v8.5.0/gradle/wrapper/gradle-wrapper.jar 