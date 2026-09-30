# The Blood of Dawnwalker — Lacra Questline Repair

> ⚠️ **BETA / EXPERIMENTAL**

An unofficial save-repair tool for restoring Lacra's questline, **"A Friend Like This" (q103)**, in *The Blood of Dawnwalker* without reverting an entire playthrough.

This project started from an existing community q103 save repair and adds an experimental Lacra actor/persistence repair for the case where q103 can be restored but Lacra herself is still missing when the encounter starts.

---

## Table of Contents

- [Background](#background)
- [The Original q103 Fix](#the-original-q103-fix)
- [The Second Problem](#the-second-problem)
- [What We Investigated](#what-we-investigated)
- [The Breakthrough](#the-breakthrough)
- [What This Tool Does](#what-this-tool-does)
- [Technical Details](#technical-details)
- [Requirements](#requirements)
- [Save Location](#save-location)
- [Back Up Your Saves](#back-up-your-saves)
- [Steam Cloud](#steam-cloud)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Analyze Mode](#analyze-mode)
- [Repair Modes](#repair-modes)
- [GOOD vs CURRENT](#good-vs-current)
- [Testing Status](#testing-status)
- [Expected Results](#expected-results)
- [Troubleshooting](#troubleshooting)
- [Reporting Results](#reporting-results)
- [Credits](#credits)
- [Disclaimer](#disclaimer)

---

# Background

I accidentally locked myself out of Lacra's questline earlier in my playthrough.

The problem was not discovered immediately. By the time I realized that **"A Friend Like This" / q103** had become unavailable, my playthrough had already progressed several in-game days.

Going back to the old save would have meant losing a significant amount of progress.

The goal was therefore:

```text
KNOWN-GOOD SAVE
       │
       │ Lacra-related state
       ▼
CURRENT SAVE
       │
       │ targeted repair
       ▼
CURRENT PROGRESS
       +
Lacra quest restored
```

The objective was **not** to replace the current save with the old save.

The objective was to restore only the state necessary to get Lacra's questline working again while preserving the current playthrough.

---

# The Original q103 Fix

The starting point for this project was the existing public q103 save research/fix created by **AiKiKun together with Claude Opus 5**.

Huge credit to them for the original save reverse-engineering work.

The original `dawnwalker_lacra_fix.py` works at the Dawnwalker DSAV save-data level.

Conceptually, it restores the q103 quest graph and removes the facts that caused q103 to remain closed:

```text
QuestHelperImpl
       │
       └── restore q103 active quest graph nodes

QuestSystemImpl
       │
       └── remove q103-related facts
```

If your only problem is that q103 became permanently closed, **try the original q103 fix first**.

If that completely solves the problem, you do not need this experimental Lacra-state repair.

This repository does **not** claim the original q103 fix as its own.

---

# The Second Problem

In my case, restoring q103 was not enough.

The quest could be triggered again, but when the Lacra encounter started, Lacra herself was still invisible/missing.

The situation looked like this:

```text
q103 restored
      │
      ▼
quest starts
      │
      ▼
encounter starts
      │
      ▼
Lacra should appear
      │
      ▼
Lacra is invisible / missing
```

This suggested that there was another layer of state involved.

Restoring the quest state did not necessarily restore the persistent actor state required for Lacra to actually appear in the encounter.

---

# What We Investigated

The investigation compared a known-good save with the current save instead of simply copying the old save over the current one.

The areas investigated included:

- `QuestHelperImpl`
- `QuestSystemImpl`
- `RebelAISubsystem`
- persistent actor state
- actor/community state
- `AttributeSaveSystem`
- world/persistent state
- Lacra references
- `LacraBoss` references
- encounter/spawn state
- q103 facts
- q103 active graph nodes

The important distinction became:

```text
Quest state
     ≠
Lacra persistent actor state
```

The goal was to find the smallest relevant state that could be restored from the known-good save without replacing unrelated current progress.

---

# The Breakthrough

The first patches I tried did **not** make Lacra appear.

The successful test used:

- the **current save** as the base
- an **older known-good save** as the Lacra reference

The relevant Lacra state was restored into the current save.

The result was significant:

> **Lacra physically appeared in the encounter again.**

However, the behavior was not completely normal.

In the successful test:

- Lacra appeared physically.
- She initially had an abnormal red aura/halo.
- I could not initially kill her normally.
- Allowing Lacra to kill the player allowed the game to progress beyond the encounter.

This is the reason this project is explicitly labeled **BETA / EXPERIMENTAL**.

The important breakthrough was that Lacra was no longer completely missing.

---

# What This Tool Does

The intended workflow is:

```text
GOOD.sav
   +
CURRENT.sav
   │
   ▼
analyze both
   │
   ├── restore q103 if required
   │
   └── restore experimental Lacra state
   │
   ▼
FIXED.sav
```

The **CURRENT** save remains the base save.

The **GOOD** save is used as a reference for the Lacra state.

The original saves are not supposed to be overwritten.

The script can also analyze the two saves before writing a repaired save.

---

# Technical Details

The experimental Lacra repair operates inside:

```text
RebelAISubsystem
```

The script searches for a specific Lacra-related serialized signature.

The current implementation uses:

```text
LACRA_ANCHOR = 20 43 6f 06 9b 3b 00
```

When the signature is found uniquely in both saves, the script uses the state beginning at the observed offset and replaces a **25-byte field** in the CURRENT save with the corresponding 25-byte field from the GOOD save.

Conceptually:

```text
GOOD
RebelAISubsystem
      │
      └── Lacra signature
              │
              └── 25-byte state
                       │
                       ▼
                 transplant
                       │
                       ▼
CURRENT
RebelAISubsystem
      │
      └── same Lacra state location
```

The script deliberately does **not** copy the entire `RebelAISubsystem`.

It also refuses to guess if the Lacra signature is not unique:

```text
GOOD    != exactly 1 match
CURRENT != exactly 1 match
        ↓
       ABORT
```

This is intentional. A failed repair is preferable to blindly modifying an unknown region of a save.

---

# Requirements

- Windows
- Python 3
- *The Blood of Dawnwalker*
- A Dawnwalker `SaveVersion 134` save
- Oodle/Kraken decompression support
- A known-good save
- Your current save

The script supports two decompression methods:

- **`ooz` executable** — the recommended method for this repository
- **`oo2core_9_win64.dll`** — an alternative supported by the script

For the workflow documented here, the examples use `ooz`.

The tested save format is:

```text
SaveVersion 134
```

The script warns if a different save version is detected.

---

# Save Location

On Windows, Dawnwalker saves are normally located at:

```text
%LOCALAPPDATA%\Dawnwalker\Saved\SaveGames
```

Example:

```text
C:\Users\<USERNAME>\AppData\Local\Dawnwalker\Saved\SaveGames
```

---

# Back Up Your Saves

**Do this before using the script.**

Copy the entire save folder somewhere safe:

```text
%LOCALAPPDATA%\Dawnwalker\Saved\SaveGames
```

Keep your original GOOD and CURRENT saves.

Do not experiment on your only copy.

The script is designed to write a new output save rather than overwrite the CURRENT save, but you should still maintain independent backups.

---

# Steam Cloud

Steam Cloud can interfere with save-file testing.

If Steam Cloud is active, Steam may synchronize saves back into the save directory after you modify or delete files.

For testing, make sure you understand which save Steam is loading.

You may want to temporarily disable Steam Cloud while testing the repaired save.

Also, do not assume that a higher-numbered save is automatically newer or better.

For example:

```text
ManualSave79.sav
ManualSave912.sav
```

The number alone does not establish which file contains the desired game state.

During testing, new generated/test saves can receive higher numbers.

Always verify using:

- save thumbnail
- timestamp
- in-game day
- player location
- inventory/progression
- actual quest state

---

# Installation

Download:

```text
dawnwalker_lacra_repair.py
```

Place it somewhere convenient.

## Oodle / Kraken decompression

Dawnwalker's `.sav` files contain Oodle/Kraken-compressed data. The repair
script needs a decompressor to read those blocks.

This repository supports an external **`ooz`** executable. `ooz` is an
open-source Kraken/Oodle decompressor.

Project:

https://github.com/powzix/ooz

Download/build `ooz` for your environment and make sure the executable is
accessible from the command prompt.

For example, if `ooz.exe` is in the same directory as the repair script:

```text
dawnwalker_lacra_repair.py
ooz.exe
```

You can then use:

```bat
--ooz ooz.exe
```

If `ooz.exe` is already in your system `PATH`, you can simply use:

```bat
--ooz ooz
```

### Alternative: Oodle DLL

The script also supports loading an Oodle runtime DLL directly:

```text
oo2core_9_win64.dll
```

This is an alternative to `ooz`; you do **not** need both.

If you already have a compatible Oodle DLL, pass it with:

```bat
--oodle-dll oo2core_9_win64.dll
```

Do not download random DLL files from generic DLL-download websites.

Keep the script, decompressor, and save files accessible from the command
prompt.

---

# Basic Usage

Example using a known-good save and current save:

```bat
python dawnwalker_lacra_repair.py ^
    --good ManualSave75.sav ^
    --current ManualSave79.sav ^
    --output ManualSave_LacraFix.sav ^
    --ooz ooz.exe
```

Where:

```text
ManualSave75.sav
    = known-good reference save

ManualSave79.sav
    = current save whose progress should be preserved

ManualSave_LacraFix.sav
    = new repaired save
```

Replace these filenames with your own.

If your `ooz` executable has a different filename or is stored elsewhere,
replace `ooz.exe` with its path, for example:

```bat
--ooz "C:\Tools\ooz.exe"
```

---

# Analyze Mode

Before modifying anything, you can analyze the GOOD and CURRENT saves:

```bat
python dawnwalker_lacra_repair.py ^
    --good ManualSave75.sav ^
    --current ManualSave79.sav ^
    --analyze ^
    --ooz ooz.exe
```

The analysis reports information including:

- GOOD SaveVersion
- CURRENT SaveVersion
- `RebelAISubsystem` sizes
- Lacra signature occurrences
- GOOD Lacra bytes
- CURRENT Lacra bytes
- whether the Lacra field differs
- q103 active state
- q103 nodes that would be restored
- q103 facts that would be removed

This is useful if you want to inspect the saves before creating a repaired file.

---

# Repair Modes

All examples below use the `ooz` decompressor. If you prefer the DLL
method, replace:

```bat
--ooz ooz.exe
```

with:

```bat
--oodle-dll oo2core_9_win64.dll
```

The default mode attempts both:

```text
q103 repair
+
experimental Lacra repair
```

## Only the q103 repair

Skip the experimental Lacra patch:

```bat
python dawnwalker_lacra_repair.py ^
    --good GOOD.sav ^
    --current CURRENT.sav ^
    --output FIXED.sav ^
    --no-lacra ^
    --ooz ooz.exe
```

Use this if you only want the original q103-style repair.

---

## Only the experimental Lacra repair

Skip the q103 repair:

```bat
python dawnwalker_lacra_repair.py ^
    --good GOOD.sav ^
    --current CURRENT.sav ^
    --output FIXED.sav ^
    --no-q103 ^
    --ooz ooz.exe
```

This can be useful if the original q103 fix has already been applied and the remaining problem is specifically that Lacra is missing during the encounter.

---

# GOOD vs CURRENT

This distinction is extremely important.

## GOOD

The GOOD save should be an earlier save where Lacra's state is known to be correct.

It is used as a **reference**.

It is not the save you are trying to continue playing from.

## CURRENT

The CURRENT save is the save containing the progress you want to preserve.

It is the base for the repaired save.

For example:

```text
GOOD
ManualSave75.sav
       │
       │ reference only
       ▼
CURRENT
ManualSave79.sav
       │
       │ preserve this progression
       ▼
ManualSave_LacraFix.sav
```

Do **not** simply replace your current save with the old GOOD save.

That defeats the purpose of the repair.

---

# Testing Status

## Known test case

The successful test was performed using:

```text
GOOD:
ManualSave75.sav

CURRENT:
ManualSave79.sav

SaveVersion:
134
```

The successful result was:

```text
q103 restored
       ↓
Lacra encounter triggered
       ↓
Lacra physically appeared
```

The Lacra encounter still showed abnormal behavior in the test:

```text
Lacra visible
    +
red aura/halo
    +
could not initially be killed normally
    +
allowing Lacra to kill the player
allowed progression
```

Therefore:

> ⚠️ The Lacra-specific repair is **not currently proven to be a universal fix**.

More save pairs need to be tested.

---

# Expected Results

The most important test is **not** simply whether the journal says that q103 is active.

The important test is:

> **When the Lacra encounter starts, does Lacra physically appear?**

Possible outcomes include:

### 1. Lacra appears normally

Excellent. Report the result.

### 2. Lacra appears but is invulnerable

This indicates that additional encounter/combat state may still need investigation.

### 3. Lacra appears with a red aura/halo

This matches the behavior observed in the original successful test.

### 4. Lacra can be damaged but the encounter does not progress

Report the exact behavior.

### 5. Lacra kills the player and the quest progresses

This also matches the behavior observed during the initial successful test.

### 6. Lacra remains invisible

The experimental state was not sufficient for that save.

### 7. The game crashes

Stop testing that output save and return to your backup.

---

# Troubleshooting

## "Lacra signature was not unique"

The script intentionally refuses to guess.

Run:

```bat
python dawnwalker_lacra_repair.py ^
    --good GOOD.sav ^
    --current CURRENT.sav ^
    --analyze ^
    --ooz ooz.exe
```

If the signature count is not exactly:

```text
GOOD=1
CURRENT=1
```

do not manually force the patch.

Report the result instead.

---

## GOOD and CURRENT have different SaveVersion values

The tested repair expects matching save versions.

The script will refuse to continue when the GOOD and CURRENT save versions differ.

Use saves from compatible game/save versions.

---

## The game loads the wrong save

Check:

- Steam Cloud
- filename
- timestamp
- save thumbnail
- save metadata
- in-game day

Do not rely only on the filename number.

---

## q103 was already progressed

The script checks for facts indicating that the current save may already be past the initial q103 stage.

In that situation, the q103 portion can be left unchanged rather than blindly resetting the quest.

This is another reason to use `--analyze` first.

---

# If It Does Not Work

Do not repeatedly overwrite your saves.

Keep:

```text
GOOD.sav
CURRENT.sav
```

unchanged.

If you want to report a failed test, provide:

1. Game version
2. Platform
3. SaveVersion
4. GOOD save filename
5. CURRENT save filename
6. Whether the original q103 fix was already applied
7. Whether q103 triggered
8. Whether Lacra appeared
9. Whether Lacra could be damaged
10. Whether the encounter progressed after player death
11. Any crash/error message

If possible, provide the GOOD and CURRENT saves so the structures can be compared.

---

# Reporting Successful Results

If the repair works, please report:

```text
Game version:
SaveVersion:
GOOD save:
CURRENT save:

q103 restored:
YES / NO

Lacra appeared:
YES / NO

Lacra could be damaged:
YES / NO

Lacra behavior:
NORMAL / ABNORMAL

Encounter progressed:
YES / NO

Additional notes:
...
```

The more different save pairs that are tested, the easier it will be to determine whether the experimental Lacra state is actually generalizable.

---

# Credits

## Original q103 research and fix

Huge credit to:

**AiKiKun**

with:

**Claude Opus 5**

for the original save reverse-engineering work and `dawnwalker_lacra_fix.py`.

That work is the foundation for the q103 restoration portion of this project.

The original q103 fix should be tried first.

This project does **not** claim the original q103 research or fix as its own.

## Experimental Lacra repair

The additional Lacra-state investigation was performed by comparing a known-good save against the current save and testing targeted state restoration.

The Lacra-specific portion of this repository is experimental and was initially validated on one affected playthrough.

---

# Disclaimer

This is an **unofficial community-made save repair tool**.

It is:

- BETA
- EXPERIMENTAL
- not endorsed by the developers
- not guaranteed to work on every save
- not guaranteed to preserve every state

Save files can become corrupted if modified incorrectly.

**Always make backups.**

Do not use this tool on your only copy of a save.

The Lacra-specific repair has only been validated on a limited test case so far.

---

# TL;DR

If you simply lost access to Lacra's questline:

1. Make a backup.
2. Try the original q103 fix by **AiKiKun + Claude Opus 5** first.
3. If q103 is restored but Lacra is still missing when the encounter starts, this experimental repair may help.
4. Use an older GOOD save where Lacra was known to work.
5. Use your CURRENT save as the base.
6. Run `--analyze` first.
7. Create a NEW output save.
8. Test the repaired save.
9. Report the result.

The key discovery behind this project was:

```text
Restoring q103
      ≠
Restoring Lacra
```

In the tested case, a targeted Lacra state restoration caused Lacra to physically appear again without reverting the entire current playthrough.

That is the part that still needs more testing.
