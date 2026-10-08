from dataclasses import dataclass
import json
import re

from bs4 import BeautifulSoup
import trafilatura


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    title: str | None
    description: str
    paragraph_count: int
    heading_count: int
    link_ratio: float
    semantic_types: frozenset[str]
    login_form: bool
    listing_count: int = 0


def _schema_types(value):
    if isinstance(value, dict):
        kind = value.get('@type', [])
        yield from ([kind] if isinstance(kind, str) else kind)
        for nested in value.values():
            yield from _schema_types(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _schema_types(nested)


def _extract(html: str, **options) -> str:
    try:
        return trafilatura.extract(html, include_comments=False, include_tables=True, **options) or ''
    except (ValueError, TypeError):
        return ''


def extract_content(html: str) -> ExtractedContent:
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else None
    description_tag = soup.find('meta', attrs={'name': 'description'})
    description = description_tag.get('content', '') if description_tag else ''
    semantic_types = set()
    for script in soup.find_all('script', attrs={'type': 'application/ld+json'}):
        try:
            semantic_types.update(str(t).lower() for t in _schema_types(json.loads(script.get_text())))
        except (ValueError, TypeError):
            pass
    og_type = soup.find('meta', attrs={'property': 'og:type'})
    if og_type:
        semantic_types.add(str(og_type.get('content', '')).lower())
    login_form = soup.find('input', attrs={'type': 'password'}) is not None
    for tag in soup.select('script, style, noscript, nav, footer, form, [hidden], [aria-hidden="true"]'):
        tag.decompose()
    # Article headers can contain the headline and introduction. Keep them;
    # remove only site-wide headers and sidebars outside the readable region.
    for tag in soup.select('header, aside'):
        if tag.find_parent(['main', 'article']) is None:
            tag.decompose()
    main = soup.find('main') or soup.find('article') or soup.body or soup
    visible_text = main.get_text(' ', strip=True)
    linked_chars = sum(len(a.get_text(' ', strip=True)) for a in main.find_all('a'))
    listings = list(dict.fromkeys(
        a.get_text(' ', strip=True) for a in main.find_all('a')
        if a.find(['h2', 'h3']) is not None and len(a.get_text(' ', strip=True).split()) >= 6
    ))
    is_blog_index = (
        re.search(r'\b(blog|newsroom|news|updates)\b', title or '', re.IGNORECASE)
        and len(listings) >= 3
        and not semantic_types.intersection({'article', 'newsarticle', 'blogposting'})
    )
    if is_blog_index:
        # A post index is useful content, but never pretend it contains the articles.
        text = '\n\n'.join(listings)
    else:
        cleaned_html = str(main)
        text = _extract(cleaned_html, favor_precision=True)
        # Nonempty extraction can still be only a caption or a headline.
        if len(text.strip()) < 300:
            candidates = [text, _extract(cleaned_html, favor_recall=True)]
            blocks = main.find_all(['p', 'h1', 'h2', 'h3', 'li', 'pre', 'blockquote'])
            block_text = '\n'.join(block.get_text(' ', strip=True) for block in blocks)
            # Div/span-based layouts may have no meaningful paragraph tags.
            candidates.extend([block_text, main.get_text('\n', strip=True)])
            text = max(candidates, key=lambda candidate: len(candidate.strip()))
    return ExtractedContent(
        text=text, title=title, description=str(description),
        paragraph_count=len(main.find_all('p')),
        heading_count=len(main.find_all(['h1', 'h2', 'h3'])),
        link_ratio=min(1.0, linked_chars / max(1, len(visible_text))),
        semantic_types=frozenset(semantic_types), login_form=login_form,
        listing_count=len(listings) if is_blog_index else 0,
    )
