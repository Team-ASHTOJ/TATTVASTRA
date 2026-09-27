"""Control-plane adapter to the internal fixed-command local runtime."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from jocky_control_plane.config import Settings


def runtime(
    settings: Settings, route: str, body: dict[str, Any] | None = None, slot: int = 1
) -> dict[str, Any]:
    if not settings.local_launcher_url or not settings.local_launcher_token:
        raise HTTPException(503, "Local runtime is unavailable. Start the stack with make demo-up.")
    url = settings.local_launcher_url
    if slot != 1:
        if len(settings.local_launcher_urls) < slot:
            raise HTTPException(503, "Additional local runtimes are not configured")
        url = settings.local_launcher_urls[slot - 1]
    request = Request(
        url + route,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {settings.local_launcher_token.get_secret_value()}",
            "Content-Type": "application/json",
        },
        method="POST" if body is not None else "GET",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result: dict[str, Any] = json.load(response)
            return result
    except HTTPError as error:
        if error.code == 409:
            raise HTTPException(
                409, "Local runtime is busy or belongs to another organization"
            ) from None
        raise HTTPException(
            503, "Local runtime authentication or operation failed. Recreate the stack."
        ) from None
    except (URLError, TimeoutError, OSError):
        raise HTTPException(
            503,
            "Local runtime unavailable. Check local-agent-launcher, then retry.",
        ) from None
