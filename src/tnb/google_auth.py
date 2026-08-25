"""One Google service-account token, shared by everything that needs one.

The judge has authenticated to Vertex this way since phase 4. Generation now
needs the same thing — Gemini is a note writer as well as a referee — and the
credential must not be loaded twice: two objects refreshing independently double
the token requests and reintroduce the race the judge already met, an HTTP 401
on 2 of 142 questions when two threads refreshed at once.

So the credential lives here, behind a lock, and both callers ask this module.
``google-auth`` is imported lazily: ``tnb models``, generation against an
ordinary provider, and the report must all keep working without the ``judge``
extra installed.
"""

from __future__ import annotations

import os
import threading

#: Vertex needs exactly this scope. Narrower than the default, on purpose.
SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)

_LOCK = threading.Lock()
_CREDENTIALS: dict[str, object] = {}


def credentials_path() -> str:
    """Where the service-account key is, from the environment.

    Never a default path: the key is a secret, it lives in the gitignored
    ``secrets/``, and guessing at its location is how one ends up committed.
    """
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not path:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set. See .env.example; the "
            "service-account key belongs in secrets/, which is gitignored."
        )
    return path


def token(*, force_refresh: bool = False, path: str | None = None) -> str:
    """A valid bearer token, refreshed when it has expired.

    ``force_refresh`` is for the caller that has just been handed a 401: the
    library thinks the token is valid and the server disagrees, and only the
    server is authoritative.
    """
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    key = path or credentials_path()
    with _LOCK:
        credential = _CREDENTIALS.get(key)
        if credential is None:
            credential = service_account.Credentials.from_service_account_file(
                key, scopes=list(SCOPES)
            )
            _CREDENTIALS[key] = credential
        if force_refresh or not credential.valid:
            credential.refresh(Request())
        return credential.token


def reset() -> None:
    """Drop the cached credential. For tests, and for a changed key file."""
    with _LOCK:
        _CREDENTIALS.clear()
