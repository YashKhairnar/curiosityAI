from app.utils.utils_fetch_arxiv import fetch_from_arxiv
from app.utils.utils_fetch_google_patents import fetch_from_google_patents


def fetch_with_fallback(fetch_fn, source_name, keywords, max_results):
    """Safely call a fetch function and handle errors gracefully."""
    try:
        results = fetch_fn(keywords, max_results=max_results)
        print(f"   → {len(results)} {source_name} results found.")
        return results
    except Exception as e:
        print(f"   ⚠️ Error fetching from {source_name}: {e}")
        return []


def process_keywords(keywords, max_results):
    """Fetch papers and patents for a single keyword."""
    print(f"\n🔍 Searching for: {keywords}")
    arxiv_results = fetch_with_fallback(fetch_from_arxiv, "arXiv", keywords, max_results=max_results)
    patent_results = fetch_with_fallback(fetch_from_google_patents, "Google Patents", keywords, max_results=max_results)

    # Attach keyword to each result
    return [
        {**item} for item in (arxiv_results + patent_results)
    ]
