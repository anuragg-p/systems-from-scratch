"""git: the capstone (module 10). T is track.py.

Every repository a test touches is a new directory under the test's own scratch directory (t.tmp,
made by tempfile, outside this checkout); ours() and real() refuse any other. The real git is
found once, by absolute path, in fixed places (never through PATH, which could hold a bin/), and
always runs with -C on that directory, GIT_CEILING_DIRECTORIES just above it (so it never looks
further up), no global or system config (GIT_CONFIG_GLOBAL=/dev/null, GIT_CONFIG_NOSYSTEM),
HOME in the scratch directory, gc and maintenance off, and a made-up author and committer with
fixed dates. Nothing reads or uses the machine's own git identity or config.

    REAL_GIT            the real git's path, or None (then the tests that need it fail, saying so)
    real_version()      "git version 2.50.1 (Apple Git-155)"
    new_repo(t, name)   an empty directory for a repository, in t.tmp: its path
    ours(t, repo, args, env=None, input=None, check=True, date=None)
                        bin/git -C repo args, with the made-up identity (and date, "SECONDS +HHMM")
    real(t, repo, args, env=None, input=None, check=True, date=None)
                        the real git -C repo args, as above
    write(repo, path, data)
                        a file of the work tree, its directories made
    gen_repo(t, shape, n, seed=1)
                        (path, {branch: name}): a repository of tools/git/gen.py's shape
    stats(r)            T.stats of a run's stderr
    objects(repo)       the names of every loose object in repo
    parse_index(repo)   the index, read by this file's own reader: (version, [(mode, hex, path)], tree)
                        where tree is the TREE extension as [(path, count, subtrees, hex or None)]
    zlib_object(repo, hex)
                        an object's bytes, header and all, as Python's zlib reads its file
"""

import hashlib
import importlib.util
import os
import re
import struct
import subprocess
import zlib

from harness.core import Fail

PROGRAMS = {"git": "10.01"}
FILES_FROM = {"tools/git/tool.mk": "10.01", "tools/git/git.h": "10.01", "lib/sha1sum.h": "10.01",
              "lib/zframe.h": "10.01", "tools/git/gen.py": "10.02"}
HIDDEN = ["tools/git/NOTES.md", "tools/git/NOTICE.txt"]
UPSTREAM = [
    {"name": "git",
     "url": "https://github.com/git/git",
     "licence": "GPL-2.0",
     "owes": "No code. Our git is written from git's documented formats (gitformat-index, the Pro Git "
             "internals chapter) and is checked against theirs: git fsck --strict passes on what ours "
             "writes, their log, cat-file, ls-files and status agree with ours, ours reads what theirs "
             "writes, and git apply takes our diff.",
     "derived": False},
    {"name": "SHA-1 (FIPS 180-4) and the zlib format (RFC 1950)",
     "url": "https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf",
     "licence": "Free to copy with the notice kept (RFC 1950's own licence); FIPS 180-4 is a U.S. government work",
     "owes": "No code. lib/sha1sum.c is written from FIPS 180-4 and lib/zframe.c from RFC 1950.",
     "derived": False,
     "also": [("RFC 1950: ZLIB Compressed Data Format Specification", "https://www.rfc-editor.org/rfc/rfc1950"),
              ("RFC 3174: US Secure Hash Algorithm 1", "https://www.rfc-editor.org/rfc/rfc3174")]},
]

TRACK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _find_real():
    for p in ("/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git", "/bin/git"):
        if os.path.isfile(p) and os.access(p, os.X_OK):
            rp = os.path.realpath(p)
            if not rp.startswith(os.path.realpath(TRACK) + os.sep):
                return p
    return None


REAL_GIT = _find_real()

IDENTITY = {"GIT_AUTHOR_NAME": "A U Thor", "GIT_AUTHOR_EMAIL": "author@example.com",
            "GIT_COMMITTER_NAME": "C O Mitter", "GIT_COMMITTER_EMAIL": "committer@example.com"}
DATE = "1700000000 +0000"

REAL_CONFIG = ["-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "init.defaultBranch=main",
               "-c", "core.autocrlf=false", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
               "-c", "core.quotePath=true", "-c", "feature.manyFiles=false", "-c", "index.skipHash=false",
               "-c", "commit.gpgSign=false", "-c", "color.ui=false", "-c", "diff.noprefix=false",
               "-c", "diff.mnemonicPrefix=false", "-c", "log.decorate=false", "-c", "core.abbrev=7"]


def _scratch(t):
    return t.tmp if hasattr(t, "tmp") else t


