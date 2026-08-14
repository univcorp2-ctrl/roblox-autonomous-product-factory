from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Product:
    name: str
    repo_url: str
    branch: str
    build_commands: tuple[str, ...]
    artifact: str
    require_studio_mcp: bool = True
    opencloud_smoke_script: str | None = None


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    reason: str
    evidence: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ReleaseResult:
    product: str
    state: str
    gates: tuple[GateResult, ...]
    artifact_path: Path | None = None
    published_version: str | None = None
