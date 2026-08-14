from __future__ import annotations

from pathlib import Path

from .process import run


def sync_repo(repo_url: str, branch: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not (target / ".git").exists():
        run(f'git clone --depth 1 --branch "{branch}" "{repo_url}" "{target}"', target.parent)
        return
    run("git fetch --prune origin", target)
    run(f'git checkout "{branch}"', target)
    run(f'git reset --hard "origin/{branch}"', target)
