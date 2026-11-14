# Module 10, the capstone git: notes for the lesson writers

Everything here was run on the reference code: Apple M4 Pro (48 GB), macOS
26.6.2, Apple clang 21.0.0, Python 3.12, and the real git as Apple ships it,
`git version 2.50.1 (Apple Git-155)` (/usr/bin/git; Homebrew's 2.49.0 gave
the same answers in the early runs); and checked on Linux: Docker
`dsa-grep-linux` (Debian 13.7, aarch64, the same Mac), gcc 14.2.0, GNU Make
4.4.1, Python 3.13.5, `git version 2.47.3`. Times are the best of three
(Python's perf_counter around the whole process, so they include starting
it), on a Mac shared with other jobs (load average about 7): read them as
"about". The counts (DS_STATS) are the same on every run and both systems.
Every "break it" below was made on the project as `./learn files dsa --at
NN.LL` writes it, with that one change, and its output is pasted as it came
(paths shortened to `r/`).

Written from FIPS 180-4 (SHA-1), RFC 1950 (zlib), gitformat-index(5) and Pro
Git chapter 10.2, fetched 2026-11-14 and read; no code from git or anywhere
else. NOTICE.txt here is the text for the top-level NOTICE.

## What is where, and what each lesson stands on

```
lib/sha1sum.h, .c   10.01  SHA-1, FIPS 180-4 (named so as not to hide any system sha1.h)
lib/zframe.h, .c    10.01  the zlib format (RFC 1950): header, Adler-32, around 09's raw DEFLATE
                           (named so as not to hide the system's zlib.h)
tools/git/git.h     10.01  everything the parts share (FILES_FROM 10.01; later parts are @from)
tools/git/repo.c    10.01  finding the repository (the safety rules), config, whole files, tracing
tools/git/object.c  10.01  objects: name, store, read and check; names typed by a person
tools/git/git.c     10.01  the commands; each lesson's are @from blocks and table lines
tools/git/tree.c    10.02  git's order, tree objects read and checked, write-tree with the cache
tools/git/index.c   10.02  the index (version 2), its TREE extension, add
tools/git/refs.c    10.03  HEAD, branches, packed-refs, NAME~N, NAME^N, NAME^{tree}
tools/git/commit.c  10.03  commits read and written, log (list, heap); commit_get is 10.04's
tools/git/compare.c 10.04  diff of two trees (all, skip), the patch, merge-base (rewalk, paint)
tools/git/gen.py    10.02  test repositories of a given shape and size (below)
tools/git/tool.mk   10.01  bin/git; LIB += sha1sum.o zframe.o; objects added per lesson
tests/tools/git.py         the fixtures (the real git, run safely), timeline steps, UPSTREAM
```

Which earlier piece each lesson uses (for the track's map):

| lesson | library piece, and the lesson that built it | what git does with it |
|---|---|---|
| 10.01 | lib/sha1sum.c, lib/zframe.c (new); `deflate_raw` 09.04 (with lz77 09.03, huffman 09.01, heap 02.04); `inflate_raw` 09.02; Array 01.01 | names objects; stores them as zlib streams; every buffer is an Array |
| 10.02 | `sort_merge` 02.02; Array 01.01; SHA-1, zlib, objects 10.01 | add sorts the paths a directory walk finds, then merges them into the index (two sorted lists) |
| 10.03 | Heap 02.04; Table 01.02/01.03 (FNV-1a, doubling); Array 01.01 | log's queue (newest first) and its set of names seen; `--algo=list` the same with Arrays |
| 10.04 | `diff_text`, `diff_myers`, `diff_unified` 06.01-06.03 (and `diff_number`'s Table 01.02); Heap 02.04; Table 01.02 | a changed file's patch; merge-base's walk by date; one Commit per name (`commit_get`) |

`branch` (10.03) lists branches with `sort_merge` too. There is no binary
search: add merges two sorted lists instead of searching the index once per
file. No piece of the library was changed; nothing in lib/diff.h, inflate.h
or deflate.h was missing.

Regions (`@build`), by lesson: 10.01 `compress`, `sha1_update`, `sha1_final`
(sha1sum.c), `zframe_adler32`, `zframe_pack`, `zframe_unpack` (zframe.c),
`object_name`, `object_write`, `object_read` (object.c), `repo_init`
(repo.c), `cmd_hash_object`, `cmd_cat_file` (git.c). 10.02 `tree_cmp`,
`tree_entries`, `build` (tree.c), `index_read`, `index_write`, `index_add`
(index.c). 10.03 `ref_read`, `ref_write`, `rev_parse` (refs.c), `commit_read`,
`commit_create`, `walk_heap`, `walk_list` (commit.c). 10.04 `walk_skip`,
`flatten`, `walk_all`, `show_change`, `paint`, `rewalk` (compare.c). A cut
region prints, for example, `git: 10.02: one directory's tree: its
subdirectories' trees first, then its own not written yet` and exits 3.

## The tool at each lesson

```
10.01  git [-C DIR] init [-q] [-b BRANCH] [DIR]
                    hash-object [-w] [-t TYPE] [--stdin] [FILE ...]
                    cat-file (-t | -s | -e | -p) NAME | cat-file TYPE NAME
10.02  + add PATH ..., ls-files [-s], write-tree [--algo=all|cache], ls-tree [-r] [-t] NAME
10.03  + commit-tree TREE [-p P ...] [-m MSG ...], commit [-q] [--allow-empty] [--algo=all|cache] -m MSG,
         log [--algo=list|heap] [--oneline] [-n N | -N] [NAME ...], branch [NAME [START]]
10.04  + diff [--algo=all|skip] [-U N] NAME NAME, merge-base [--algo=rewalk|paint] [--all] NAME NAME
```

A NAME is 40 hexadecimal digits or the first 4 or more of them; from 10.03
also HEAD, a branch or tag, and `~N`, `^N`, `^{tree}` after any name. Before
its lesson a command is an ordinary error, status 2: at 10.01 `git: no
command 'add' (have: init, hash-object, cat-file)`; so is a bad --algo:
`git: no --algo 'bogo' (have: list, heap)`. At 10.01 `cat-file -p` of a tree
says `git: NAME is a tree, which this git cannot show` (an @else line). Exit
statuses: 0; 1 for `cat-file -e` of a missing object, `merge-base` with no
common ancestor, `commit` with nothing to commit; 2 for every error. init's
branch is `main` (the real git's default is still `master` unless
init.defaultBranch is set; the fixtures set it to main).

Not done, each an ordinary error or simply absent: status, checkout, merge,
tags (an annotated tag object is read by cat-file, never made), .gitignore
(add takes every file but .git), reflogs, config other than .git/config,
dates other than "SECONDS +HHMM" (with or without @), rename detection
(compare with `git diff --no-renames`), packed objects, SHA-256 objects,
index version 4, a split or sparse index. Version 3 indexes are read.

## Safety: how this git is kept off real repositories

The course's own checkout is a git repository (with loose objects and no
packs, so "packed repositories are refused" alone would not protect it), and
the other agents' worktrees are in it. So:

- **Never walks up.** repo_open() looks only at `.git` in the directory
  given (-C DIR, or the current one). Run in a/b/c inside a repository, it
  says `git: not a git repository: there is no .git here (this git looks only
  in the directory it is given, never in the ones above it)`. The real git
  would use the first .git above. This is the deliberate difference to say in
  10.01. `./learn run dsa --at 10.0X -- git ...` runs in build/at/dsa/10.0X/,
  which has no .git, so a reader's command there can never reach the
  course's own repository; `git -C demo init` there makes a repository of
  its own inside the ignored build/ directory.
- **No .git file.** A linked worktree or submodule has a .git *file*: refused
  (`git: .git is a file, not a directory: a linked worktree or a submodule,
  which this git does not open`). That is what this agent's own worktree has.
- **Writes only to its own repositories.** init writes `[dsa] ours = true`
  into .git/config; every command that writes (hash-object -w, add,
  write-tree, commit-tree, commit, branch, and object_write and ref_write
  themselves) dies without it: `git: add: this git changes only repositories
  its own init made (.git/config has no "[dsa] ours = true"); it reads this
  one, but will not write to it`. It reads any repository of loose objects.
  init refuses a directory that has a .git already.
- **No environment but the identity.** GIT_DIR, GIT_WORK_TREE,
  GIT_INDEX_FILE and the rest are ignored; only GIT_AUTHOR_* and
  GIT_COMMITTER_* (name, email, date) are read, else user.name and user.email
  from .git/config, else an error. No global, system or ~/.gitconfig is read,
  so the machine's identity never enters a commit.
- **The tests** (tests/tools/git.py) run every repository in the test's own
  tempfile directory and refuse any other path (`_inside`). The real git is
  found once by absolute path in fixed places (/usr/bin, /usr/local/bin,
  /opt/homebrew/bin: never PATH) and always runs with `-C <that directory>`,
  GIT_CEILING_DIRECTORIES just above it, GIT_CONFIG_GLOBAL=/dev/null,
  GIT_CONFIG_SYSTEM=/dev/null, GIT_CONFIG_NOSYSTEM=1, HOME in the scratch
  directory, a made-up author and committer with fixed dates, and `-c` for
  gc.auto=0, maintenance.auto=false and a dozen more neutral settings. The
  timeline makes its repository with `mktemp -d` under $TMPDIR, passes it
  with -C, checks that a directory inside it is not taken for a repository,
  and removes it at the end.

## DS_STATS and DS_TRACE

DS_STATS=1, git's own lines (each printed once used; git's first):

