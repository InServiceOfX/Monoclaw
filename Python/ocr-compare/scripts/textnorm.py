#!/usr/bin/env python3
"""Repair Cyrillic homoglyphs that OCR produces for isolated Latin capitals.

On a scanned English textbook, Surya occasionally returns the Cyrillic letter
that looks identical to the intended Latin one -- U+0421 ES for C, U+0412 VE
for B, U+041D EN for H, U+041E O for O. It happens most on *isolated* capitals,
which in a propulsion text means exactly the places it hurts: chemical formulas
and symbols (C, H, O, B, N). `C_6H_5NH_2` with a Cyrillic C is not the same
string as the Latin one, so any downstream lookup silently misses.

Cyrillic ONLY. Greek is deliberately untouched: in this corpus Greek letters
are real mathematics (nu, theta, gamma, rho), not OCR noise, and mapping them
to Latin look-alikes would destroy content rather than repair it.

Usable as a module (`normalize`) or a filter (`textnorm.py < in > out`).
"""

import sys

# Cyrillic -> Latin, restricted to pairs that are visually identical in the
# fonts a scanner sees. Anything ambiguous is left alone on purpose.
CYRILLIC_TO_LATIN = {
    "А": "A", "В": "B", "Е": "E", "З": "3",
    "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "У": "Y",
    "Х": "X", "І": "I", "Ј": "J", "Ѕ": "S",
    "а": "a", "е": "e", "о": "o", "р": "p",
    "с": "c", "у": "y", "х": "x", "і": "i",
    "ј": "j", "ѕ": "s",
}

TABLE = str.maketrans(CYRILLIC_TO_LATIN)


def normalize(text):
    """Return text with Cyrillic look-alikes replaced by their Latin twins."""
    return text.translate(TABLE) if text else text


def count_homoglyphs(text):
    """How many characters normalize() would change. For reporting."""
    return sum(1 for ch in (text or "") if ch in CYRILLIC_TO_LATIN)


if __name__ == "__main__":
    data = sys.stdin.read()
    sys.stderr.write(f"replaced {count_homoglyphs(data)} Cyrillic homoglyphs\n")
    sys.stdout.write(normalize(data))
