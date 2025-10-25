import os
from urllib.parse import quote
from dotenv import load_dotenv
from serpapi import GoogleSearch


load_dotenv()
SERP_API_KEY = os.getenv("SERP_API_KEY")


def _extract_reference_links(detail):
    """Return a flat list of citation links (patent + non-patent)."""
    links = []

    print(detail.get('title'))
    # 1) Patent citations → build Google Patents URLs from publication numbers
    for c in (detail.get("patent_citations") or {}).get("original", []) or []:
        if isinstance(c, dict):
            pub = c.get("publication_number") or c.get("patent_number")
            if pub:
                links.append(f"https://patents.google.com/patent/{pub}/en")
        elif isinstance(c, str):
            links.append(f"https://patents.google.com/patent/{c}/en")

    print(f"Patent citations found: {len(links)}")
    # 2) Non-patent citations → use link/url if present, else skip
    for c in detail.get("non_patent_citations") or []:
        if isinstance(c, dict):
            link = c.get("link") or c.get("url")
            if link:
                links.append(link)

    print(f"Total citations found: {len(links)}")
    return links



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
