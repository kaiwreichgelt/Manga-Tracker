# Manga Tracker

A small desktop app for remembering what chapter you're on.

Reading twelve ongoing series means twelve chapter numbers to remember, and the
answer is usually "somewhere around 120?". This keeps them in one place, shows
how far through each series you are, and tells you how long it's been since you
last picked one up.

![The Manga Tracker window](docs/screenshot.png)

## What it does

- **Track chapters**, whole or half (`24` and `24.5` both work — specials count)
- **One-click progress**: `+1 chapter` when you finish one, `−1` to undo a misclick
- **Optional series totals**, so you get `127 / 140` and a progress bar
- **Last-updated times** in plain words — `just now`, `yesterday`, `12 days ago`
- **Live filter**: type `vin` to find *Vinland Saga*
- **Library summary**: how many chapters you've read, and how far through overall

## Running it

Needs Python 3.9 or newer. No dependencies — the interface uses `tkinter`, which
ships with Python.

```bash
python gui.py
```

On Windows you can double-click `Manga Tracker.pyw` instead, which opens the
window with no console behind it.

There's also a keyboard-driven version if you prefer a terminal:

```bash
python tracker.py
```

Both read and write the same file, so you can switch between them freely.

### Keyboard shortcuts

| Key | Does |
| --- | --- |
| `Ctrl+N` | Add a manga |
| `Ctrl+F` | Jump to the filter box |
| `Enter` / double-click | Edit the selected row |
| `+` / `−` | Step the selected chapter up or down |
| `Delete` | Remove the selected manga |

## Where your data lives

In `manga.json`, next to the script:

```json
{
  "Frieren": {
    "chapter": 127,
    "total": 140,
    "updated": "2026-10-06T18:46:33"
  }
}
```

Plain JSON on purpose — it's readable, hand-editable, and backs up by being
copied. It's gitignored, so your reading history stays off GitHub.

Older save files, from back when the format was just `{"Frieren": 127}`, still
load; they're upgraded in place the first time you change a chapter.

## A few decisions worth explaining

**`Ctrl+C` and `Ctrl+D` mean different things.** In the terminal version, `Ctrl+C`
abandons whatever you're part-way through and returns you to the menu, while
`Ctrl+D` exits. They can't be treated the same: `Ctrl+D` means stdin has closed,
so a menu loop that treated it as "go back to the menu" would print the menu
forever. They're separate exceptions for that reason.

**"Last updated" means the chapter moved**, not that you opened the app. Fixing a
typo in a title, or correcting a series total, deliberately leaves the timestamp
alone — otherwise it would stop answering the question it exists to answer.

**Partial totals don't get summed into a percentage.** If only three of your ten
series have known totals, adding those three up produces a denominator that isn't
your real goal. The summary reports total chapters read, then gives the
percentage with its scope stated: `164 of 514 across the 2 with known totals`.

**Bad data is reported, not silently dropped.** A chapter saved as `NaN`,
`Infinity`, `true` or a string can't be written back out by `json.dump`, so the
loader skips those entries and says which ones and why, rather than failing on
save later.

## Layout

| File | What's in it |
| --- | --- |
| `tracker.py` | Loading, saving, validation — and the terminal interface |
| `gui.py` | The window |
| `Manga Tracker.pyw` | Double-click launcher for Windows |

`gui.py` imports `tracker` rather than duplicating any of it, so both interfaces
agree about what a library file means and what counts as valid.

## Still to come

- Tests covering the chapter maths, the save-format migrations, and the dialogs
- Looking up series totals automatically instead of typing them in
- Sorting the list by progress or by how stale an entry is