def _inside(t, repo):
    """repo must be a directory under the scratch directory: never this checkout, never anything else."""
    tmp = os.path.realpath(_scratch(t))
    rp = os.path.realpath(repo)
    if not rp.startswith(tmp + os.sep) or rp.startswith(os.path.realpath(TRACK) + os.sep):
        raise Fail(f"refusing to run git on {repo}: not a repository of this test's own scratch directory")
    return rp


def new_repo(t, name):
    path = os.path.join(_scratch(t), name)
    os.makedirs(path)
    return path


def write(repo, path, data):
    p = os.path.join(repo, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data.encode() if isinstance(data, str) else data)
    return p


def ours(t, repo, args, env=None, input=None, check=True, date=None):
    _inside(t, repo)
    e = dict(IDENTITY)
    e["GIT_AUTHOR_DATE"] = e["GIT_COMMITTER_DATE"] = date or DATE
    e.update(env or {})
    root = t if isinstance(t, str) else t.root
    return T.run(root, "git", ["-C", repo] + list(args), input=input, env=e, check=check)


def _real_env(t, repo, date, extra):
    home = os.path.join(_scratch(t), "home-for-real-git")
    os.makedirs(home, exist_ok=True)
    e = {"PATH": "/usr/bin:/bin", "HOME": home, "XDG_CONFIG_HOME": home, "LC_ALL": "C", "TZ": "UTC",
         "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
         "GIT_CEILING_DIRECTORIES": os.path.dirname(os.path.realpath(repo)), "GIT_TERMINAL_PROMPT": "0",
         "GIT_PAGER": "cat", "PAGER": "cat", "GIT_AUTHOR_DATE": date or DATE, "GIT_COMMITTER_DATE": date or DATE}
    e.update(IDENTITY)
    e.update(extra or {})
    return e


def real(t, repo, args, env=None, input=None, check=True, date=None):
    if REAL_GIT is None:
        raise Fail("no git on this machine to check against (looked in /usr/bin, /usr/local/bin, /opt/homebrew/bin)")
    rp = _inside(t, repo)
    argv = [REAL_GIT, "-C", rp] + REAL_CONFIG + [str(a) for a in args]
    if isinstance(input, str):
        input = input.encode()
    try:
        r = subprocess.run(argv, input=input, stdin=None if input is not None else subprocess.DEVNULL,
                           capture_output=True, env=_real_env(t, rp, date, env), timeout=300)
    except subprocess.TimeoutExpired:
        raise Fail(f"the real git {' '.join(args)} did not finish")

    class R:
        pass
    res = R()
    res.raw, res.rc = r.stdout, r.returncode
    res.out = r.stdout.decode("utf-8", "surrogateescape")
    res.err = r.stderr.decode("utf-8", "surrogateescape")
    if check and r.returncode != 0:
        raise Fail(f"the real git {' '.join(str(a) for a in args)}: exit {r.returncode}\n{res.out[-1500:]}{res.err[-1500:]}")
    return res


_version = []


