import requests
import feedparser


def fetch_from_arxiv(keywords, max_results, enrich_references=True):
    """Fetch papers from arXiv using keyword search."""

    query = "+OR+".join([f"all:{k}" for k in keywords])
    base_url = "http://export.arxiv.org/api/query?"
    url = f"{base_url}search_query={query}&start=0&max_results={max_results}"

    response = requests.get(url)
    feed = feedparser.parse(response.text)

    papers = []
    for entry in feed.entries:
        ref_links = []

        # Add DOI link if available
        if "arxiv_doi" in entry:
            doi = entry.arxiv_doi
            doi_link = f"https://doi.org/{doi}"
            ref_links.append(doi_link)

            if enrich_references:
                ref_links.extend(fetch_references_from_crossref(doi))

        # Add all related arXiv links (PDF, etc.)
        for link in entry.get("links", []):
            href = link.get("href")
            if href and href not in ref_links:
                ref_links.append(href)

        papers.append({
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link,
            "references": ref_links
        })

    return papers


def fetch_references_from_crossref(doi):
    """Fetch referenced DOIs for a paper using CrossRef API."""
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return []
        data = response.json().get("message", {})
        refs = [ref.get("DOI") for ref in data.get("reference", []) if ref.get("DOI")]
        return [f"https://doi.org/{r}" for r in refs]
    except Exception as e:
        print(f"   ⚠️ CrossRef lookup failed for DOI {doi}: {e}")
        return []
