import json

import pytest


def debug_response(response):
    if getattr(pytest, "DEBUG", False):
        try:
            data = response.json()
        except Exception:
            data = response.content.decode()

        print(
            json.dumps(
                {
                    "status": response.status_code,
                    "data": data,
                },
                ensure_ascii=False,
                indent=4,
            )
        )