# Original q103 fix – Restart q103 (`dawnwalker_lacra_fix.py`, by AiKiKun)

[← Back to README](../README.md) · Next: [v1](v1.md) · Latest: [v2](v2.md)

> **Status: superseded.** The quest restarts, but Lacra never spawns for the duel. If q103
> closed because you protected Nish or refused to cooperate with Lacra, use [v2](v2.md).
> This script is **not included in this repository**, and we don't currently have a link to it.

## Who made it

**AiKiKun** with **Claude Opus 5**. It was the first public q103 save research and fix. Its
save-parsing layer is the base that both [v1](v1.md) and [v2](v2.md) build on:

- the DSAV node tree
- the name table
- node replacement
- the fact-name hash (UE `Strihash_DEPRECATED`)

> **About this page:** the original research was published outside this repository and was
> never copied here. This page only summarises what v1's README said about it.
> [v2's methodology](v2.md#methodology-how-the-fix-was-found) builds on the original fix's
> save-parsing helpers and describes the save format in more detail.

## Mechanism

It works at the DSAV save-data level and tries to **restart q103 in the middle**:

```text
QuestHelperImpl
       └── re-insert q103's active quest-graph nodes

QuestSystemImpl
       └── remove the q103 facts that keep the quest closed
```

## Prerequisites

- A single save in which q103 (A Friend Like This) has closed.
- Python 3 and an Oodle decompressor (see [setup](setup.md)).

## Pros

- Only needs the save you want to keep playing.
- The quest runs again: the alley clues and the house scenes work, and the cinematic with
  Lacra plays.

## Cons

- **Lacra (the boss) never spawns**, so the duel can't be fought and q103 can't finish.
- This can't be fixed within the restart approach, as the
  [v2 research](v2.md#why-the-restart-approach-could-never-work) later showed:
  - LacraBoss is spawned only once, at the end of the Prologue, when the game
    automatically starts q103.
  - The game drops restored spawn actions when it loads a save.

## What came next

- **[v1](v1.md)** (heeyblitz): kept the original restart and added a copy of Lacra's actor
  state from an older save. Lacra appeared, but the duel was broken.
- **[v2](v2.md)** (Wllader): drops the restart approach and skips ahead to Song of the
  Mountain instead.