```
stats: git: objects hashed H, written W, already there E, read R
stats: index: entries read R, entries written W, files hashed H
stats: write-tree: trees built B, from the cache C
stats: log: commits C, queue scans Q, seen probes P
stats: diff: trees read T, blobs read B, entries compared E, subtrees skipped S, blobs skipped K, bytes compared Y, files changed F
stats: merge-base: commits visited V, walks W
stats: sha1: blocks B, bytes N          (B counts the padding's blocks: (bytes + 8) / 64 + 1 for one object)
stats: zlib: packed P, unpacked U, bytes checked B     (B: bytes through Adler-32)
```

plus the library's own lines (array, table, sort, heap, inflate, deflate,
lz77, huffman, myers). Note that `heap` in a command that writes objects
includes huffman's use of it (deflate builds codes with the heap); log and
merge-base write nothing, so their heap line is their own.

DS_TRACE=1 prints git's own steps on stderr; the library's (inflate would
print every byte of every object) only with DS_TRACE=all. The format, one
line per step:

```
trace: object: blob of 6 bytes is ce/013625030ba8dba906f756967f9e9ca394464a: written, 21 bytes compressed
trace: object: blob of 6 bytes is ce/013625030ba8dba906f756967f9e9ca394464a: already there
trace: object: read commit 06e83fd206ce7c613ad1c81876e562db21960e96, 270 bytes
trace: index: add d/e/f.txt 100644 4cdb226            (also "update", "remove")
trace: index: d/e/f.txt changed: the cached tree of d/e/ is gone      (one per directory above, top first: "/")
trace: tree: d/e/ (1 entry, 1 file under it): cd21a79, built          (bottom up: children before parents)
trace: tree: b/ (1 file under it): 1933da3, from the cache
trace: ref: refs/heads/main is now 04edf9e
trace: log: pop 04edf9e 1700000060; heap: 790a49c 1700000030          (after each pop: the heap's array, in order)
trace: log: push 4531ec6 1700000000; heap: 790a49c 1700000030, 4531ec6 1700000000
trace: log: 4531ec6, parent of 790a49c: seen already
trace: diff: b/: 1933da3 on both sides: the same, passed over
trace: diff: d/: d61f885 and 7ecc4e4: different, opened
trace: diff: d/e/f.txt: 4cdb226 and 06654ae: changed
trace: diff: x/: only in the first                                     (or "second")
trace: merge-base: pop 4531ec6 1700000000, reached by 1 and 2, stale
trace: merge-base: 790a49c 1700000030 is not in the first's history   (--algo=rewalk)
```

Names in traces are the first 7 digits, not checked for uniqueness; dates
are the committer's seconds. The heap line lists `h->items` as stored
(v[0] is the top; the children of i are 2i+1 and 2i+2), so a figure can draw
the tree. The tests pin the object, index, tree, log and merge-base formats.

## The example used below

A repository made with fixed dates (author A U Thor, committer C O Mitter,
both author@example.com style), so every name below is reproducible:
hello.txt ("hello\n"), "b c" ("space\n"), b/c ("c\n"), d/e/f.txt ("deep\n"),
d/g.txt ("g\n"); commit "first" at 1700000000; d/e/f.txt gets a line
"changed", commit "second" at 1700000060; a commit "on a side branch" on
first at 1700000030 (commit-tree, branch side); "Merge side" of the two at
1700000120.

