"""Track {{ID}}: {{TITLE}}

The contract every track meets (see harness/core.py):

    TITLE, KIND, SUMMARY   shown by ./learn map
    build(t)               called once before this track's tests; raise Fail on error
    fixtures               any functions tests call as t.track.<name>(t, ...)

For a compiler track, a fixture typically compiles a source string and
returns a Session running the result. For an interpreter track, a fixture
typically starts the REPL and returns its Session.
"""

from harness.core import Fail  # noqa: F401

TITLE = "{{TITLE}}"
KIND = "{{KIND}}"
SUMMARY = "<one sentence>"

# The industry repository this track is built on. The site credits it on the overview, the
# home card and /credits and, with "derived": True, on every lesson page. When the code is
# derived from it, keep its licence next to the code ("licence_file", and in FILES_FROM).
UPSTREAM = {
    "name": "<project>",
    "url": "https://github.com/<owner>/<repo>",
    "licence": "<as its LICENSE file says, e.g. MIT>",
    "owes": "<one sentence: what this track owes to it>",
    "derived": False,
    # "copyright": "<its copyright line>", "licence_file": "LICENSE", "chip": "based on <project>",
}

# When each file comes into the project the site shows, lesson by lesson (see
# harness/timeline.py): a file with @build regions comes with its first region's
# lesson unless it is named here; every file without regions must be named, at the
# first lesson that needs it to build or run. ./learn check reports any file left out.
FILES_FROM = {
    # "Makefile": "00.01",
}


def build(t):
    # e.g. t.run(["make", "-s"])
    pass


def start(t):
    """Example fixture: start the system under test and return a Session."""
    return t.spawn(["echo", "replace me"], name="{{ID}}")
