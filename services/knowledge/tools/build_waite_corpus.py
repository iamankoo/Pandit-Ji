"""Parse the Wikisource transcription of Waite's *Pictorial Key to the Tarot*, Part III.

Maintainer tool (needs network, not run in CI): fetches the rendered text of
`The Pictorial Key to the Tarot/Part 3` from the MediaWiki API, extracts the
56 Lesser Arcana entries (section 2) and the 22 Greater Arcana entries
(section 3) and writes one JSON line per card to
`content/corpus/waite_pictorial_key_part3.jsonl`.

The card text is Waite's own (public domain); it is whitespace-normalised and
otherwise left exactly as transcribed. Nothing is translated, paraphrased or
generated.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import urllib.request

API = (
    "https://en.wikisource.org/w/api.php?action=parse&page="
    "The_Pictorial_Key_to_the_Tarot/Part_3&prop=text&format=json&formatversion=2"
    "&disablelimitreport=1"
)
SUITS = {"WANDS": "wands", "CUPS": "cups", "SWORDS": "swords", "PENTACLES": "pentacles"}
RANKS = [
    "King", "Queen", "Knight", "Page", "Ten", "Nine", "Eight", "Seven",
    "Six", "Five", "Four", "Three", "Two", "Ace",
]  # fmt: skip
TRUMP_RE = re.compile(r"^(\d+|Zero)\. ([A-Za-z ]+?)\.—(.*)$")


def fetch_text() -> str:
    req = urllib.request.Request(API, headers={"User-Agent": "PanditJi-maintainer/1.0"})
    raw = json.load(urllib.request.urlopen(req, timeout=120))["parse"]["text"]
    raw = re.sub(r"<style.*?</style>", "", raw, flags=re.S)
    raw = re.sub(r'<span class="pagenum[^>]*>.*?</span>', "", raw, flags=re.S)
    raw = re.sub(r"<br\s*/?>", "\n", raw)
    raw = re.sub(r"</(p|div|h\d)>", "\n\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", "", raw))
    return re.sub(r"\n{3,}", "\n\n", text)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\u00ad", "")).strip()


def main(out_path: str) -> None:
    text = fetch_text()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    lesser = text[text.index("§  2.THE LESSER ARCANA") : text.index("§ 3\n\nTHE GREATER ARCANA")]
    greater = text[
        text.index("THE GREATER ARCANA AND THEIR DIVINATORY MEANINGS") : text.index(
            "§ 4\n\nSOME ADDITIONAL MEANINGS"
        )
    ]
    cards: list[dict[str, object]] = []
    suit = ""
    blocks = [b for b in re.split(r"\n\s*\n", lesser) if b.strip()]
    i = 0
    pending: tuple[str, str] | None = None
    while i < len(blocks):
        b = blocks[i].strip()
        lines = [x.strip() for x in b.split("\n") if x.strip()]
        if lines and lines[0].startswith("THE SUIT OF "):
            suit = SUITS[lines[0].replace("THE SUIT OF ", "").strip()]
            rank = lines[1].strip() if len(lines) > 1 else ""
            pending = (suit, rank)
        elif len(lines) == 2 and lines[0] in SUITS and lines[1] in RANKS:
            pending = (SUITS[lines[0]], lines[1])
        elif pending and "Divinatory Meanings" in b:
            s, r = pending
            cards.append(
                {
                    "card_id": f"TAROT.{s.upper()}.{r.upper()}",
                    "arcana": "lesser",
                    "suit": s,
                    "rank": r.lower(),
                    "number": None,
                    "title": f"{r} of {s.capitalize()}"
                    if r != "Ace"
                    else f"Ace of {s.capitalize()}",
                    "section": "Part III §2",
                    "text": norm(b),
                }
            )
            pending = None
        elif pending and len(lines) == 1 and lines[0] in RANKS:
            pending = (pending[0], lines[0])
        i += 1
    for line in re.split(r"\n\s*\n", greater):
        m = TRUMP_RE.match(norm(line))
        if m:
            n = 0 if m.group(1) == "Zero" else int(m.group(1))
            name = m.group(2)
            cards.append(
                {
                    "card_id": f"TAROT.TRUMP.{n:02d}",
                    "arcana": "greater",
                    "suit": None,
                    "rank": None,
                    "number": n,
                    "title": name,
                    "section": "Part III §3",
                    "text": norm(m.group(3)),
                }
            )
    meta = {
        "_meta": {
            "source": "WAITE_PICTORIAL_KEY",
            "page": "The Pictorial Key to the Tarot/Part 3",
            "retrieved_via": "en.wikisource.org MediaWiki parse API",
            "rendered_text_sha256": digest,
            "lesser_count": sum(1 for c in cards if c["arcana"] == "lesser"),
            "greater_count": sum(1 for c in cards if c["arcana"] == "greater"),
        }
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False, sort_keys=True) + "\n")
        for c in cards:
            fh.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
    print(meta["_meta"])


if __name__ == "__main__":
    main(sys.argv[1])
