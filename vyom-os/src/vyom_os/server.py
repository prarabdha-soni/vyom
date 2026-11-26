"""``vyom-os-api``: serve the Vyom OS API with uvicorn."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "vyom_os.api:create_app_from_env",
        factory=True,
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=int(os.environ.get("API_PORT", "8000")),
        reload=False,
        proxy_headers=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
