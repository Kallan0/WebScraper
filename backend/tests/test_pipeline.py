import pytest
from app.services.cleaner import clean_text
from app.services.extractor import extract_content, ExtractedContent
from app.services.classifier import classify_content


def page(**changes):
    values = dict(text='', title='A useful article', description='', paragraph_count=5,
                  heading_count=2, link_ratio=0.05, semantic_types=frozenset(), login_form=False)
    return ExtractedContent(**(values | changes))


def test_cleaning_preserves_content_and_removes_noise():
    assert clean_text('Menu\nHello    world &amp; friends.\n\nNext paragraph.') == 'Hello world & friends.\n\nNext paragraph.'
    assert len(clean_text('A' * 200, 100)) == 100


@pytest.mark.parametrize('html', ['', '<html><body></body></html>', '<html><body><p>Broken markup'])
def test_empty_and_malformed_html(html):
    assert isinstance(extract_content(html).text, str)


def test_extraction_removes_noise_and_preserves_metadata():
    result = extract_content('<title>News story</title><nav>Buy now</nav><article><h1>Research</h1>'
                             '<p>Researchers published a useful discovery for the community.</p>'
                             '<p>The results show an improvement in daily life.</p></article><script>secret()</script>')
    assert result.title == 'News story'
    assert 'Buy now' not in result.text
    assert 'secret()' not in result.text
    assert 'Researchers' in result.text


def test_fallback(monkeypatch):
    monkeypatch.setattr('app.services.extractor.trafilatura.extract', lambda *a, **kw: None)
    result = extract_content('<main><p>Useful information.</p><p>Additional context.</p></main>')
    assert 'Useful information.' in result.text


@pytest.mark.parametrize(('features', 'category'), [
    ({}, 'article'),
    ({'title': 'API reference documentation'}, 'documentation'),
    ({'semantic_types': frozenset({'product'})}, 'product'),
    ({'semantic_types': frozenset({'newsarticle'})}, 'news'),
    ({'semantic_types': frozenset({'blogposting'})}, 'blog'),
    ({'paragraph_count': 1}, 'unknown'),
])
def test_classifier_categories(features, category):
    result = classify_content(page(**features), 'This is a meaningful sentence with facts. ' * 60)
    assert result.content_type == category
    assert result.suitable


@pytest.mark.parametrize(('features', 'text'), [
    ({}, 'Too short.'),
    ({'link_ratio': 0.9, 'paragraph_count': 1}, 'A directory link. ' * 30),
    ({'login_form': True, 'title': 'Sign in'}, 'Please log in to continue. ' * 30),
    ({'paragraph_count': 0}, 'Fragment ' * 60),
])
def test_unsuitable_content(features, text):
    assert not classify_content(page(**features), text).suitable


def test_short_nonempty_extraction_retries_dom(monkeypatch):
    monkeypatch.setattr('app.services.extractor.trafilatura.extract', lambda *a, **kw: 'A tiny headline')
    prose = 'The research describes meaningful findings in community health. Important evidence supports its conclusions. '
    result = extract_content('<main><div>' + prose * 8 + '</div></main>')
    assert prose.strip() in result.text
    assert len(result.text) > 300
    assert classify_content(result, clean_text(result.text)).suitable


def test_article_header_is_preserved(monkeypatch):
    monkeypatch.setattr('app.services.extractor.trafilatura.extract', lambda *a, **kw: '')
    result = extract_content('<header>Site navigation</header><main><article><header>'
                             '<h1>Important article headline</h1></header><p>Article text.</p>'
                             '</article></main>')
    assert 'Important article headline' in result.text
    assert 'Site navigation' not in result.text


def test_blog_index_uses_all_post_cards(monkeypatch):
    monkeypatch.setattr('app.services.extractor.trafilatura.extract', lambda *a, **kw: 'Just one headline')
    cards = ''.join(f'<a href="/post/{i}"><h2>New research explains important community improvements number {i}</h2>'
                    '<span>Researchers share findings from a long study.</span><time>January 2026</time></a>'
                    for i in range(4))
    result = extract_content('<title>Blog | Research</title><main>' + cards + '</main>')
    assert result.listing_count == 4
    assert 'number 0' in result.text and 'number 3' in result.text
    classification = classify_content(result, clean_text(result.text))
    assert classification.content_type == 'blog_index'
    assert classification.suitable


def test_simple_link_directory_remains_unsuitable():
    result = extract_content('<title>Link directory</title><main>' + ''.join(
        '<a href="/item">Directory link without article information.</a>' for _ in range(20)) + '</main>')
    assert not classify_content(result, clean_text(result.text)).suitable
