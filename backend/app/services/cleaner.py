import html
import re
import unicodedata

NOISE = {'accept cookies', 'reject cookies', 'all rights reserved', 'skip to content', 'menu'}


def clean_text(text: str, max_characters: int = 50_000) -> str:
    text = unicodedata.normalize('NFKC', html.unescape(text))
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    paragraphs = []
    for line in text.splitlines():
        line = re.sub(r'\s+', ' ', line).strip()
        if not line or len(line) < 3 or line.lower().rstrip('.:') in NOISE:
            continue
        paragraphs.append(line)
    return '\n\n'.join(paragraphs)[:max_characters].rstrip()
