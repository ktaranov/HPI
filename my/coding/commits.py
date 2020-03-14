"""
Git commits data: crawls filesystem
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import List, NamedTuple, Optional, Dict, Any, Iterator

from ..common import PathIsh, LazyLogger
from mycfg import commits as config

# pip3 install gitpython
import git # type: ignore
from git.repo.fun import is_git_dir, find_worktree_git_dir # type: ignore


log = LazyLogger('my.commits', level='info')


_things = {
    *config.emails,
    *config.names,
}


def by_me(c) -> bool:
    actor = c.author
    if actor.email in config.emails:
        return True
    if actor.name in config.names:
        return True
    aa = f"{actor.email} {actor.name}"
    for thing in _things:
        if thing in aa:
            # TODO this is probably useless
            raise RuntimeError("WARNING!!!", actor, c, c.repo)
    return False


class Commit(NamedTuple):
    commited_dt: datetime
    authored_dt: datetime
    message: str
    repo: str # TODO put canonical name here straightaway??
    sha: str
    ref: Optional[str]=None
        # TODO filter so they are authored by me

    @property
    def dt(self) -> datetime:
        return self.commited_dt


# TODO not sure, maybe a better idea to move it to timeline?
def fix_datetime(dt) -> datetime:
    # git module got it's own tzinfo object.. and it's pretty weird
    tz = dt.tzinfo
    assert tz._name == 'fixed'
    offset = tz._offset
    ntz = timezone(offset)
    return dt.replace(tzinfo=ntz)


def _git_root(git_dir: PathIsh) -> Path:
    gd = Path(git_dir)
    if gd.name == '.git':
        return gd.parent
    else:
        return gd # must be bare


def _repo_commits_aux(gr: git.Repo, rev: str) -> Iterator[Commit]:
    # without path might not handle pull heads properly
    for c in gr.iter_commits(rev=rev):
        if by_me(c):
            repo = str(_git_root(gr.git_dir))

            yield Commit(
                commited_dt=fix_datetime(c.committed_datetime),
                authored_dt=fix_datetime(c.authored_datetime),
                message=c.message.strip(),
                repo=repo,
                sha=c.hexsha,
                ref=rev,
            )


def repo_commits(repo: PathIsh):
    gr = git.Repo(str(repo))
    for r in gr.references:
        yield from _repo_commits_aux(gr=gr, rev=r.path)


def canonical_name(repo: Path) -> str:
    # TODO could determine origin?
    if repo.match('github/repositories/*/repository'):
        return repo.parent.name
    else:
        return repo.name
        # if r.name == 'repository': # 'repository' thing from github..
        #     rname = r.parent.name
        # else:
        #     rname = r.name
    # if 'backups/github' in repo:
    #     pass # TODO 


# TODO could reuse in clustergit?..
def git_repos_in(roots: List[Path]) -> List[Path]:
    from subprocess import check_output
    outputs = check_output([
        'fdfind',
        # '--follow', # right, not so sure about follow... make configurable?
        '--hidden',
        '--full-path',
        '--type', 'f',
        '/HEAD', # judging by is_git_dir, it should always be here..
        *roots,
    ]).decode('utf8').splitlines()
    candidates = set(Path(o).resolve().absolute().parent for o in outputs)

    # exclude stuff within .git dirs (can happen for submodules?)
    candidates = {c for c in candidates if '.git' not in c.parts[:-1]}

    candidates = {c for c in candidates if is_git_dir(c)}

    repos = list(sorted(map(_git_root, candidates)))
    return repos


def repos():
    return git_repos_in(config.roots)


# TODO cachew for all commits?
def commits() -> Iterator[Commit]:
    for r in repos():
        log.info('processing %s', r)
        yield from repo_commits(r)


def print_all():
    for c in commits():
        print(c)


# TODO enforce read only? although it doesn't touch index
