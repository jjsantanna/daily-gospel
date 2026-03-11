#!/usr/bin/env python3
"""Fetch today's Catholic daily gospel reading from Universalis.
Outputs two lines: the gospel reference, then the full text."""
import urllib.request
import re
import sys

def fetch_gospel():
    url = "https://universalis.com/today/mass.htm"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return None, None

    # Extract Gospel section
    m = re.search(
        r'Gospel(.*?)(?=<h[23]|Communion|Reflection|Prayer after Communion|$)',
        html, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return None, None

    raw = m.group(1)

    # Decode HTML entities
    raw = raw.replace('&#8216;', '\u2018').replace('&#8217;', '\u2019') \
             .replace('&#8220;', '\u201c').replace('&#8221;', '\u201d') \
             .replace('&amp;', '&').replace('&nbsp;', ' ')

    text = re.sub(r'<[^>]+>', ' ', raw)
    text = re.sub(r'\s+', ' ', text).strip()

    # Extract reference (e.g. "Matthew 5:17-19" or "John 3:16-21")
    ref_match = re.search(
        r'\b(Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|'
        r'Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|'
        r'James|Peter|John|Jude|Revelation|Genesis|Exodus|Psalms?|Isaiah|Jeremiah|'
        r'Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|'
        r'Zephaniah|Haggai|Zechariah|Malachi)\s+\d+:\d+[\d\-,]*',
        text
    )
    reference = ref_match.group(0) if ref_match else "Daily Gospel"

    return reference, text[:2000]

if __name__ == "__main__":
    reference, text = fetch_gospel()
    if text:
        print(f"REFERENCE: {reference}")
        print(f"TEXT: {text}")
    else:
        print("Could not fetch gospel today.")
        sys.exit(1)
