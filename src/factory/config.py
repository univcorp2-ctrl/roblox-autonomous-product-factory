from __future__ import annotations

import tomllib
from pathlib import Path

from .models import Product


def load_product(path: Path) -> Product:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Product(
        name=data["product"]["name"],
        repo_url=data["product"]["repo_url"],
        branch=data["product"].get("branch", "main"),
        build_commands=tuple(data["build"].get("commands", [])),
        artifact=data["build"]["artifact"],
        require_studio_mcp=bool(data.get("gates", {}).get("require_studio_mcp", True)),
        opencloud_smoke_script=data.get("gates", {}).get("opencloud_smoke_script"),
    )
