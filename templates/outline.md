---
id: <track id, lowercase>
title: <track title>
kind: <kernel | compiler | interpreter | inference | research | ...>
status: coming soon
audience: <who this is for, one line>
prerequisites: <what they must already know, one line>
outcome: <the real, working thing they have at the end, one sentence>
upstream: Proposed, not decided: [<repo>](https://github.com/<owner>/<repo>) (<licence>) for <what>
---

# <Track title>

<Two or three sentences: what you build over the whole track and why it
is worth having.>

**Coming soon.** This is the outline: the direction, not the lessons yet.

## Rules of this format

- An outline gives direction only. Lessons are written when the track is built.
- Every module has, in this order: `Goal`, `You build`, `Value`, `Lessons`
  (titles only, numbered NN.LL), `Learn from` (resource keys).
- `Goal` is one sentence a learner can repeat back. `You build` names a
  real artifact. `Value` says what it is good for outside the course.
- Every resource is defined once, in `## Library` at the end, and cited
  by key like `[V-GPT]`. Kinds: book, video, article, paper, course, code.
  Put a URL in `Where` when there is one: the site links the title to it.
- `upstream` names the industry repositories the track will be backed by,
  each with its licence (read from the repo's LICENSE) and what it is for.
  Until the owner decides, it starts "Proposed, not decided:". The site
  shows it as "Planned to follow". A built track says it in `UPSTREAM`
  in its `track.py`.
- ASCII only.
- The site lists the outline beside the real tracks as "Coming soon" and
  shows it at `/t/<id>`; its lessons are titles, not links, until the
  track is built in `tracks/<id>/` (which then takes the id over).
- Module art is optional, one folder per module next to this file:
  `outlines/<file name without .md>/NN/cover.svg` and `icon.svg`, for
  example `outlines/inference-engineering/02/cover.svg`. Same contract as a
  track's `lessons/NN-slug/` art (see `harness/web/art.py`): the cover is
  a 640x300 teaching diagram styled only by the `.art` classes, the icon a
  20x20 `currentColor` line icon. A missing or unsafe file shows nothing.
- `./learn check` checks these rules.

## Module NN - <Title>

- Goal: <what the learner understands after this module>
- You build: <the artifact this module adds>
- Value: <what it is good for>
- Lessons:
  - NN.LL <Lesson title>
- Learn from: [KEY], [KEY]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| KEY | book | <title> | <author> | <publisher and year, or URL> |