## 10.01 Objects: a hash is a name

The code: SHA-1 from FIPS 180-4 (`compress`: 16 words to 80, 80 rounds of
Ch/Parity/Maj/Parity with the four constants; `sha1_update` takes bytes and
compresses each block as it fills; `sha1_final` pads with 0x80, zeros, and
the length in bits big-endian). The zlib format (`zframe_pack`: 0x78, FLG
with FLEVEL 0 and the check bits that make CMF*256+FLG a multiple of 31,
`deflate_raw` with gzip -1's search, the Adler-32 big-endian;
`zframe_unpack`: checks the header, `inflate_raw`, then the sum). Objects:
`object_name` hashes "blob 6\0" and the bytes; `object_write` names it, and if
.git/objects/ce/0136... exists it stops (stored once), else compresses and
writes it through a temporary file renamed into place, read-only;
`object_read` inflates it, reads the header, checks the size, and hashes the
bytes again: an object whose bytes are not its name is "damaged".

```
$ bin/git -C demo init
Initialized empty Git repository in .../demo/.git/
$ printf 'hello\n' > demo/hello.txt
$ DS_STATS=1 DS_TRACE=1 bin/git -C demo hash-object -w hello.txt
ce013625030ba8dba906f756967f9e9ca394464a
trace: object: blob of 6 bytes is ce/013625030ba8dba906f756967f9e9ca394464a: written, 21 bytes compressed
stats: git: objects hashed 1, written 1, already there 0, read 0
stats: sha1: blocks 1, bytes 13
stats: array: pushes 69, grows 9, moves 40
stats: zlib: packed 1, unpacked 0, bytes checked 13
stats: deflate: stored blocks 0, fixed blocks 1, dynamic blocks 0, bits out 120
...
$ DS_STATS=1 bin/git -C demo hash-object -w hello.txt
ce013625030ba8dba906f756967f9e9ca394464a
stats: git: objects hashed 1, written 0, already there 1, read 0
stats: sha1: blocks 1, bytes 13
$ ls demo/.git/objects/ce
013625030ba8dba906f756967f9e9ca394464a
$ od -An -tx1 demo/.git/objects/ce/013625030ba8dba906f756967f9e9ca394464a
 78 01 4b ca c9 4f 52 30 63 c8 48 cd c9 c9 e7 02 00 1d c5 04 14
$ bin/git -C demo cat-file -t ce01; bin/git -C demo cat-file -s ce01; bin/git -C demo cat-file -p ce01
blob
6
hello
```

The 21 bytes: 78 01 (the zlib header), 15 bytes of DEFLATE (a fixed block),
1d c5 04 14 (Adler-32 of the 13 bytes "blob 6\0hello\n"). The real git's
`hash-object` prints the same name, its `cat-file -p` reads ours, and its
`fsck --strict` passes (it says "dangling blob" for an object nothing points
to yet: not an error).

Measured:

```
hash-object (no -w)   1 MB     10 MB     100 MB
ours                  0.006 s  0.027 s   0.235 s     (about 425 MB/s of SHA-1)
Apple's git           0.017 s  0.031 s   0.166 s
the book, -w          ours 247066 bytes; the real git at level 1 257886, level 6 216842, level 9 215989
cat-file -p of it     0.009 s  (8 dynamic blocks, 247805 symbols, all from the table)
```

Apple's git is quicker on 100 MB: it is built on the system's SHA-1. Ours is
FIPS 180-4 as written, one block at a time, and git's
collision-detecting SHA-1 is not attempted (the comment in sha1sum.c says
so). The object file is gzip -1's DEFLATE (module 09, chain 4), smaller
than the real git's level 1 and larger than its default.

The slow way: there is no honest one here. Naming by SHA-1 and storing by
name is the obvious way, and there is nothing slower worth a flag; the
lesson's "before" is a store without names (where would the file go, how
would you know it is there?), and its measurable claim is "stored once":
written 1, then already there 1, and the file untouched (the test checks its
mtime).

What the real git writes, ours reads: objects at core.looseCompression 0
(stored blocks), 1, 6 and 9; its commits and trees (`cat-file -t -s -p`).

Damaged objects (the test runs these on every `./learn test`): every cut
of an object file, every single bit flipped (a handful of flips in unused
padding bits change nothing anyone can see, and are allowed), an unknown
type, a wrong size, no size, no NUL, nothing in it, another object's bytes
under this name, junk after the stream, a preset dictionary, not zlib, a
size of 26 digits. Real messages:

```
git: object 3b18e5... is damaged: the data ends in the middle of a block
git: object 3b18e5... is damaged: the data's Adler-32 is 1db80413, but the stream says 1dc50414
git: object 3b18e5... is damaged: its header says 9 bytes, and it has 4
git: object 3b18e5... is damaged: its bytes are the object 2f8a9d...
git: object 3b18e5... is damaged: 4 bytes after its zlib stream
git: object 3b18e5... is not in the repository
git: this repository has packed objects (.git/objects/pack/pack-....pack), and this git reads only loose objects
git: this repository names its objects with sha256 (extensions.objectformat), and this git only with SHA-1
git: 0123456 is the start of no object's name here
git: 3f2a is the start of 2 objects' names: give more of it
```

Break it (forget the length in the padding: in `sha1_final`, `s->buf[56 +
i] = (unsigned char)(bits >> (56 - 8 * i));` becomes `s->buf[56 + i] = 0;`;
the compiler warns that `bits` is unused):

```
$ bin/git -C r hash-object -w hello.txt
3fa655b09dd8ab132718d6b463075e8e43df654d
$ git -C r hash-object hello.txt                    (the real git)
ce013625030ba8dba906f756967f9e9ca394464a
$ bin/git -C r cat-file -p 3fa655b
hello
$ git -C r cat-file -p 3fa655b09dd8ab132718d6b463075e8e43df654d
hello
$ git -C r fsck --strict; echo $?
error: ce013625030ba8dba906f756967f9e9ca394464a: hash-path mismatch, found at: .git/objects/3f/a655b09dd8ab132718d6b463075e8e43df654d
1
```

Worth a paragraph: ours is still consistent with itself (it reads back what
it wrote), and the real git's cat-file reads the file at that path without
checking; only fsck, which hashes the bytes, sees that the name is not the
SHA-1 of them. A name is only a name if everyone computes it the same way.

