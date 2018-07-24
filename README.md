# Identifier Translator Service

## Create user account
Account registration is not allowed via HTTP, it must be done directly via CLI.
The easiest way is to run python on the api container:

```
docker exec -it identifiertranslatorservice_api python
```

Then call the `create_account()` method in `AuthController()`:
```
from api import *
authctrl.AuthController.create_account("email@obp.com", "secure_password")
```

## Auth tokens
All HTTP requests must contain the a valid authentication token within the "Authorization" header, using the Bearer schema.

Tokens can be obtained making a POST request to `/auth`, providing "email" and "password" with values equal to those used in account creation.

## Debugging
You may set env variable `API_DEBUG` to `True` in order to enable debugging
