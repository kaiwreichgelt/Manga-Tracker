def get_chapter():
    # Accepts normal chapters (24) and special chapters (24.5)
    while True:
        answer = input("Chapter you're on: ")
        try:
            chapter = float(answer)
        except ValueError:
            print("Please enter a number, like 24 or 24.5.")
            continue
        if chapter.is_integer():
            return int(chapter)
        return chapter


manga = {"Frieren": 0, "One Piece": 0, "Naruto": 0}
title = input("Manga name: ")
chapter = get_chapter()
manga[title] = chapter
for title, chapter in manga.items():
    print(f"{title}: chapter {chapter}")
