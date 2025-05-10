# Open Agent Platform LangGraph Tools Agent

This is a LangGraph agent that can be used with the Open Agent Platform.

## Setup

**TODO:** Add setup docs here

## Open Agent Platform

**TODO:** Add Open Agent Platform docs here

## Authentication

This project uses LangGraph custom auth to authenticate requests to the server. It's configured to use Supabase as the authentication provider, however it can be easily swapped for another service.

Requests must contain an `Authorization` header with a `Bearer` token. This token should be a valid JWT token from Supabase.

The auth handler then takes that token and verifies it with Supabase. If the token is valid, it returns the user's identity. If the token is invalid, it raises an exception. This means you must have a Supabase URL & key set in your environment variables to use this auth handler:

```bash
SUPABASE_URL=""
SUPABASE_KEY=""
```

The auth handler is then used as middleware for all requests to the server. It is configured to run on the following events:

* `threads.create`
* `threads.read`
* `threads.delete`
* `threads.update`
* `threads.search`
* `assistants.create`
* `assistants.read`
* `assistants.delete`
* `assistants.update`
* `assistants.search`
* `store`

For creation methods, it auto-injects the user's ID into the metadata. This is then uses in all read/update/delete/search methods to ensure that the user can only access their own threads and assistants.

By using custom authentication, we can call this LangGraph server directly from a frontend application, without having to worry about exposing API keys/secrets, since you only need a JWT token from Supabase to authenticate.

For more info, see our [LangGraph custom auth docs](https://langchain-ai.github.io/langgraph/tutorials/auth/getting_started/).
