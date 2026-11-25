# The Blood of Dawnwalker – Lacra Questline Repair

> ⚠️ **BETA / EXPERIMENTAL**: these are unofficial save edits. Always keep backups.

> ⚠️ **Game update 1.2 (November 11, 2026):** none of the fixes here, **including v2**, have
> been tested on saves from game version 1.2. v2 was tested on build CL-265636
> (SaveVersion 136). If you try it on 1.2, keep your backups and please
> [report the result](#reporting-results).

Unofficial save-repair tools for Lacra's questline in *The Blood of Dawnwalker*. They cover
**"A Friend Like This" (q103)** and its continuation, **"Song of the Mountain"**, and they let
you get the questline back without reverting your whole playthrough.

The usual reason the questline closes is that you protected Nish from Lacra or refused to
cooperate with her. That ends q103 **by design**, and Song of the Mountain never starts.

---

## Which fix should I use?

**Use [v2](docs/v2.md).** The older approaches are documented for reference.

| Version | Script | Author | Approach | Status | Docs |
|---|---|---|---|---|---|
| **v2** (recommended) | `dawnwalker_lacra_fix_v2.py` | Wllader | Marks q103 as finished *with* Lacra's cooperation and starts Song of the Mountain at its "Lacra waits for you" start | ✅ Confirmed in game on one save (SaveVersion 134 → played on 136). ⚠️ Not tested on 1.2. | [docs/v2.md](docs/v2.md) |
| **v1** | `dawnwalker_lacra_repair.py` | heeyblitz | The original fix's q103 restart plus a 25-byte Lacra state copied from an older "known-good" save | ⚠️ Partial: Lacra appeared but with a red aura and couldn't be killed normally; the quest only moved on after she killed the player. SaveVersion 134 only. | [docs/v1.md](docs/v1.md) |
| **Original q103 fix** | `dawnwalker_lacra_fix.py` (not in this repo) | AiKiKun with Claude Opus 5 | Restarts q103 in the middle by restoring its active quest nodes and removing q103 facts | ❌ The quest restarts, but the Lacra boss never spawns. | [docs/original-q103-fix.md](docs/original-q103-fix.md) |

### At a glance

| | Original fix | v1 | v2 |
|---|---|---|---|
| Saves needed | Current save | GOOD + CURRENT (same SaveVersion) | Current save |
| Lacra duel | Lacra never spawns | Plays, but broken | Skipped (no XP) |
| Nish interrogation | Not reached | Plays | Skipped (no XP) |
| Reaches Song of the Mountain | No | Only if the game moves on after Lacra kills you | Yes, directly |
| Tested SaveVersions | – | 134 | 134 (patched), played on 136 |
| Tested on game 1.2 | No | No | **No** |

---

## Documentation

- **[Setup](docs/setup.md)**: save location, backups, Steam Cloud, Python, Oodle/`ooz`
  decompression. Read this first, whichever fix you use.
- **[v2: continue into Song of the Mountain](docs/v2.md)** (Wllader): usage, mechanism,
  prerequisites, pros and cons, and the full research methodology.
- **[v1: q103 restart + Lacra state transplant](docs/v1.md)** (heeyblitz): legacy, with the
  original research write-up.
- **[Original q103 fix](docs/original-q103-fix.md)** (AiKiKun): where it all started.

## How we got from the original fix to v2

1. **[Original fix](docs/original-q103-fix.md)**: restarted q103 → the quest ran, but Lacra
   never spawned.
2. **[v1](docs/v1.md)**: assumed Lacra's actor state was a separate problem and copied it from
   an older save → she appeared, but the duel was broken.
3. **[v2 research](docs/v2.md#methodology-how-the-fix-was-found)**: the quest graphs were
   exported from the game files, and the problem turned out to be in how quests restart:
   - LacraBoss is spawned **only once, at the end of the Prologue**, when the game
     automatically starts q103. She then stays hidden in her house until the duel.
   - The game **drops restored actions** (like spawns) when it loads a save; it only resumes
     *waits*.
   - So no mid-quest restart can ever spawn her properly.
4. **[v2](docs/v2.md)**: skips ahead to Song of the Mountain using only wait nodes, so the game
   spawns Lacra itself.

## Quick start (v2)

```
python dawnwalker_lacra_fix_v2.py "C:\Users\<you>\AppData\Local\Dawnwalker\Saved\SaveGames\ManualSave1.sav" --ooz ooz.exe
```

1. Back up your save folder first.
2. Run the command above on your save. It writes a new save slot.
3. Load the new slot and wait for night.
4. Find Lacra (cave next to Stonefall / near Crown Rock) and talk to her. Song of the Mountain
   continues from there.

See [docs/v2.md](docs/v2.md) for prerequisites and caveats.

---

## Reporting results

Reports from other saves are the most useful thing right now, **especially from game version
1.2**. Please include:

```text
Fix:                 v2 / v1 / original q103 fix
Game version/build:  (e.g. 1.2, CL-265636)
Platform:            Steam / GOG
SaveVersion:         (printed by the script)
How q103 ended:      (protected Nish, no cooperation, Lacra killed, ...)

v2: Lacra appeared at night:        YES / NO   (where?)
v2: "Lacra by the mountain" played: YES / NO
v2: Song of the Mountain continued: YES / NO

v1 / original fix: q103 restored / Lacra appeared / could be damaged / encounter progressed

Crash or error message:
Additional notes:
```

---

## Credits

- **AiKiKun** with **Claude Opus 5**: the original q103 save research and
  `dawnwalker_lacra_fix.py` (the original q103 fix), whose save-parsing layer v1 and v2 build on.
- **heeyblitz**: [dawnwalker-lacra-repair](https://github.com/heeyblitz/dawnwalker-lacra-repair),
  the upstream repository and v1 (`dawnwalker_lacra_repair.py`).
- **Wllader**: v2 (`dawnwalker_lacra_fix_v2.py`) and its quest-graph research.
- **powzix**: [ooz](https://github.com/powzix/ooz), the open-source Oodle decompressor.
- **persiangirl**: the community AES key, via [Make your own Mapping File](https://www.nexusmods.com/thebloodofdawnwalker/mods/136).
- **Vercadi** and the UE4SS team: [UE4SS for Dawnwalker](https://www.nexusmods.com/thebloodofdawnwalker/mods/18).
- **FModel**: [fmodel.app](https://fmodel.app).
- **DwSav**: [Nexus mod 285](https://www.nexusmods.com/thebloodofdawnwalker/mods/285), for its fact and quest lists.
- **xxHash**: [Cyan4973/xxHash](https://github.com/Cyan4973/xxHash) and the [Python bindings](https://pypi.org/project/xxhash/).

## Disclaimer

This is an **unofficial, community-made** save repair. It is not affiliated with or endorsed
by Rebel Wolves or Bandai Namco. The game files are only read; nothing here ships game assets.

It is beta/experimental, not guaranteed to work on every save, and not tested on game
version 1.2. Save files can be corrupted if modified incorrectly. **Always make backups**, and
never use these tools on your only copy of a save.
