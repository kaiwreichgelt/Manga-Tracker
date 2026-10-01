import json
import math

SAVE_FILE = "manga.json"


def prompt(message):
    # Returns None if the user ends input (Ctrl+D) or interrupts (Ctrl+C).
    try:
        return input(message)
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def load_manga():
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        raise SystemExit(f"{SAVE_FILE} isn't valid JSON. Fix or delete it, then run again.")
    if not isinstance(data, dict):
        raise SystemExit(f"{SAVE_FILE} should hold an object of title -> chapter.")
    # Drop values an earlier buggy run may have saved (NaN, Infinity, non-numbers),
    # since json.dump would refuse to write them back out.
    manga = {}
    for name, progress in data.items():
        if isinstance(progress, bool) or not isinstance(progress, (int, float)):
            print(f"Ignoring {name}: saved chapter isn't a number.")
        elif not math.isfinite(progress):
            print(f"Ignoring {name}: saved chapter isn't a real number.")
        else:
            manga[name] = progress
    return manga


def get_title(manga):
    while True:
        answer = prompt("Manga name: ")
        if answer is None:
            return None
        name = answer.strip()
        if not name:
            print("Please enter a manga name.")
            continue
        # Match an existing entry regardless of case, so "frieren" updates "Frieren".
        for existing in manga:
            if existing.casefold() == name.casefold():
                return existing
        return name


def get_chapter():
    # Accepts normal chapters (24) and special chapters (24.5)
    while True:
        answer = prompt("Chapter you're on: ")
        if answer is None:
            return None
        try:
            chapter = float(answer)
        except ValueError:
            print("Please enter a number, like 24 or 24.5.")
            continue
        if not math.isfinite(chapter) or chapter < 0:
            print("Please enter a chapter of 0 or more.")
            continue
        if chapter.is_integer():
            return int(chapter)
        return chapter


manga = load_manga()
title = get_title(manga)
if title is None:
    raise SystemExit(0)
chapter = get_chapter()
if chapter is None:
    raise SystemExit(0)
if title in manga:
    print(f"Updating {title}: chapter {manga[title]} -> {chapter}")
else:
    print(f"Adding {title} at chapter {chapter}")
manga[title] = chapter
with open(SAVE_FILE, "w") as f:
    json.dump(manga, f, indent=2, allow_nan=False)
for name, progress in manga.items():
    print(f"{name}: chapter {progress}")
