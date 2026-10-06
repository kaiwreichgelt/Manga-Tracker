import json
import math
from datetime import datetime

SAVE_FILE = "manga.json"

MENU = """
1) Add or update a manga
2) List everything
3) Remove a manga
q) Quit"""


class Quit(Exception):
    # stdin is closed (Ctrl+D), so there's no point prompting again.
    pass


class Cancelled(Exception):
    # Ctrl+C: abandon whichever action is running, but keep the session.
    pass


def prompt(message):
    try:
        return input(message)
    except EOFError:
        print()
        raise Quit
    except KeyboardInterrupt:
        print()
        raise Cancelled


def read_entry(name, value):
    # Returns {"chapter", "updated"} for one saved manga, or None if unusable.
    # Accepts the old flat format (title -> chapter) alongside the current
    # one (title -> {"chapter": n, "updated": timestamp}).
    if isinstance(value, dict):
        chapter, raw_time = value.get("chapter"), value.get("updated")
    else:
        chapter, raw_time = value, None
    # Drop values an earlier buggy run may have saved (NaN, Infinity, non-numbers),
    # since json.dump would refuse to write them back out.
    if isinstance(chapter, bool) or not isinstance(chapter, (int, float)):
        print(f"Ignoring {name}: saved chapter isn't a number.")
        return None
    if not math.isfinite(chapter):
        print(f"Ignoring {name}: saved chapter isn't a real number.")
        return None
    updated = None
    if raw_time is not None:
        try:
            updated = datetime.fromisoformat(raw_time)
        except (TypeError, ValueError):
            print(f"{name}: ignoring an update time I can't read.")
    return {"chapter": chapter, "updated": updated}


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
    manga = {}
    for name, value in data.items():
        entry = read_entry(name, value)
        if entry is not None:
            manga[name] = entry
    if any(not isinstance(value, dict) for value in data.values()):
        print(f"Upgraded {SAVE_FILE} to record update times. Existing entries show "
              f"'never' until you next change them.")
    return manga


def save_manga(manga):
    data = {
        name: {
            "chapter": entry["chapter"],
            "updated": entry["updated"].isoformat(timespec="seconds") if entry["updated"] else None,
        }
        for name, entry in manga.items()
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2, allow_nan=False)


def describe_age(updated):
    # How long ago progress last changed, in words.
    if updated is None:
        return "never"
    seconds = (datetime.now() - updated).total_seconds()
    if seconds < 0:
        # Hand-edited file, or the clock moved backwards.
        return f"on {updated:%Y-%m-%d}"
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        count = int(seconds // 60)
        return f"{count} minute{'' if count == 1 else 's'} ago"
    if seconds < 86400:
        count = int(seconds // 3600)
        return f"{count} hour{'' if count == 1 else 's'} ago"
    days = int(seconds // 86400)
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    return f"on {updated:%Y-%m-%d}"


def get_title(manga):
    while True:
        name = prompt("Manga name: ").strip()
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
        try:
            chapter = float(prompt("Chapter you're on: "))
        except ValueError:
            print("Please enter a number, like 24 or 24.5.")
            continue
        if not math.isfinite(chapter) or chapter < 0:
            print("Please enter a chapter of 0 or more.")
            continue
        if chapter.is_integer():
            return int(chapter)
        return chapter


def add_or_update(manga):
    title = get_title(manga)
    chapter = get_chapter()
    entry = manga.get(title)
    if entry is None:
        print(f"Adding {title} at chapter {chapter}")
    elif entry["chapter"] == chapter:
        print(f"{title} is already at chapter {chapter}, last changed {describe_age(entry['updated'])}")
        return
    else:
        print(f"Updating {title}: chapter {entry['chapter']} -> {chapter}")
    manga[title] = {"chapter": chapter, "updated": datetime.now()}
    save_manga(manga)


def show_library(manga):
    if not manga:
        print("Nothing tracked yet.")
        return
    name_width = max(len(name) for name in manga)
    rows = []
    for name, entry in sorted(manga.items(), key=lambda item: item[0].casefold()):
        rows.append((name, f"chapter {entry['chapter']}", describe_age(entry["updated"])))
    chapter_width = max(len(row[1]) for row in rows)
    for name, chapter, age in rows:
        print(f"  {name:<{name_width}}  {chapter:<{chapter_width}}  updated {age}")


def remove_manga(manga):
    if not manga:
        print("Nothing tracked yet.")
        return
    title = get_title(manga)
    if title not in manga:
        print(f"{title} isn't being tracked.")
        return
    answer = prompt(f"Remove {title} at chapter {manga[title]['chapter']}? [y/N] ")
    if answer.strip().casefold() not in ("y", "yes"):
        print(f"Kept {title}.")
        return
    del manga[title]
    save_manga(manga)
    print(f"Removed {title}.")


def main():
    manga = load_manga()
    actions = {"1": add_or_update, "2": show_library, "3": remove_manga}
    while True:
        print(MENU)
        try:
            choice = prompt("> ").strip().casefold()
        except Cancelled:
            # Ctrl+C with no action running means the user wants out.
            raise Quit
        if choice in ("q", "quit"):
            return
        if choice not in actions:
            print("Please pick 1, 2, 3, or q.")
            continue
        try:
            actions[choice](manga)
        except Cancelled:
            print("Cancelled.")


if __name__ == "__main__":
    try:
        main()
    except Quit:
        pass
