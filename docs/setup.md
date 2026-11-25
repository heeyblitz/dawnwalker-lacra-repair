# Setup shared by all fixes

[← Back to README](../README.md)

## Save location

```text
Steam: %LOCALAPPDATA%\Dawnwalker\Saved\SaveGames
GOG:   %LOCALAPPDATA%\Dawnwalker\Saved\GOGSaveGames
```

Example: `C:\Users\<USERNAME>\AppData\Local\Dawnwalker\Saved\SaveGames`

## Back up your saves

**Back up the entire save folder before using any fix here.** Do not experiment on your only
copy. The scripts write a new save instead of overwriting the source, but keep your own
backups anyway.

## Steam Cloud

Steam Cloud can sync saves back into the folder after you modify or delete files. While
testing, make sure you know which save Steam is loading, and consider temporarily disabling
Steam Cloud.

Don't assume a higher-numbered save is newer. Generated or test saves can get higher numbers,
so `ManualSave912.sav` is not necessarily later than `ManualSave79.sav`. Check the save's:

- thumbnail
- timestamp
- in-game day
- player location
- quest state

## Python

Python 3 on Windows. v2 needs Python 3.8+ and no extra packages.

## Oodle / Kraken decompression

Dawnwalker's `.sav` files contain Oodle/Kraken-compressed data, so the scripts need a
decompressor to **read** saves. v2 doesn't need one for writing: it writes "stored"
(uncompressed) Kraken blocks, which the game accepts.

Pick **one**:

- **`ooz`**: an open-source Kraken/Oodle decompressor, <https://github.com/powzix/ooz>.
  Build or download it, then pass:
  - `--ooz ooz.exe` if it's next to the script,
  - its full path, e.g. `--ooz "C:\Tools\ooz.exe"`, or
  - `--ooz ooz` if it's in your `PATH`.
- **`oo2core_9_win64.dll`**: the Oodle runtime, which ships with many Unreal Engine games.
  Pass `--oodle-dll oo2core_9_win64.dll`.

Do not download random DLL files from generic DLL-download websites.