Break it (Adler-32 that starts s1 at 0 instead of 1: in `zframe_adler32`,
`uint32_t s1 = adler & 0xffff, s2 = adler >> 16;` becomes `uint32_t s1 = 0,
s2 = adler >> 16;`): ours writes and reads its own objects happily; the real
git cannot read them, and ours cannot read the real git's:

```
$ bin/git -C r hash-object -w hello.txt; bin/git -C r cat-file -p ce01362
ce013625030ba8dba906f756967f9e9ca394464a
hello
$ git -C r cat-file -p ce013625030ba8dba906f756967f9e9ca394464a
error: inflate: data stream error (incorrect data check)
error: unable to unpack ce013625030ba8dba906f756967f9e9ca394464a header
fatal: Not a valid object name ce013625030ba8dba906f756967f9e9ca394464a
$ bin/git -C theirs cat-file -p ce01362          (an object the real git wrote)
git: object ce013625030ba8dba906f756967f9e9ca394464a is damaged: the data's Adler-32 is 1db80413, but the stream says 1dc50414
```

Tried and not worth a lesson: dropping the "already there" check in
object_write changes only the counts (written 1 each time); the file is
replaced by an identical one.

## 10.02 Trees and the index: a directory as a hash

The code: `index_read` (header DIRC and version; the checksum, the SHA-1 of
everything before it, or all zeros, which git allows; each entry's 62 fixed
bytes, flags, path and NUL padding to 8 bytes, checked for bounds, a mode git
writes, a path git keeps, and strictly increasing order; then extensions:
TREE is read, an unknown one starting A-Z is optional and passed over, any
other is an error); `index_write` (the same, version 2, and the TREE
extension); `index_add` (walk the directories named, collect the files,
sort them with module 02's merge sort, then merge two sorted lists, the
index and the files found: a file found is hashed and stored, an index entry
under a named path whose file is gone is dropped, and each change forgets
the cached trees above it); `tree_cmp` (git's order); `tree_entries` (a tree
read and checked: modes 40000, 100644, 100755, 120000, 160000 only, no
zero-padded mode, no '/' or "." or ".." names, in git's order); `build`
(one directory's tree from the index entries under it: a subdirectory's
entries are consecutive in the index, so it builds those first, recursively,
then its own; with the cache, a directory whose cached tree is still valid
and has the same number of files is taken as it is).

Why the index's order gives git's order for free: the index is sorted by the
bytes of full paths; "b c" < "b/c" because ' ' (0x20) < '/' (0x2f), which is
exactly git's rule that the directory b sorts as "b/". So build never sorts;
it checks each entry against the one before with tree_cmp and dies if the
order is wrong (it cannot be, unless the index is). The rule is not written
down in git's documentation (fsck's `treeNotSorted` and mktree's "the order
is normalized" say only that there is one); it was found with the real
git's write-tree and checked by the tests.

```
$ DS_STATS=1 DS_TRACE=1 bin/git -C demo add .          (hello.txt was added already)
trace: object: blob of 6 bytes is 94/95c3c5a31810439c36d49aad161b7f3db75d09: written, 21 bytes compressed
trace: index: add b c 100644 9495c3c
trace: object: blob of 2 bytes is f2/ad6c76f0115a6ba5b00456a849810e7ec0af20: written, 17 bytes compressed
trace: index: add b/c 100644 f2ad6c7
...
trace: object: blob of 6 bytes is ce/013625030ba8dba906f756967f9e9ca394464a: already there
stats: git: objects hashed 5, written 4, already there 1, read 0
stats: index: entries read 1, entries written 5, files hashed 5
stats: sort: comparisons 8, moves 12
$ bin/git -C demo ls-files -s
100644 9495c3c5a31810439c36d49aad161b7f3db75d09 0	b c
100644 f2ad6c76f0115a6ba5b00456a849810e7ec0af20 0	b/c
100644 4cdb2265d30204be5463b38174b2e8e717982405 0	d/e/f.txt
100644 01058d844a98d293a3b03a8615a34700e4ed2be3 0	d/g.txt
100644 ce013625030ba8dba906f756967f9e9ca394464a 0	hello.txt
$ DS_STATS=1 DS_TRACE=1 bin/git -C demo write-tree 2>&1 | grep -v object
dcd498446ac96829dc31ffa4625d0c6bafd91ef4
trace: tree: b/ (1 entry, 1 file under it): 1933da3, built
trace: tree: d/e/ (1 entry, 1 file under it): 8588183, built
trace: tree: d/ (2 entries, 2 files under it): d61f885, built
trace: tree: / (4 entries, 5 files under it): dcd4984, built
stats: write-tree: trees built 4, from the cache 0
$ bin/git -C demo cat-file -p dcd4984
100644 blob 9495c3c5a31810439c36d49aad161b7f3db75d09	b c
040000 tree 1933da329284aca10dab8dc2fdd54213acd39be5	b
040000 tree d61f885518975b70c71142b25e9733011c54f39e	d
100644 blob ce013625030ba8dba906f756967f9e9ca394464a	hello.txt
$ printf 'deep\nchanged\n' > demo/d/e/f.txt
$ DS_TRACE=1 bin/git -C demo add d/e/f.txt
trace: object: blob of 13 bytes is 06/654ae6638a2540fc8ae7fe1fc9e4fe396d423d: written, 29 bytes compressed
trace: index: update d/e/f.txt 100644 06654ae
trace: index: d/e/f.txt changed: the cached tree of / is gone
trace: index: d/e/f.txt changed: the cached tree of d/ is gone
trace: index: d/e/f.txt changed: the cached tree of d/e/ is gone
$ DS_STATS=1 DS_TRACE=1 bin/git -C demo write-tree 2>&1 | grep -v object
6f0dd63257b03b15e8d779d11019ce6aa44c8d55
trace: tree: b/ (1 file under it): 1933da3, from the cache
trace: tree: d/e/ (1 entry, 1 file under it): cd21a79, built
trace: tree: d/ (2 entries, 2 files under it): 7ecc4e4, built
trace: tree: / (4 entries, 5 files under it): 6f0dd63, built
stats: write-tree: trees built 3, from the cache 1
$ DS_STATS=1 bin/git -C demo write-tree --algo=all 2>&1 | grep write-tree
6f0dd63257b03b15e8d779d11019ce6aa44c8d55
stats: write-tree: trees built 4, from the cache 0
```

The real git agrees on all of it: its ls-files -s and ls-files read our
index as ours does (and ours reads its index, with its TREE and UNTR
extensions); its write-tree on our index gives our tree, including when our
cached trees are part forgotten; its status after our add and commit is
clean; fsck --strict passes. The real git's own tree of "b c" and b/c lists
"b c" first, as ours does.

"A change deep in a directory renames every tree above it and nothing
else", as the test checks with the real git's `ls-tree -r -t` before and
after one change to d/e/f/g.txt: the trees renamed are exactly "", d, d/e
and d/e/f.

The slow way and the fast: `--algo=all` builds every tree; the default uses
the cached trees (the index's TREE extension, gitformat-index's "cache
tree"), so only the directories above a change are built. Measured on
`gen.py tree N` (N files, eight to a directory), after changing the last file:

```
files    directories   all: built    cache: built, from the cache    all      cache    add .
1000         134           134            4      14                  0.004 s  0.004 s  0.022 s
4000         509           509            4      20                  0.008 s  0.006 s  0.080 s
16000       2073          2073            5      23                  0.022 s  0.016 s  0.337 s
64000       8585          8585            6      28                  0.081 s  0.053 s  1.551 s
```

Be honest in the lesson about the clock: the counts differ by a thousand
times, the time by less than two, because hashing 8585 small trees (all
already stored, so nothing is compressed) costs less than reading and
writing an index of 64000 entries (about 5 MB), which both do. The cache
pays more when the trees are new (each must be compressed and written), and
the real git uses the same cache to compare the index with HEAD without
opening the trees, which is the next break-it.

Break it (forget to forget: in `cache_invalidate`, `CacheTree *ct =
ix->cache;` becomes `CacheTree *ct = NULL;`): the change is staged, but the
cached top tree still says the old tree; commit believes it, and so does the
real git, which uses the same cache:

```
$ printf 'deeper\n' > r/d/e/f/g.txt
$ DS_STATS=1 bin/git -C r add d
stats: index: entries read 5, entries written 5, files hashed 2
$ DS_STATS=1 bin/git -C r commit -m deeper; echo $?
nothing to commit: the index is HEAD's tree
stats: write-tree: trees built 0, from the cache 1
1
$ git -C r status --porcelain                        (the real git: nothing to say)
$ git -C r write-tree; git -C r rev-parse HEAD^{tree}
0f8e40515217ebc9221bf7729ece57bf291eba5d
0f8e40515217ebc9221bf7729ece57bf291eba5d
```

(Made at 10.03 so that commit exists; index.c is the same at 10.02.) A cache
that is not forgotten when what it describes changes lies to everyone who
trusts it.

Break it (plain byte order: in `tree_cmp`, `int ca = alen > n ? (unsigned
char)a[n] : adir ? '/' : 0;` and the cb line lose `adir ? '/' :` and `bdir
? '/' :`): ours refuses its own index and the real git's trees.

```
$ bin/git -C r add .; bin/git -C r write-tree        ("b c" and b/c)
git: the index is not in git's order: 'b' after 'b c'
$ git -C theirs write-tree; git -C theirs cat-file -p b9c92c9
b9c92c98d135b4b426ff71c932bfeff6ad0867ba
100644 blob 9495c3c5a31810439c36d49aad161b7f3db75d09	b c
040000 tree 1933da329284aca10dab8dc2fdd54213acd39be5	b
$ bin/git -C theirs ls-tree b9c92c9
git: tree b9c92c98d135b4b426ff71c932bfeff6ad0867ba is damaged: 'b' comes after 'b c', out of git's order
```

Break it (one byte short of padding: in `index_write`, `size_t step = (62 +
e->len + 8) & ~(size_t)7;` becomes `(62 + e->len + 7)`): a path whose entry
is a multiple of 8 bytes loses its NUL; both readers notice, in their own
words.

```
$ bin/git -C r add .; bin/git -C r ls-files -s         (files ab, abcdefghij, x)
git: the index is damaged: entry 1's path
$ git -C r ls-files -s
fatal: unknown index entry format 0x696a0000
```

Damaged indexes the test runs (an ordinary error each, `git: the index ...`):
every 7th cut, a byte changed every 13 bytes, version 4 (`git: the index is
version 4, which this git does not read (it reads 2 and 3)`), version 9,
more entries than it has, a mode git does not write, a required extension
(`link`), an extension running past the end, cached trees that cannot be
read, two entries swapped. Damaged trees: mode 100664 (`tree X: entry 'x'
has mode 100664, which git does not write`), a zero-padded 040000, out of
order, a directory after its "b c", cut short, a '/' in a name, no mode.
add of a file that is gone takes it out of the index; `add nonesuch` is
`git: pathspec 'nonesuch' did not match any files`; a left .git/index.lock
is `git: .git/index.lock exists: another git is at work here, or one stopped
half way (remove it if not)`.

## 10.03 Commits: walking a graph for log

The code: `commit_read` (the tree line first, parent lines, author,
committer and its date, any other header lines passed over, a blank line,
the message; each part checked); `commit_create` (the text, with the
identity from the environment; the message as git's `commit -m` cleans it:
trailing spaces and blank lines at the ends dropped, runs of blank lines
made one); `ref_read`, `ref_write` (refs/heads/x through x.lock, renamed),
`rev_parse`; `walk_heap` (the newest commit off the heap, printed, each
parent looked up in the table of names seen and, if new, put in it and
pushed); `walk_list` (the same with an Array searched end to end for the
newest, and an Array of names searched from the start).

The order: the committer's date, newest first; two from the same second in
the order they were met (a sequence number). That is the real git's order
for a plain `git log`, including ties: the test makes three branches from
one root, all in the same second, and log of the merge and of the three tips
in a shuffled order print the real git's lines.

```
$ bin/git -C demo commit -m first
[main (root-commit) 4531ec6] first
$ bin/git -C demo cat-file -p HEAD
tree dcd498446ac96829dc31ffa4625d0c6bafd91ef4
author A U Thor <author@example.com> 1700000000 +0000
committer C O Mitter <committer@example.com> 1700000000 +0000

first
$ bin/git -C demo log
commit 06e83fd206ce7c613ad1c81876e562db21960e96
Merge: 04edf9e 790a49c
Author: A U Thor <author@example.com>
Date:   Tue Nov 14 22:15:20 2023 +0000

    Merge side

commit 04edf9e3a6a10c66ce9d9350930deb41312163ae
...
$ DS_STATS=1 DS_TRACE=1 bin/git -C demo log --oneline 2>&1 | grep -v object
06e83fd Merge side
04edf9e second
790a49c on a side branch
4531ec6 first
trace: log: pop 06e83fd 1700000120; heap: (empty)
trace: log: push 04edf9e 1700000060; heap: 04edf9e 1700000060
trace: log: push 790a49c 1700000030; heap: 04edf9e 1700000060, 790a49c 1700000030
trace: log: pop 04edf9e 1700000060; heap: 790a49c 1700000030
trace: log: push 4531ec6 1700000000; heap: 790a49c 1700000030, 4531ec6 1700000000
trace: log: pop 790a49c 1700000030; heap: 4531ec6 1700000000
trace: log: 4531ec6, parent of 790a49c: seen already
trace: log: pop 4531ec6 1700000000; heap: (empty)
stats: log: commits 4, queue scans 0, seen probes 0
stats: heap: pushes 4, pops 4, comparisons 2, moves 6
stats: table: lookups 9, probes 1, inserts 4, resizes 0, moves 0
$ DS_STATS=1 bin/git -C demo log --oneline --algo=list 2>&1 | grep log:
stats: log: commits 4, queue scans 2, seen probes 10
```

(The two "read commit 06e83fd" lines the grep hides: log checks that each
start is a commit before it walks, then reads it again.)

The real git agrees: our commit-tree and commit make commits with the real
git's names, given the same tree, parents, people and dates (the test makes
the same commit in a repository of each and compares HEAD); the real git's
log, log --oneline, -n 2, -3 and log of two starts print ours byte for byte
on our history, and ours prints the real git's on its own (merges, time zones
+0530, -0800, +0100, a tab and an indented line in a message, ties); fsck
--strict passes. Log's format: "Date:   " and the author's date in the
author's own zone, day of the month not padded; each message line four
spaces in, tabs expanded to every eighth column counted from the start of
the message line (the real git expands them: found by comparing).

