"""A window for the manga tracker.

The saving, loading and validation all live in tracker.py, so the command line
and this window always agree about what the library means.
"""

import contextlib
import io
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import tracker

BAR_WIDTH = 12


def progress_bar(share):
    filled = max(0, min(BAR_WIDTH, round(share * BAR_WIDTH)))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def chapter_text(entry):
    chapter = tracker.format_number(entry["chapter"])
    if entry["total"] is None:
        return chapter
    return f"{chapter} / {tracker.format_number(entry['total'])}"


def share_text(entry):
    if entry["total"] is None:
        return ""
    share = entry["chapter"] / entry["total"]
    return f"{progress_bar(share)}  {share:.0%}"


class EditDialog(tk.Toplevel):
    """Asks for a title, chapter and total. Returns None if cancelled."""

    def __init__(self, parent, manga, title=None):
        super().__init__(parent)
        self.manga = manga
        self.original = title
        self.entry = manga.get(title) if title else None
        self.result = None

        self.title("Edit manga" if title else "Add manga")
        self.transient(parent)
        self.resizable(False, False)

        body = ttk.Frame(self, padding=16)
        body.grid(sticky="nsew")

        current = tracker.format_number(self.entry["chapter"]) if self.entry else ""
        total = ""
        if self.entry and self.entry["total"] is not None:
            total = tracker.format_number(self.entry["total"])

        self.name_var = tk.StringVar(value=title or "")
        self.chapter_var = tk.StringVar(value=current)
        self.total_var = tk.StringVar(value=total)

        hint = "or +1 to step" if self.entry else "e.g. 24 or 24.5"
        rows = [
            ("Title", self.name_var, ""),
            ("Chapter you're on", self.chapter_var, hint),
            ("Chapters in total", self.total_var, "blank if unknown"),
        ]
        self.fields = {}
        for row, (label, variable, note) in enumerate(rows):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", pady=4)
            field = ttk.Entry(body, textvariable=variable, width=28)
            field.grid(row=row, column=1, sticky="ew", padx=(10, 6), pady=4)
            self.fields[label] = field
            ttk.Label(body, text=note, foreground="gray").grid(row=row, column=2, sticky="w")

        self.error = ttk.Label(body, text="", foreground="#b00020", wraplength=320)
        self.error.grid(row=len(rows), column=0, columnspan=3, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=len(rows) + 1, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Save", command=self.save).grid(row=0, column=1)

        self.bind("<Return>", lambda event: self.save())
        self.bind("<Escape>", lambda event: self.destroy())
        # Editing usually means changing the chapter, so start the cursor there.
        self.fields["Chapter you're on" if self.entry else "Title"].focus_set()

    def fail(self, message):
        self.error.config(text=message)
        return None

    def save(self):
        name = self.name_var.get().strip()
        if not name:
            return self.fail("Please enter a manga name.")
        # Renaming onto a title that already exists would silently merge them.
        clash = [
            other for other in self.manga
            if other.casefold() == name.casefold() and other != self.original
        ]
        if clash:
            return self.fail(f"{clash[0]} is already in your library.")

        current = self.entry["chapter"] if self.entry else None
        try:
            chapter = tracker.parse_chapter_input(self.chapter_var.get(), current)
        except ValueError as problem:
            return self.fail(str(problem))

        total = None
        raw_total = self.total_var.get().strip()
        if raw_total:
            try:
                total = tracker.parse_chapter_input(raw_total)
            except ValueError:
                return self.fail("Please enter a total number of chapters, or leave it blank.")
            if total == 0:
                return self.fail("Please enter a total above 0.")
            if total < chapter:
                return self.fail(
                    f"You're on chapter {tracker.format_number(chapter)}, "
                    f"so the total can't be lower."
                )

        self.result = {"title": name, "chapter": chapter, "total": total}
        self.destroy()


class App(ttk.Frame):
    def __init__(self, parent, manga):
        super().__init__(parent, padding=12)
        self.parent = parent
        self.manga = manga
        self.visible = []
        self.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Filter").grid(row=0, column=0, padx=(0, 8))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self.refresh(keep_selection=False))
        self.filter_box = ttk.Entry(top, textvariable=self.filter_var)
        self.filter_box.grid(row=0, column=1, sticky="ew")
        ttk.Button(top, text="Clear", command=lambda: self.filter_var.set("")).grid(
            row=0, column=2, padx=(6, 0)
        )

        columns = ("chapter", "share", "updated")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", height=14)
        self.tree.heading("#0", text="Title")
        self.tree.heading("chapter", text="Chapter")
        self.tree.heading("share", text="Progress")
        self.tree.heading("updated", text="Last updated")
        self.tree.column("#0", width=210, anchor="w")
        self.tree.column("chapter", width=110, anchor="center")
        self.tree.column("share", width=170, anchor="w")
        self.tree.column("updated", width=130, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        buttons = ttk.Frame(self)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Add manga", command=self.add).grid(row=0, column=0)
        self.bump_button = ttk.Button(buttons, text="+1 chapter", command=self.bump)
        self.bump_button.grid(row=0, column=1, padx=(6, 2))
        self.drop_button = ttk.Button(buttons, text="−1 chapter", command=self.drop)
        self.drop_button.grid(row=0, column=2, padx=(2, 6))
        self.edit_button = ttk.Button(buttons, text="Edit", command=self.edit)
        self.edit_button.grid(row=0, column=3)
        self.remove_button = ttk.Button(buttons, text="Remove", command=self.remove)
        self.remove_button.grid(row=0, column=4, padx=6)

        self.summary = ttk.Label(self, text="", foreground="gray")
        self.summary.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.status = ttk.Label(self, text="", foreground="gray")
        self.status.grid(row=4, column=0, columnspan=2, sticky="w")

        self.tree.bind("<Double-1>", lambda event: self.edit())
        self.tree.bind("<Return>", lambda event: self.edit())
        self.tree.bind("<Delete>", lambda event: self.remove())
        self.tree.bind("<plus>", lambda event: self.bump())
        self.tree.bind("<KP_Add>", lambda event: self.bump())
        self.tree.bind("<minus>", lambda event: self.drop())
        self.tree.bind("<KP_Subtract>", lambda event: self.drop())
        self.tree.bind("<<TreeviewSelect>>", lambda event: self.sync_buttons())
        parent.bind("<Control-n>", lambda event: self.add())
        parent.bind("<Control-f>", lambda event: self.filter_box.focus_set())

        self.refresh()

    def selected_title(self):
        chosen = self.tree.selection()
        return chosen[0] if chosen else None

    def sync_buttons(self):
        title = self.selected_title()
        state = "normal" if title else "disabled"
        for button in (self.bump_button, self.edit_button, self.remove_button):
            button.config(state=state)
        # There's nothing below chapter 0 to step down to.
        at_start = title is not None and self.manga[title]["chapter"] == 0
        self.drop_button.config(state="disabled" if at_start else state)

    def say(self, message):
        self.status.config(text=message)

    def refresh(self, keep_selection=True):
        remembered = self.selected_title() if keep_selection else None
        query = self.filter_var.get().strip()
        if query:
            names = tracker.find_matches(self.manga, query)
        else:
            names = sorted(self.manga, key=str.casefold)
        self.visible = names

        self.tree.delete(*self.tree.get_children())
        for name in names:
            entry = self.manga[name]
            self.tree.insert(
                "", "end", iid=name, text=name,
                values=(chapter_text(entry), share_text(entry),
                        tracker.describe_age(entry["updated"])),
            )
        if remembered in names:
            self.tree.selection_set(remembered)
            self.tree.focus(remembered)
        self.update_summary(query, len(names))
        self.sync_buttons()

    def update_summary(self, query, shown):
        if not self.manga:
            self.summary.config(text="Nothing tracked yet. Add your first manga.")
            return
        read = sum(entry["chapter"] for entry in self.manga.values())
        titles = f"{len(self.manga)} title{'' if len(self.manga) == 1 else 's'}"
        known = [e for e in self.manga.values() if e["total"] is not None]
        text = f"{titles}, {tracker.format_number(read)} chapters read"
        if known:
            goal = sum(e["total"] for e in known)
            if len(known) == len(self.manga):
                text = (f"{titles}, {tracker.format_number(read)} of "
                        f"{tracker.format_number(goal)} chapters read ({read / goal:.0%})")
            else:
                # Partial totals can't speak for the whole library, so name the scope.
                counted = sum(e["chapter"] for e in known)
                text += (f"  ·  {tracker.format_number(counted)} of "
                         f"{tracker.format_number(goal)} across the {len(known)} "
                         f"with known totals ({counted / goal:.0%})")
        if query:
            text += f"  ·  showing {shown} of {len(self.manga)}"
        self.summary.config(text=text)

    def save(self):
        try:
            tracker.save_manga(self.manga)
            return True
        except OSError as problem:
            messagebox.showerror("Couldn't save", f"{tracker.SAVE_FILE} wasn't written:\n\n{problem}")
            return False

    def add(self):
        dialog = EditDialog(self.parent, self.manga)
        self.wait_window(dialog)
        if not dialog.result:
            return
        result = dialog.result
        self.manga[result["title"]] = {
            "chapter": result["chapter"],
            "total": result["total"],
            "updated": datetime.now(),
        }
        if self.save():
            self.filter_var.set("")
            self.refresh()
            self.tree.selection_set(result["title"])
            self.say(f"Added {result['title']} at chapter {tracker.format_number(result['chapter'])}")

    def edit(self):
        title = self.selected_title()
        if not title:
            return
        before = self.manga[title]
        dialog = EditDialog(self.parent, self.manga, title)
        self.wait_window(dialog)
        if not dialog.result:
            return
        result = dialog.result
        moved = result["chapter"] != before["chapter"]
        replacement = {
            "chapter": result["chapter"],
            "total": result["total"],
            # Only a chapter change counts as progress, so fixing a title or a
            # total on its own leaves the timestamp alone.
            "updated": datetime.now() if moved else before["updated"],
        }
        # Rebuilt rather than popped and reinserted, so a rename keeps its
        # place in the saved file instead of jumping to the end.
        rebuilt = {
            (result["title"] if name == title else name):
                (replacement if name == title else entry)
            for name, entry in self.manga.items()
        }
        self.manga.clear()
        self.manga.update(rebuilt)
        if self.save():
            self.refresh()
            self.tree.selection_set(result["title"])
            if result["title"] != title:
                self.say(f"Renamed {title} to {result['title']}")
            elif moved:
                self.say(f"{result['title']}: chapter {tracker.format_number(before['chapter'])} "
                         f"→ {tracker.format_number(result['chapter'])}")
            else:
                self.say(f"Updated {result['title']}")

    def step(self, amount):
        title = self.selected_title()
        if not title:
            return
        entry = self.manga[title]
        try:
            chapter = tracker.parse_chapter_input(f"{amount:+g}", entry["chapter"])
        except ValueError:
            # Only reachable by stepping down from chapter 0.
            self.say(f"{title} is already at chapter 0.")
            return
        entry["chapter"] = chapter
        entry["updated"] = datetime.now()
        if self.save():
            self.refresh()
            self.say(f"{title}: now on chapter {tracker.format_number(chapter)}")

    def bump(self):
        self.step(1)

    def drop(self):
        self.step(-1)

    def remove(self):
        title = self.selected_title()
        if not title:
            return
        entry = self.manga[title]
        if not messagebox.askyesno(
            "Remove manga",
            f"Remove {title}, at chapter {chapter_text(entry)}?\n\nThis can't be undone.",
            default="no",
        ):
            return
        del self.manga[title]
        if self.save():
            self.refresh()
            self.say(f"Removed {title}")


def main():
    # tracker reports data problems by printing, which a window would swallow.
    notes = io.StringIO()
    try:
        with contextlib.redirect_stdout(notes):
            manga = tracker.load_manga()
    except SystemExit as problem:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Can't open your library", str(problem))
        return

    root = tk.Tk()
    root.title("Manga Tracker")
    root.minsize(660, 420)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    app = App(root, manga)
    warnings = notes.getvalue().strip()
    if warnings:
        app.say(warnings.replace("\n", "  ·  "))
    root.mainloop()


if __name__ == "__main__":
    main()