def real_version():
    if not _version:
        if REAL_GIT is None:
            return "no real git"
        r = subprocess.run([REAL_GIT, "--version"], capture_output=True,
                           env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"})
        _version.append(r.stdout.decode().strip())
    return _version[0]


def stats(r):
    return T.stats(r.err)


_gen = []


def gen_repo(t, shape, n, seed=1):
    if not _gen:
        spec = importlib.util.spec_from_file_location("dsa_git_gen", os.path.join(TRACK, "tools", "git", "gen.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _gen.append(mod)
    path = os.path.join(_scratch(t), f"{shape}-{n}-{seed}")
    os.makedirs(path)
    _inside(t, path)
    return path, _gen[0].make_repo(shape, n, path, seed)


def objects(repo):
    out = []
    base = os.path.join(repo, ".git", "objects")
    for d in sorted(os.listdir(base)):
        if re.fullmatch(r"[0-9a-f]{2}", d):
            out += [d + f for f in sorted(os.listdir(os.path.join(base, d))) if re.fullmatch(r"[0-9a-f]{38}", f)]
    return out


def zlib_object(repo, hexname):
    with open(os.path.join(repo, ".git", "objects", hexname[:2], hexname[2:]), "rb") as f:
        return zlib.decompress(f.read())


def object_name(kind, data):
    return hashlib.sha1(b"%s %d\x00" % (kind, len(data)) + data).hexdigest()


def parse_index(repo):
    """The index, read here independently of ours: (version, entries, tree), checked."""
    with open(os.path.join(repo, ".git", "index"), "rb") as f:
        d = f.read()
    if d[:4] != b"DIRC" or hashlib.sha1(d[:-20]).digest() != d[-20:]:
        raise Fail("the index: not DIRC, or its checksum is wrong")
    version, count = struct.unpack(">II", d[4:12])
    pos, entries = 12, []
    for _ in range(count):
        mode = struct.unpack(">I", d[pos + 24:pos + 28])[0]
        oid = d[pos + 40:pos + 60].hex()
        flags = struct.unpack(">H", d[pos + 60:pos + 62])[0]
        name = d[pos + 62:d.index(b"\x00", pos + 62)]
        if (flags & 0xfff) != min(len(name), 0xfff):
            raise Fail(f"the index: {name!r} has length {flags & 0xfff} in its flags")
        step = (62 + len(name) + 8) & ~7
        if d[pos + 62 + len(name):pos + step] != b"\x00" * (step - 62 - len(name)):
            raise Fail(f"the index: {name!r} is not padded with NULs")
        entries.append((mode, oid, name.decode("utf-8", "surrogateescape")))
        pos += step
    tree = None
    while pos < len(d) - 20:
        sig, n = d[pos:pos + 4], struct.unpack(">I", d[pos + 4:pos + 8])[0]
        body = d[pos + 8:pos + 8 + n]
        if sig == b"TREE":
            tree, at = [], 0

            def one(prefix, at):
                nul = body.index(b"\x00", at)
                name = body[at:nul].decode()
                nl = body.index(b"\n", nul)
                count, subs = (int(x) for x in body[nul + 1:nl].split(b" "))
                at = nl + 1
                h = None
                if count >= 0:
                    h = body[at:at + 20].hex()
                    at += 20
                path = prefix + name + ("/" if name else "")
                tree.append((path, count, subs, h))
                for _ in range(subs):
                    at = one(path, at)
                return at
            if one("", 0) != len(body):
                raise Fail("the index: its TREE extension has bytes after its entries")
        pos += 8 + n
    return version, entries, tree


# ---------------------------------------------------------------- the project at each lesson

COMMANDS = [("10.01", "init, hash-object, cat-file"), ("10.02", "add, ls-files, write-tree, ls-tree"),
            ("10.03", "commit-tree, commit, log, branch"), ("10.04", "diff, merge-base")]


def _have(k):
    from harness.core import lesson_key
    return ", ".join(c for lid, c in COMMANDS if lesson_key(lid) <= k)


ENV = ("GIT_AUTHOR_NAME='A U Thor' GIT_AUTHOR_EMAIL=author@example.com GIT_AUTHOR_DATE='1700000000 +0000' "
       "GIT_COMMITTER_NAME='C O Mitter' GIT_COMMITTER_EMAIL=committer@example.com "
       "GIT_COMMITTER_DATE='1700000000 +0000'")


def timeline_steps(k):
    """In a directory of its own, made with mktemp and passed with -C: never the project's."""
    if k < (10, 1):
        return []
    have = _have(k)
    g = 'bin/git -C "$GR"'
    steps = [T.sh_step('GR=$(mktemp -d "${TMPDIR:-/tmp}/dsa-git.XXXXXX") && mkdir "$GR/repo" && GR="$GR/repo" && '
                       f'{g} init -q && printf "hello\\n" > "$GR/hello.txt" && {g} hash-object -w hello.txt',
                       "ce013625030ba8dba906f756967f9e9ca394464a\n"),
             T.sh_step(f'{g} cat-file -p ce01362; {g} cat-file -t ce01362; {g} cat-file -s ce01362',
                       "hello\nblob\n6\n"),
             T.sh_step(f'{g} cat-file -p 0123456', "git: 0123456 is the start of no object's name here\n", 2),
             T.sh_step('mkdir "$GR/inside" && bin/git -C "$GR/inside" cat-file -t ce01362',
                       "git: not a git repository: there is no .git here (this git looks only in the directory "
                       "it is given, never in the ones above it)\n", 2),
             T.sh_step(f'{g} init', regex=r"git: \./\.git is there already: this git does not make a repository "
                                          r"twice\r?\n", status=2),
             T.sh_step(f'{g} frobnicate', f"git: no command 'frobnicate' (have: {have})\n", 2)]
    if k < (10, 2):
        steps.append(T.sh_step(f'{g} add hello.txt', f"git: no command 'add' (have: {have})\n", 2))
    else:
        steps += [T.sh_step(f'mkdir -p "$GR/d" && printf "deep\\n" > "$GR/d/e.txt" && {g} add . && {g} ls-files -s',
                            "100644 4cdb2265d30204be5463b38174b2e8e717982405 0\td/e.txt\n"
                            "100644 ce013625030ba8dba906f756967f9e9ca394464a 0\thello.txt\n"),
                  T.sh_step(f'{g} write-tree', "fe4afc2c60ebbe9ffedbcd4a540bd5ba01813af9\n"),
                  T.sh_step(f'{g} ls-tree fe4afc2',
                            "040000 tree 374baa59ef697b833805ef5c59c67c13195ffe55\td\n"
                            "100644 blob ce013625030ba8dba906f756967f9e9ca394464a\thello.txt\n"),
                  T.sh_step(f'{g} write-tree --algo=bogo', "git: no --algo 'bogo' (have: all, cache)\n", 2)]
    if (10, 2) <= k < (10, 3):
        steps.append(T.sh_step(f'{g} commit -m first', f"git: no command 'commit' (have: {have})\n", 2))
    if k >= (10, 3):
        steps += [T.sh_step(f'{ENV} {g} commit -m first',
                            "[main (root-commit) 82764a0] first\n"),
                  T.sh_step(f'printf "deep\\nchanged\\n" > "$GR/d/e.txt" && {g} add d && '
                            f'{ENV.replace("1700000000", "1700000060")} {g} commit -q -m second && {g} log --oneline',
                            regex=r"[0-9a-f]{7} second\r?\n82764a0 first\r?\n"),
                  T.sh_step(f'{g} log --algo=bogo', "git: no --algo 'bogo' (have: list, heap)\n", 2),
                  T.sh_step(f'{g} log HEAD~5', regex=r"git: HEAD~5: 82764a0 has 0 parents, so no parent 1\r?\n",
                            status=2)]
    if (10, 3) <= k < (10, 4):
        steps.append(T.sh_step(f'{g} diff HEAD~1 HEAD', f"git: no command 'diff' (have: {have})\n", 2))
    if k >= (10, 4):
        steps += [T.sh_step(f'{g} diff HEAD~1 HEAD',
                            regex=r"diff --git a/d/e\.txt b/d/e\.txt\r?\nindex 4cdb226\.\.06654ae 100644\r?\n"
                                  r"--- a/d/e\.txt\r?\n\+\+\+ b/d/e\.txt\r?\n@@ -1 \+1,2 @@\r?\n deep\r?\n"
                                  r"\+changed\r?\n"),
                  T.sh_step(f'{g} merge-base HEAD HEAD~1', regex=r"82764a0[0-9a-f]{33}\r?\n"),
                  T.sh_step(f'{g} merge-base --algo=bogo HEAD HEAD', "git: no --algo 'bogo' (have: rewalk, paint)\n", 2)]
    steps.append(T.sh_step('rm -rf "${GR%/repo}"', ""))
    return steps


def timeline_after(root, k):
    """A repository ours writes, as far as the lesson goes, checked by the real git."""
    if k < (10, 1):
        return None
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="dsa-git-after-")
    try:
        repo = new_repo(tmp, "repo")
        e = dict(IDENTITY, GIT_AUTHOR_DATE=DATE, GIT_COMMITTER_DATE=DATE)
        T.run(root, "git", ["-C", repo, "init", "-q"], env=e)
        book = T.data(root, "book.txt")
        shutil.copyfile(book, os.path.join(repo, "book.txt"))
        name = T.run(root, "git", ["-C", repo, "hash-object", "-w", "book.txt"], env=e).out.strip()
        with open(book, "rb") as f:
            data = f.read()
        if name != object_name(b"blob", data):
            raise Fail(f"git hash-object on the book: {name}")
        if real(tmp, repo, ["cat-file", "-p", name]).raw != data:
            raise Fail("the real git does not read the book back from our object")
        note = f"git: the book as {name[:7]}, read back by the real git"
        if k >= (10, 2):
            write(repo, "a/b/c.txt", "c\n")
            T.run(root, "git", ["-C", repo, "add", "."], env=e)
            tree = T.run(root, "git", ["-C", repo, "write-tree"], env=e).out.strip()
            theirs = real(tmp, repo, ["write-tree"]).out.strip()
            if tree != theirs:
                raise Fail(f"write-tree: ours {tree}, the real git's {theirs}")
            note += "; the same tree as the real git's"
        if k >= (10, 3):
            T.run(root, "git", ["-C", repo, "commit", "-q", "-m", "the book"], env=e)
            if real(tmp, repo, ["status", "--porcelain"]).out != "":
                raise Fail("the real git status is not clean after our add and commit")
            if T.run(root, "git", ["-C", repo, "log"], env=e).out != real(tmp, repo, ["log"]).out:
                raise Fail("git log: ours and the real git's differ")
            note += ", log and a clean status"
        real(tmp, repo, ["fsck", "--strict"])
        return note + "; fsck --strict passes"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