Measured on `gen.py linear N` (one line of N commits) and `wide N` (16
branches whose dates interleave, joined by one merge):

```
linear N    list: seen probes   list       heap+table: table probes   heap      the real git
 2000         1999000          0.053 s       2514                     0.051 s   0.075 s
 4000         7998000          0.100 s       5468                     0.091 s   0.116 s
 8000        31996000          0.200 s      11462                     0.183 s   0.227 s
16000       127992000          0.485 s      23392                     0.365 s   0.441 s
32000       511984000          1.238 s      47900                     0.784 s   0.912 s
64000      2047968000          3.597 s      96044                    1.803 s   2.097 s
128000     8191936000         19.876 s     191310                    5.498 s   6.749 s   (one run each)
wide N      list: queue scans, seen probes        heap: comparisons
 1600          23895, 1306431     0.039 s           11193     0.037 s
 6400          95895, 20585631    0.158 s           44794     0.145 s
25600         383895, 328102431   0.902 s          179191     0.615 s
102400      1535895, 5244569631   12.853 s         716793     3.903 s   (one run each)
```

seen probes on a line is exactly n(n-1)/2 (each new parent is compared with
every name seen; the test checks it). The time is mostly reading the
commits (open, inflate, SHA-1: about 25 microseconds each), which both pay,
so the list's cost shows only once n(n-1)/2 compares of 20 bytes outgrow the
reads: at 16000 commits the list is a third slower, at 32000 more than half,
at 128000 it takes 20 s where the heap and table take 5.5 s (and the real
git 6.7 s). Making those histories took gen.py 20 s and 45 s. On a line the heap never holds two
commits (comparisons 0): the heap matters when many lines run at once; with
16 it compares about 7 times per commit where the list scans 15.

