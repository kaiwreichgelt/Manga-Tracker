import json
import math

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


def save_manga(manga):
    with open(SAVE_FILE, "w") as f:
        json.dump(manga, f, indent=2, allow_nan=False)


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
    if title not in manga:
        print(f"Adding {title} at chapter {chapter}")
    elif manga[title] == chapter:
        print(f"{title} is already at chapter {chapter}")
        return
    else:
        print(f"Updating {title}: chapter {manga[title]} -> {chapter}")
    manga[title] = chapter
    save_manga(manga)


def show_library(manga):
    if not manga:
        print("Nothing tracked yet.")
        return
    width = max(len(name) for name in manga)
    for name, progress in sorted(manga.items(), key=lambda entry: entry[0].casefold()):
        print(f"  {name:<{width}}  chapter {progress}")


def remove_manga(manga):
    if not manga:
        print("Nothing tracked yet.")
        return
    title = get_title(manga)
    if title not in manga:
        print(f"{title} isn't being tracked.")
        return
    answer = prompt(f"Remove {title} at chapter {manga[title]}? [y/N] ")
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
