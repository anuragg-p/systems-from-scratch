---
id: {{ID}}
title: {{TITLE}}
labels: with code
---

# {{ID}} {{TITLE}}

<One or two sentences: what this lesson teaches and why the system needs it.
No hook question, no jargon the reader has not met yet.>

## Where this fits

![Where {{ID}} fits](figures/{{ID}}-map.svg)

<The track's architecture map (the same in every lesson; this lesson's piece
in the accent colour, earlier pieces solid, later ones dashed), then three to
five plain sentences: what this piece is, what sits above it and uses it,
what sits below it and it uses, and what the system can do after this lesson
that it could not do before. No identifiers, offsets or function names here.

The first lesson of a track is different: it is the whole system in one
picture before any part is built. Follow one request through every layer
and back, name each layer in one plain sentence (what it is given, what it
gives back), and say the order the track builds them in and why. Only that
lesson and the module READMEs give the tour of the whole system.>

## The idea

![<Caption for the lesson's main diagram>](figures/{{ID}}-<name>.svg)

<Start from the need: what the system cannot do yet, or what goes wrong
without this code, with one concrete case the reader can picture. Then the
idea in plain words, with one small worked example. Function names only
once the idea is clear. When the lesson has several pieces of code, give
each its own short lead-in under a small heading (### name): where it fits
and why it is needed, before any detail. The page shows the full code right
after this section: explain it, do not paste it or restate it line by line.>

## Run it

<How to see it working on the reader's own machine: the command, what the
system prints (pasted from a real run), and one thing to type or try that
exercises this lesson.>

<!-- verify: session -->
```
$ ./learn run {{TRACK}} --at {{ID}}
<what it printed, pasted from a real run>
```

## How it works

<Only the two or three decisions in the code that are not obvious, and why
each was made that way: what breaks otherwise. Quote the few lines that
matter. Define each new term in **bold** the first time. State the
**invariant** the code protects and point at the line that keeps it. If a
sentence only repeats what a line of code plainly says, delete it.
Reference detail that is true but dull (field tables, every offset) goes in
a figure or a short table at the end, or is dropped.>

## Decide the boundary

<Optional; the site shows it at the end of How it works. Name this design's
choice as a choice. "This system does X. Another could do Y, and pay Z."
End on the question that decides between them.>

## Break it

<An experiment: one change to make in the code, exactly what happens when
you run it, and why. Verified by really doing it.>

<!-- verify: patch file=<the file, inside the project>
-<the line as it is>
+<the line as the reader changes it>
-->
<!-- verify: session run="./learn run {{TRACK}} --at {{ID}}" -->
```
<what it printed, pasted from a real run>
```

## Go deeper

<Further reading as links, never copied text: for xv6 the OSTEP chapters
(the authors' free PDFs), for other tracks their own references. Say what
to look for in each. Only link pages that have been fetched and say what
the lesson claims.>

Related: <NN.LL Title>, <NN.LL Title>

<!-- The verify: comments are for authors and never shown: each says how ./learn verify
replays the block under it (README.md, "Verifying a lesson"). Every code block must be code
from the project at this lesson, or carry one. -->

Figures go on a line of their own, `![Caption](figures/NN.LL-name.svg)`,
with the file in the figures/ folder beside the lesson. Only where the idea
is a process (a sort, a heap fixing itself), one figure per lesson may be
stepped: each top-level `<g class="step">` is a frame the reader steps
through, its first `<title>` the step's caption, and the frames come from a
real run of the reference code (art/steps.py writes them). This is a lesson,
not an exercise: never tell the reader to write or fill in the code, and
never mention stubs, solutions, workspaces or tests. Never refer to code
from a later lesson as if the reader already has it. (Delete this paragraph
in a real lesson.)