Break it (no set of names seen: in `walk_heap`, `if (table_get(&seen, p,
20) != NULL) {` becomes `if (0) {`): a commit two paths lead to is printed
twice.

```
$ DS_STATS=1 bin/git -C r log --oneline 3f88564        (first, left and right on it, merged)
3f88564 merge
f245c9b left
b1090f6 right
e6eb99b first
e6eb99b first
stats: log: commits 5, queue scans 0, seen probes 0
$ git -C r log --oneline 3f88564
3f88564 merge
f245c9b left
b1090f6 right
e6eb99b first
```

Break it (the heap the wrong way up: in `commit_newer`, `return x->time >
y->time ? -1 : 1;` becomes `return x->time < y->time ? -1 : 1;`), on
`gen.py fork 3` (main 0-2, then left 0-2 and right 0-2 on it):

```
$ bin/git -C r log --oneline left right
2cc2b93 left 2
73bb960 left 1
319b46a left 0
e9f6579 main 2
362c470 main 1
5ca57f5 main 0
fb58be9 right 2
253ce09 right 1
ffbffb5 right 0
$ git -C r log --oneline left right
fb58be9 right 2
253ce09 right 1
ffbffb5 right 0
2cc2b93 left 2
...
```

(The oldest commit in the queue comes out first, so ours goes all the way
down one branch, past the fork, before it ever prints the newest commit.)

Errors the test runs: `git: HEAD~9: 4531ec6 has 0 parents, so no parent 1`,
`git: HEAD^3: ... has 2 parents, so no parent 3`, `git: 'nonesuch' names
nothing: not an object's name, a branch or a tag`, a tree given to log (`is
a tree, not a commit`), `git: HEAD is on main, which has no commits yet`, a
commit whose parent is missing (`git: object 1111... is not in the
repository`, after the commits before it are printed), and commits with no
tree, no committer, no date, no end to the header, or a bad parent line.
`commit` with nothing changed prints `nothing to commit: the index is
HEAD's tree` and exits 1.

## 10.04 diff between commits, and the merge base

