# Identifier Translator Service
[![Build Status](https://travis-ci.org/hirmeos/identifier_translation_service.svg?branch=master)](https://travis-ci.org/hirmeos/identifier_translation_service)


## Auth tokens
All HTTP requests must contain the a valid authentication token within the "Authorization" header, using the Bearer schema.

JWTokens can be obtained from hirmeos/tokens\_api

## Debugging
You may set env variable `API_DEBUG` to `True` in order to enable debugging
