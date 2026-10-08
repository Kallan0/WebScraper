from dataclasses import dataclass
import re
from app.services.extractor import ExtractedContent


@dataclass(frozen=True)
class Classification:
    content_type: str
    suitable: bool
    reason: str | None = None


def classify_content(page: ExtractedContent, text: str) -> Classification:
    if len(text) < 300:
        return Classification('empty', False, 'This URL has too little readable text in its HTML. Try a direct article URL; pages that require JavaScript or sign-in may not expose their content.')
    metadata = f'{page.title or ""} {page.description}'.lower()
    if page.login_form and (page.paragraph_count < 3 or re.search(r'\b(log ?in|sign ?in)\b', metadata)):
        return Classification('unknown', False, 'Login pages cannot be summarized. Use a publicly readable webpage.')
    if page.listing_count >= 3:
        return Classification('blog_index', True)
    if page.link_ratio > 0.5 and (len(text) < 1500 or page.paragraph_count < 3):
        return Classification('landing_page', False, 'This page contains mostly links. Try an article or another content page.')
    if re.search(r'\b(documentation|api reference|developer guide|reference manual)\b', metadata):
        category = 'documentation'
    elif 'product' in page.semantic_types:
        category = 'product'
    elif 'newsarticle' in page.semantic_types or re.search(r'\bnews\b', metadata):
        category = 'news'
    elif 'blogposting' in page.semantic_types or re.search(r'\bblog\b', metadata):
        category = 'blog'
    elif 'article' in page.semantic_types or len(text) > 1500 and page.paragraph_count >= 3:
        category = 'article'
    elif page.link_ratio > 0.3:
        category = 'landing_page'
    else:
        category = 'unknown'
    # Unknown content can still be useful prose; reject fragments deterministically.
    sentences = len(re.findall(r'[.!?](?:\s|$)', text))
    if sentences < 2 and page.paragraph_count < 2:
        return Classification(category, False, 'Unable to find enough meaningful text to summarize.')
    return Classification(category, True)