The code: `walk_skip` (two trees' entries merged in git's order; the same
name, mode and object: passed over, a whole subdirectory for one comparison
of 20 bytes; a subdirectory that differs: opened, recursively; a file:
a change; a name on one side only: everything under it gone or new; a file
that became a symbolic link: gone, then new, as git prints it); `flatten`
and `walk_all` (the slow way: every tree opened, every blob read, files
compared byte by byte by path); `show_change` (git's header lines: `diff
--git a/P b/P`, new/deleted file mode, old/new mode, `index A..B MODE` with
7-digit unique names; "Binary files ... differ" when either blob has a NUL
in its first 8000 bytes; else module 06: `diff_text` of each blob,
`diff_myers`, `--- a/P` and `+++ b/P` (a tab after a name with a space, as
git writes it; quoted names for tabs and quotes), `diff_unified`); `paint`
(merge-base: both commits marked 1 and 2 and pushed on a heap by date; each
commit popped passes its marks to its parents; one with both is a merge
base, and its marks become "stale" too, so everything behind it is passed
along as stale; it stops when only stale commits are queued; then any base
that another base reaches is dropped); `rewalk` (the obvious way: walk b's
history newest first, and for each commit walk a's whole history again to
see if it is there; the first ones found are the candidates; then the same
dropping).

```
$ DS_STATS=1 DS_TRACE=1 bin/git -C demo diff HEAD~1~1 HEAD 2>&1 | grep -v object
diff --git a/d/e/f.txt b/d/e/f.txt
index 4cdb226..06654ae 100644
--- a/d/e/f.txt
+++ b/d/e/f.txt
@@ -1 +1,2 @@
 deep
+changed
trace: diff: b c: 9495c3c on both sides: the same, passed over
trace: diff: b/: 1933da3 on both sides: the same, passed over
trace: diff: d/: d61f885 and 7ecc4e4: different, opened
trace: diff: d/e/: 8588183 and cd21a79: different, opened
trace: diff: d/e/f.txt: 4cdb226 and 06654ae: changed
trace: diff: d/g.txt: 01058d8 on both sides: the same, passed over
trace: diff: hello.txt: ce01362 on both sides: the same, passed over
stats: diff: trees read 6, blobs read 2, entries compared 7, subtrees skipped 1, blobs skipped 3, bytes compared 0, files changed 1
stats: myers: d 1, diagonals 2, cells 3, bytes 8
$ DS_STATS=1 bin/git -C demo diff --algo=all HEAD~1~1 HEAD 2>&1 | grep diff:
stats: diff: trees read 8, blobs read 12, entries compared 5, subtrees skipped 0, blobs skipped 0, bytes compared 21, files changed 1
$ DS_STATS=1 DS_TRACE=1 bin/git -C demo merge-base main~1 side 2>&1 | grep -v object
4531ec69f8bbf02ab6d151b79429a9c0701732ef
trace: merge-base: pop 04edf9e 1700000060, reached by 1
trace: merge-base: pop 790a49c 1700000030, reached by 2
trace: merge-base: pop 4531ec6 1700000000, reached by 1 and 2, stale
trace: merge-base: pop 4531ec6 1700000000, reached by 1 and 2, stale
stats: merge-base: commits visited 4, walks 0
$ DS_STATS=1 DS_TRACE=1 bin/git -C demo merge-base --algo=rewalk main~1 side 2>&1 | grep -v object
4531ec69f8bbf02ab6d151b79429a9c0701732ef
trace: merge-base: 790a49c 1700000030 is not in the first's history
trace: merge-base: 4531ec6 1700000000 is in the first's history: a candidate
stats: merge-base: commits visited 6, walks 2
```

(4531ec6 is popped twice: both its children pushed it. The real git's walk
does the same.)

Checked against the real git, which is not minimal by default (the diff
agent found this for diff(1); git's own diff is the same unless --minimal):
so the tests compare what a patch does, not its hunks. On two commits that
change, add, delete, empty, make executable, change mode and content, turn
a file into a directory and back, change a symbolic link's target, turn a
file into a link, and touch names with a space and a tab and a last line
without a newline: the header lines (diff --git, modes, index, ---, +++) are
the real git's `diff --no-renames`, line for line; the lines added and taken
away in each file are its `--numstat --minimal`; and `git apply --cached`
(with `--unidiff-zero` at -U0) on a `read-tree` of the first commit makes
the second commit's tree at -U3, -U1 and -U0. A binary change is the real
git's text exactly. The real git's hunk headers carry a function name after
"@@" (`@@ -10,7 +10,7 @@ int main(void)`); ours do not, as module 06's do
not; git apply ignores it. The real git detects renames by default; ours
does not (a rename is a deletion and an addition; compare with
--no-renames).

Measured, `gen.py tree N`, one file changed at the bottom:

```
files    skip: trees, blobs read, subtrees skipped   time      all: trees, blobs read    time      the real git
 1000      8, 2, 14                                 0.003 s     268,   2002            0.033 s   0.012 s
 4000      8, 2, 20                                 0.003 s    1018,   8002            0.134 s   0.014 s
16000     10, 2, 23                                 0.003 s    4146,  32002            0.601 s   0.014 s
64000     12, 2, 28                                 0.004 s   17170, 128002            2.662 s   0.014 s
```

Two trees per level of the path and the two blobs, whatever the size of the
tree: the time does not move from 1000 files to 64000 (it is starting the
process), where reading everything grows with the files. (all's "blobs
read" is both commits' files and the changed file's two blobs again, read
to print them.)

`gen.py fork N` (N commits, then N more on each of two branches):

```
N      paint: visited   time      rewalk: visited, walks   time
 100        202         0.007 s       20202,  101          0.009 s
 200        402         0.011 s       80402,  201          0.018 s
 400        802         0.018 s      320802,  401          0.041 s
 800       1602         0.034 s     1281602,  801          0.106 s
1600       3202         0.062 s     5123202, 1601          0.333 s
```

paint visits the two branches and the base: 2N + 2. rewalk visits a's whole
history (2N commits) once for each commit of b's branch it tries: about 2N^2.
The time is dominated by reading the 3N commits until about N = 800, then
the walks show: four times the work for twice the commits.

merge-base cases the test runs against the real git (both algorithms, with
and without --all): a fork, an ancestor (the answer is the older commit), a
criss-cross (two branches that each merged the other: two best common
ancestors, and --all prints both; without it, the real git's first), a
commit with itself, a branch from another root (no common ancestor: nothing
printed, status 1).

Break it (mode changes forgotten: in `walk_skip`, `if (x->mode == y->mode &&
memcmp(x->oid, y->oid, 20) == 0) {` becomes `if (memcmp(x->oid, y->oid, 20)
== 0) {`): hello.txt made executable, d/k.txt given a line; the bytes are
the same, so the mode change is passed over:

```
$ bin/git -C r diff HEAD~1 HEAD
diff --git a/d/k.txt b/d/k.txt
index b68fde2..cf835ac 100644
--- a/d/k.txt
+++ b/d/k.txt
@@ -1 +1,2 @@
 k
+k
$ git -C r diff HEAD~1 HEAD
diff --git a/d/k.txt b/d/k.txt
...
+k
diff --git a/hello.txt b/hello.txt
old mode 100644
new mode 100755
```

Break it (never stale: in `paint`, delete `f |= STALE;`): the answer is
still right, the work is not. On `gen.py fork 200`:

```
$ DS_STATS=1 bin/git -C r merge-base left right
dc66756ba21b6d091efe9b834ffd167d05c3f161
stats: merge-base: commits visited 40600, walks 398
```

(0.513 s, against 402 visited and 0.011 s.) Without the stale mark every
commit of the trunk is a "merge base", the walk goes to the root, and
dropping the 199 that the newest one reaches takes 398 more walks.

## Hostile input, under AddressSanitizer and UndefinedBehaviorSanitizer

The finished project built with `make EXTRA_CFLAGS="-fsanitize=address,undefined
-fno-omit-frame-pointer -fno-sanitize-recover=all"` in a copy, fed by a fuzz
script kept out of the track: every object file of a small repository (blobs,
trees, commits) damaged 8 times each (cuts, bit flips, bytes inserted and
deleted, random bytes; half of them inside the zlib stream, so the content
itself is damaged and the stream is good), each run through log (both
algorithms), ls-tree -r -t, diff (both), merge-base (both), ls-files and
cat-file; 150 damaged hand-made trees and commits through ls-tree, log,
merge-base and diff; 300 damaged indexes, most with a checksum made to
match, through ls-files, write-tree and add; HEAD, refs/heads/main,
packed-refs and config damaged 40 times each; and names on the command line
such as `HEAD~99999999999999999999`, `HEAD` followed by 2000 `~1`, 5000 a's,
`refs/../../x`, `../../etc/passwd`. Every run had to end with status 0, 1 or
2 and no sanitizer report.

- Mac (Apple clang 21): 3617 runs, 0 failures (3 min 53 s: sanitized
  processes start slowly on macOS).
- Linux (gcc 14.2, Debian in Docker): 7234 runs (two rounds), 0 failures.
  gcc found two places where a path could be cut short by snprintf
  (-Wformat-truncation): fixed, with every snprintf that could truncate now
  checked.

## BSD, GNU, and the real git: what differs

- The real git's diff is not minimal and detects renames; its hunk headers
  name a function. The tests compare file lists, header lines, line counts
  (`--minimal`) and what git apply makes.
- The real git trusts the cached trees in the index for status (the
  10.02 break-it); and it reads an object by its path without checking its
  name (10.01's), as fsck does not.
- Apple's git hashes faster than ours (system SHA-1); Debian's git 2.47.3
  and Apple's 2.50.1 gave the same answers everywhere.
- Debian has no `patch` and no `zip`: nothing here needs them.

## The tests and the timeline

10.01: names of 201 byte strings (0 to 199 bytes and a megabyte) against
hashlib, with the sha1 blocks and bytes counted exactly; the real git's names
for the book, nothing, binary bytes; -w stored once, the file 78 01 ... that
Python's zlib reads, read back by the real git, fsck --strict; the start of a
name, ambiguous among 600 objects; the real git's objects at four levels and
its commit and tree; about 200 damaged objects; packed and SHA-256
repositories; no walk-up, no .git file, no writing to the real git's, no
second init; the trace. 10.02: the index both ways (ls-files -s, ls-files,
status), version 2, sorted, the TREE extension parsed by the test's own
reader; trees equal to the real git's, in git's order; the real git's index
with TREE and UNTR read by ours; one deep change: the cached trees forgotten
(the trace and the index), 4 built and 2 from the cache, the trees renamed
are exactly the path's; 3000 files: one tree per directory, then the depth
of the change; add of a gone file, a missing path, a locked index, the real
git's repository; 21 damaged indexes and 7 damaged trees. 10.03: commit-tree
and commit names equal to the real git's; log in five forms both ways;
cat-file of seven names; the real git's history with three zones and a
merge, both algorithms; 2000 commits: n(n-1)/2 seen probes against under 3n
table probes; 16 branches: queue scans against heap comparisons; the trace;
11 bad names and commits. 10.04: the patch against the real git's header
lines, numstat and git apply at three contexts; binary; all and skip print
the same; 3000 files: 2 trees per level and 2 blobs against all of them;
seven merge-base cases both algorithms both ways; 150-commit fork: 2N+2
against N^2; the trace; a missing parent, a name of nothing, a blob.

check-timeline at each lesson from 10.01 types into one shell: a repository
made with mktemp (hash-object -w, cat-file -p/-t/-s, a name of nothing, the
no-walk-up message from a directory inside it, a second init, a command that
does not exist); the next lesson's command as `no command`; from 10.02 add,
ls-files -s, write-tree (fe4afc2c...), ls-tree, a bad --algo; from 10.03
commit (82764a0, the same name on every machine), a second commit and log,
`HEAD~5`; from 10.04 diff and merge-base; then the directory is removed.
After the shell (timeline_after), in a tempfile directory: the book through
hash-object -w and the real git's cat-file; from 10.02 write-tree equal to
the real git's; from 10.03 log equal, status clean; fsck --strict at every
lesson.

Whole runs on the Mac (loaded by other jobs): `./learn test dsa 10` about 10
s (1.8, 2.8, 2.9, 2.4; most of it starting processes, the real git some 400
times); on Linux 1.8 s. check-skeleton dsa 10 16 s, check-timeline dsa 10
36 s (most of both is building the project four times).

## For the lessons: running it

`./learn run dsa --at 10.01 -- git -C demo init` makes build/at/dsa/10.01/
demo, a repository of its own; every later command takes `-C demo`. Set the
identity once in the reader's shell for 10.03 on (`export
GIT_AUTHOR_NAME=... GIT_AUTHOR_EMAIL=... GIT_COMMITTER_NAME=...
GIT_COMMITTER_EMAIL=...`, and the two _DATE variables for names that are the
same on every machine); without them commit says `git: who is committing?
Set GIT_AUTHOR_NAME and GIT_AUTHOR_EMAIL (or user.name and user.email in
.git/config): this git reads no other config`. To make test repositories:
`python3 tools/git/gen.py linear 2000 big` (shapes linear, wide, fork,
tree; see its docstring); its repositories say `[dsa] ours = true`, so add
and commit work in them.
