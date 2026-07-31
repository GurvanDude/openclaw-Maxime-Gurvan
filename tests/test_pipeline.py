"""Tests unitaires pour dataharvest.pipeline (GenericPipeline, PaginationPipeline)."""

from types import SimpleNamespace

from dataharvest.pipeline import GenericPipeline, PaginationPipeline

SELECTORS = {
    "titre": "h2.post-title a",
    "url": "h2.post-title a",
    "date": "time[datetime]",
    "categorie": ".cat-links a",
}

HTML_TWO_ARTICLES = """
<html><body>
<article>
  <h2 class="post-title"><a href="/article-1">Titre 1</a></h2>
  <time datetime="2024-01-01">1 janvier</time>
  <span class="cat-links"><a>Actu</a></span>
</article>
<article>
  <h2 class="post-title"><a href="https://example.com/article-2">Titre 2</a></h2>
  <time datetime="2024-01-02">2 janvier</time>
  <span class="cat-links"><a>Tech</a></span>
</article>
</body></html>
"""


def make_pagination(pattern="/page/{n}/", start=1, max_pages=3):
    return SimpleNamespace(pattern=pattern, start=start, max_pages=max_pages)


# ---- GenericPipeline -------------------------------------------------------


def test_process_returns_list_on_empty_html():
    pipeline = GenericPipeline(SELECTORS)

    result = pipeline.process("")

    assert result == []


def test_process_returns_list_when_no_selector_matches():
    pipeline = GenericPipeline({"titre": ".ne-existe-pas"})

    result = pipeline.process("<html><body><p>rien ici</p></body></html>")

    assert result == []


def test_process_does_not_raise_when_a_selector_finds_nothing():
    selectors = dict(SELECTORS)
    selectors["auteur"] = ".author"  # ne matche jamais dans HTML_TWO_ARTICLES
    pipeline = GenericPipeline(selectors)

    result = pipeline.process(HTML_TWO_ARTICLES)

    assert len(result) == 2
    assert result[0]["auteur"] == ""
    assert result[1]["auteur"] == ""


def test_process_extracts_titre_date_categorie():
    pipeline = GenericPipeline(SELECTORS)

    result = pipeline.process(HTML_TWO_ARTICLES)

    assert result[0]["titre"] == "Titre 1"
    assert result[0]["date"] == "2024-01-01"
    assert result[0]["categorie"] == "Actu"
    assert result[1]["titre"] == "Titre 2"


def test_process_resolves_relative_urls_with_base_url():
    pipeline = GenericPipeline(SELECTORS)

    result = pipeline.process(HTML_TWO_ARTICLES, base_url="https://blogdumoderateur.com/")

    assert result[0]["url"] == "https://blogdumoderateur.com/article-1"
    # une URL deja absolue n'est pas modifiee
    assert result[1]["url"] == "https://example.com/article-2"


def test_process_keeps_relative_url_as_is_without_base_url():
    pipeline = GenericPipeline(SELECTORS)

    result = pipeline.process(HTML_TWO_ARTICLES)

    assert result[0]["url"] == "/article-1"


def test_generic_pipeline_next_page_url_is_always_none():
    pipeline = GenericPipeline(SELECTORS)

    assert pipeline.next_page_url(HTML_TWO_ARTICLES, "https://example.com/") is None


def test_process_prefers_title_attribute_over_truncated_text():
    html = """
    <article class="product_pod">
      <h3><a href="/book-1" title="A Very Long Full Book Title">A Very Long F...</a></h3>
    </article>
    """
    pipeline = GenericPipeline({"titre": "h3 a"})

    result = pipeline.process(html)

    assert result[0]["titre"] == "A Very Long Full Book Title"


def test_process_reads_content_attribute_of_meta_tags():
    html = """
    <div class="quote">
      <span class="text">Une citation</span>
      <meta class="keywords" content="change,deep-thoughts,thinking">
    </div>
    """
    pipeline = GenericPipeline({"citation": "span.text", "tags": ".keywords"})

    result = pipeline.process(html)

    assert result[0]["tags"] == "change,deep-thoughts,thinking"


def test_process_broadcasts_single_match_selector_to_all_items():
    html = """
    <ul class="breadcrumb"><li class="active">Mystery</li></ul>
    <article><h3><a href="/b1">Book 1</a></h3></article>
    <article><h3><a href="/b2">Book 2</a></h3></article>
    """
    selectors = {"titre": "article h3 a", "categorie": "ul.breadcrumb li.active"}
    pipeline = GenericPipeline(selectors)

    result = pipeline.process(html)

    assert len(result) == 2
    assert result[0]["categorie"] == "Mystery"
    assert result[1]["categorie"] == "Mystery"


# ---- PaginationPipeline ----------------------------------------------------


def test_pagination_returns_none_when_pattern_is_null():
    pipeline = PaginationPipeline(SELECTORS, make_pagination(pattern=None))

    result = pipeline.next_page_url(HTML_TWO_ARTICLES, "https://example.com/")

    assert result is None


def test_pagination_returns_none_when_page_has_no_items():
    pipeline = PaginationPipeline(SELECTORS, make_pagination())

    result = pipeline.next_page_url("<html><body>vide</body></html>", "https://example.com/")

    assert result is None


def test_pagination_builds_next_url_from_base_url():
    pipeline = PaginationPipeline(SELECTORS, make_pagination(max_pages=3))

    result = pipeline.next_page_url(HTML_TWO_ARTICLES, "https://example.com")

    assert result == "https://example.com/page/2/"


def test_pagination_builds_next_url_replacing_existing_page_segment():
    pipeline = PaginationPipeline(SELECTORS, make_pagination(max_pages=5))

    first = pipeline.next_page_url(HTML_TWO_ARTICLES, "https://example.com")
    second = pipeline.next_page_url(HTML_TWO_ARTICLES, first)

    assert first == "https://example.com/page/2/"
    assert second == "https://example.com/page/3/"


def test_pagination_stops_at_max_pages():
    pipeline = PaginationPipeline(SELECTORS, make_pagination(max_pages=2))

    first = pipeline.next_page_url(HTML_TWO_ARTICLES, "https://example.com")
    second = pipeline.next_page_url(HTML_TWO_ARTICLES, first)

    assert first == "https://example.com/page/2/"
    assert second is None
