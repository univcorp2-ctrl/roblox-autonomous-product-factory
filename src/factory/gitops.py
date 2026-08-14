from __future__ import annotations

from pathlib import Path

from .process import CommandFailed, run


def sync_repo(repo_url: str, branch: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not (target / ".git").exists():
        run(f'git clone --depth 1 --branch "{branch}" "{repo_url}" "{target}"', target.parent)
        return

    run("git fetch --prune origin", target)
    run(f'git checkout "{branch}"', target)

    # Protect edits to tracked source files. Generated build artifacts are commonly
    # untracked and must not stop the factory. Git itself will refuse a fast-forward
    # if an untracked file would actually be overwritten by the incoming commit.
    dirty_tracked = run("git status --porcelain --untracked-files=no", target).strip()
    if dirty_tracked:
        raise CommandFailed(
            "tracked working-tree changes detected; refusing to overwrite them. "
            "Archive or commit the local work before autonomous sync.\n" + dirty_tracked[:4000]
        )
    run(f'git merge --ff-only "origin/{branch}"', target)
