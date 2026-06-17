# OAuth Callback Failure

## Symptoms

Users cannot complete login after provider redirect. Logs mention invalid callback state, OAuth code exchange failure, redirect mismatch, or invalid client.

## Checks

Validate redirect URI, client secret, provider status, callback domain, and session state storage.

## Suggested Actions

Restore OAuth configuration, rotate invalid credentials, and replay login canaries through the callback path.

