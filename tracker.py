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


def format_number(value):
    # 207.5 stays 207.5, but 164.0 should read as 164.
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def read_chapter_count(name, value, label):
    # A chapter or total is usable only if it's a real, non-negative number.
    # Guards against NaN, Infinity and non-numbers an earlier run may have
    # saved, since json.dump would refuse to write them back out.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        print(f"{name}: ignoring a {label} that isn't a number.")
        return None
    if not math.isfinite(value) or value < 0:
        print(f"{name}: ignoring a {label} that isn't a real count.")
        return None
    return value


def read_entry(name, value):
    # Builds one library entry, accepting the old flat format (title -> chapter)
    # alongside the current one (title -> {chapter, total, updated}).
    if isinstance(value, dict):
        raw_chapter = value.get("chapter")
        raw_total = value.get("total")
        raw_time = value.get("updated")
    else:
        raw_chapter, raw_total, raw_time = value, None, None

    chapter = read_chapter_count(name, raw_chapter, "chapter")
    if chapter is None:
        print(f"Ignoring {name}.")
        return None

    total = None
    if raw_total is not None:
        total = read_chapter_count(name, raw_total, "total")
        if total == 0:
            print(f"{name}: ignoring a total of 0.")
            total = None
        elif total is not None and total < chapter:
            print(f"{name}: total of {format_number(total)} is below chapter "
                  f"{format_number(chapter)}, so it may be out of date.")

    updated = None
    if raw_time is not None:
        try:
            updated = datetime.fromisoformat(raw_time)
        except (TypeError, ValueError):
            print(f"{name}: ignoring an update time I can't read.")

    return {"chapter": chapter, "total": total, "updated": updated}


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
            "total": entry["total"],
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


def describe_progress(entry):
    chapter = format_number(entry["chapter"])
    if entry["total"] is None:
        return f"chapter {chapter}"
    share = entry["chapter"] / entry["total"]
    return f"chapter {chapter} of {format_number(entry['total'])} ({share:.0%})"


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


def get_total(chapter, current):
    # Blank keeps what we already know, so an unknown total stays unknown and a
    # known one survives a routine chapter bump without being retyped.
    if current is None:
        message = "Chapters in total (blank if unknown): "
    else:
        message = f"Chapters in total [{format_number(current)}, blank to keep]: "
    while True:
        answer = prompt(message).strip()
        if not answer:
            return current
        try:
            total = float(answer)
        except ValueError:
            print("Please enter a number, or leave it blank.")
            continue
        if not math.isfinite(total) or total <= 0:
            print("Please enter a total above 0.")
            continue
        if total < chapter:
            print(f"You're on chapter {format_number(chapter)}, so the total can't be lower.")
            continue
        if total.is_integer():
            return int(total)
        return total


def add_or_update(manga):
    title = get_title(manga)
    chapter = get_chapter()
    entry = manga.get(title)
    total = get_total(chapter, entry["total"] if entry else None)
    if entry is None:
        print(f"Adding {title} at chapter {format_number(chapter)}")
    elif entry["chapter"] != chapter:
        print(f"Updating {title}: chapter {format_number(entry['chapter'])} "
              f"-> {format_number(chapter)}")
    elif entry["total"] != total:
        print(f"{title}: total is now {format_number(total)} chapters")
    else:
        print(f"{title} is already at chapter {format_number(chapter)}, "
              f"last changed {describe_age(entry['updated'])}")
        return
    # Only a chapter change counts as progress, so correcting a total on its own
    # leaves the timestamp where it was.
    moved = entry is None or entry["chapter"] != chapter
    manga[title] = {
        "chapter": chapter,
        "total": total,
        "updated": datetime.now() if moved else entry["updated"],
    }
    save_manga(manga)


def show_summary(manga):
    read = sum(entry["chapter"] for entry in manga.values())
    titles = f"{len(manga)} title{'' if len(manga) == 1 else 's'}"
    known = [entry for entry in manga.values() if entry["total"] is not None]
    if not known:
        print(f"\n  {titles}, {format_number(read)} chapters read")
        return
    goal = sum(entry["total"] for entry in known)
    if len(known) == len(manga):
        print(f"\n  {titles}, {format_number(read)} of {format_number(goal)} "
              f"chapters read ({read / goal:.0%})")
        return
    # Measuring every chapter against partial totals would invent a denominator,
    # so the percentage says which titles it covers.
    counted = sum(entry["chapter"] for entry in known)
    print(f"\n  {titles}, {format_number(read)} chapters read")
    print(f"  {format_number(counted)} of {format_number(goal)} across the "
          f"{len(known)} with known totals ({counted / goal:.0%})")


def show_library(manga):
    if not manga:
        print("Nothing tracked yet.")
        return
    rows = [
        (name, describe_progress(entry), describe_age(entry["updated"]))
        for name, entry in sorted(manga.items(), key=lambda item: item[0].casefold())
    ]
    name_width = max(len(row[0]) for row in rows)
    progress_width = max(len(row[1]) for row in rows)
    for name, progress, age in rows:
        print(f"  {name:<{name_width}}  {progress:<{progress_width}}  updated {age}")
    show_summary(manga)


def remove_manga(manga):
    if not manga:
        print("Nothing tracked yet.")
        return
    title = get_title(manga)
    if title not in manga:
        print(f"{title} isn't being tracked.")
        return
    answer = prompt(f"Remove {title} at {describe_progress(manga[title])}? [y/N] ")
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
