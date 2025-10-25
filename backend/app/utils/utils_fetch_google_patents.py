import os
from serpapi import GoogleSearch


SERP_API_KEY = os.getenv("SERP_API_KEY")


def fetch_from_google_patents(keywords, max_results):
    """Fetch Google Patents results using SerpApi."""

    # Step 1: search Google Patents
    query = " OR ".join([str(k) for k in keywords])
    search_params = {
        "engine": "google_patents",
        "q": "(" + query + ")",
        "num": max_results,
        "api_key": SERP_API_KEY,
    }
    search = GoogleSearch(search_params).get_dict()

    results = []
    for item in search.get("organic_results", [])[:max_results]:
        patent_id = item.get("patent_id")
        link = item.get("patent_link")

        if not patent_id:
            continue

        # Step 2: fetch full patent details
        details_params = {
            "engine": "google_patents_details",
            "patent_id": patent_id,
            "api_key": SERP_API_KEY,
        }
        detail = GoogleSearch(details_params).get_dict()

        title = detail.get("title")
        abstract = detail.get("abstract")
        # references = _extract_reference_links(detail)
        references = []

        results.append({
            "title": title,
            "summary": abstract,
            "link": link,
            "references": references
        })

    return results
