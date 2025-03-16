import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def crawl_website(start_url):
    """
    Crawls the website starting from start_url and returns a list of all unique internal links.
    """
    visited = set()      # Track visited URLs to avoid revisiting
    links_found = set()  # Use a set to store unique links
    to_visit = [start_url]

    # Get the domain of the starting URL to restrict crawling to the same domain
    domain = urlparse(start_url).netloc

    while to_visit:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            response = requests.get(current_url, timeout=5)
            # Proceed only if the content is HTML
            if "text/html" not in response.headers.get("Content-Type", ""):
                continue
        except Exception as e:
            print(f"Failed to fetch {current_url}: {e}")
            continue

        soup = BeautifulSoup(response.content, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Convert relative URL to absolute URL
            full_url = urljoin(current_url, href)
            # Ensure the link is within the same domain
            if urlparse(full_url).netloc != domain:
                continue
            # Remove any URL fragments (e.g., "#section") to avoid duplicates
            full_url = full_url.split("#")[0]
            if full_url not in visited and full_url not in to_visit:
                links_found.add(full_url)
                to_visit.append(full_url)

    # Return the links as a list
    return list(links_found)

if __name__ == "__main__":
    start_url = "https://example.com"  # Replace with your target URL
    all_links = crawl_website(start_url)

    print("Found links:")
    for link in all_links:
        print(link)
