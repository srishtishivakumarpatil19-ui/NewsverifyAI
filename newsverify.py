import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

from urllib.parse import urlparse

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


# ==================================================
# STAGE 1: TEXT CLEANING AND KEYWORD EXTRACTION
# ==================================================

def clean_text(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_keywords(text):

    stop_words = {
        "the", "is", "are", "was", "were",
        "a", "an", "in", "on", "of", "and",
        "to", "for", "by", "with", "has",
        "have", "had", "this", "that",
        "from", "its", "it", "as", "at",
        "be", "been", "will", "after",
        "who", "what", "when", "where",
        "which", "their", "they", "he", "she"
    }

    words = re.findall(r'[a-zA-Z0-9]+', text.lower())

    return {
        word for word in words
        if len(word) > 2 and word not in stop_words
    }


# ==================================================
# SOURCE DOMAIN EXTRACTION
# ==================================================

def get_domain(url):

    try:
        host = urlparse(url).hostname

        if not host:
            return ""

        return host.lower().removeprefix("www.")

    except Exception:
        return ""


# ==================================================
# STAGE 1: NEWS SEARCHING
# DDGS + GOOGLE NEWS RSS BACKUP
# ==================================================

def search_news(headline):

    articles = []

    # FIRST METHOD: DDGS SEARCH

    print("\nTrying DDGS news search...")

    if DDGS is not None:

        try:
            with DDGS() as ddgs:
                results = ddgs.text(
                    headline,
                    max_results=8
                )

                articles = list(results)

            if articles:
                print("DDGS search successful.")
                return articles

        except Exception as error:
            print("DDGS search unavailable:", error)

    else:
        print("DDGS package is not installed.")

    # SECOND METHOD: GOOGLE NEWS RSS

    print("\nTrying Google News RSS backup...")

    try:

        query = urllib.parse.quote(headline)

        url = (
            "https://news.google.com/rss/search?q="
            + query
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            xml_data = response.read()

        root = ET.fromstring(xml_data)

        for item in root.findall(".//item"):

            title = item.findtext("title", "")
            description = item.findtext("description", "")
            link = item.findtext("link", "")

            if link:

                articles.append({
                    "title": title,
                    "body": description,
                    "href": link
                })

            if len(articles) >= 8:
                break

        if articles:
            print("Google News RSS search successful.")

        return articles

    except Exception as error:

        print("Google News RSS unavailable:", error)

        return []


# ==================================================
# REMOVE DUPLICATE ARTICLES
# ==================================================

def clean_articles(results):

    articles = []

    seen_urls = set()
    seen_titles = set()

    for result in results:

        title = clean_text(
            result.get("title", "No title")
        )

        description = clean_text(
            result.get("body", "")
        )

        link = str(result.get("href", "")).strip()

        if not link:
            continue

        domain = get_domain(link)

        if not domain:
            continue

        normalized_url = link.rstrip("/").lower()
        normalized_title = title.lower()

        if normalized_url in seen_urls:
            continue

        if normalized_title in seen_titles:
            continue

        seen_urls.add(normalized_url)
        seen_titles.add(normalized_title)

        articles.append({
            "title": title,
            "description": description,
            "link": link,
            "domain": domain
        })

    return articles


# ==================================================
# USER INPUT VALIDATION
# ==================================================

def get_article_numbers(prompt, valid_numbers):

    while True:

        value = input(prompt).strip()

        if not value:
            return []

        try:

            numbers = [
                int(x.strip())
                for x in value.split(",")
            ]

            if len(numbers) != len(set(numbers)):
                print("Duplicate article numbers are not allowed.")
                continue

            if any(n not in valid_numbers for n in numbers):
                print("Please enter valid article numbers.")
                continue

            return numbers

        except ValueError:

            print("Enter numbers separated by commas.")


# ==================================================
# MAIN PROGRAM
# ==================================================

print("=" * 60)
print("              NewsVerify AI Agent")
print("=" * 60)

news = input("\nEnter a news headline: ").strip()

if not news:

    print("Headline cannot be empty.")
    raise SystemExit


# ==================================================
# STAGE 1: NEWS SEARCHING
# ==================================================

print("\nSTAGE 1: NEWS SEARCHING")
print("=" * 60)

print("Searching for news reports...")

results = search_news(news)

if not results:

    print("\nNo news reports found.")
    print("Check your internet connection.")
    print("\nFINAL VERDICT: UNVERIFIED")
    print("Explanation: No search evidence was retrieved.")

    raise SystemExit


# ==================================================
# STAGE 2: CLEAN NEWS RESULTS
# ==================================================

print("\nSTAGE 2: CLEAN NEWS RESULTS")
print("=" * 60)

articles = clean_articles(results)

print("Search results received:", len(results))
print("Unique articles found:", len(articles))
print("Duplicate articles removed:",
      len(results) - len(articles))

if not articles:

    print("\nNo usable articles found.")
    print("FINAL VERDICT: UNVERIFIED")

    raise SystemExit


# ==================================================
# STAGE 3: NEWS VERIFICATION
# ==================================================

print("\nSTAGE 3: NEWS VERIFICATION")
print("=" * 60)

headline_keywords = get_keywords(news)

scores = []

for i, article in enumerate(articles, 1):

    article_text = (
        article["title"]
        + " "
        + article["description"]
    )

    article_keywords = get_keywords(article_text)

    matched = headline_keywords & article_keywords

    score = (
        len(matched) / len(headline_keywords) * 100
        if headline_keywords else 0
    )

    scores.append(score)

    print(f"\n{i}. {article['title']}")

    print("Source:", article["domain"])
    print("Link:", article["link"])

    print("Description:", article["description"])

    print("Matched keywords:", matched)

    print(f"Keyword match: {score:.1f}%")

    print("-" * 60)


average_score = sum(scores) / len(scores)

print("\nSTAGE 3 SUMMARY")
print("=" * 60)

print("Reports compared:", len(articles))

print(f"Average keyword match: {average_score:.1f}%")


# ==================================================
# STAGE 4: AI VERDICT
# ==================================================

print("\nSTAGE 4: AI VERDICT")
print("=" * 60)

print("\nPlease open and manually verify the news links.")

print("Check the following:")
print("1. Is the source reliable?")
print("2. Does the article support the headline?")
print("3. Does the article contradict the headline?")
print("4. Is the report independent?")
print("5. Is the information current?")

valid_numbers = set(range(1, len(articles) + 1))

print("\nEnter article numbers separated by commas.")
print("Example: 1,3")


support_indices = get_article_numbers(
    "\nSupporting article numbers: ",
    valid_numbers
)

contradiction_indices = get_article_numbers(
    "Contradicting article numbers: ",
    valid_numbers
)


# ==================================================
# CHECK CONFLICTING INPUT
# ==================================================

if set(support_indices) & set(contradiction_indices):

    print("\nERROR: An article cannot be selected")
    print("as both supporting and contradicting.")

    print("\nFINAL VERDICT: UNVERIFIED")

    raise SystemExit


# ==================================================
# COUNT DISTINCT DOMAINS
# ==================================================

support_domains = {
    articles[i - 1]["domain"]
    for i in support_indices
}

contradiction_domains = {
    articles[i - 1]["domain"]
    for i in contradiction_indices
}

support = len(support_domains)

contradiction = len(contradiction_domains)


# ==================================================
# GENERATE VERDICT
# ==================================================

if support >= 2 and contradiction == 0:

    verdict = "REAL"

    explanation = (
        "At least two distinct publisher domains "
        "have manually verified reports supporting "
        "the headline, with no selected reports "
        "contradicting it."
    )

elif contradiction >= 2 and support == 0:

    verdict = "FAKE"

    explanation = (
        "At least two distinct publisher domains "
        "have manually verified reports contradicting "
        "the headline, with no selected reports "
        "supporting it."
    )

else:

    verdict = "UNVERIFIED"

    explanation = (
        "There is insufficient or conflicting "
        "evidence for a reliable verdict."
    )


# ==================================================
# FINAL VERDICT DISPLAY
# ==================================================

print("\n" + "=" * 60)

print("                 FINAL VERDICT")

print("=" * 60)

print("\nHeadline:", news)

print("\nVerdict:", verdict)

print("\nExplanation:", explanation)

print("\nReports compared:", len(articles))

print(f"Average keyword match: {average_score:.1f}%")

print("\nSupporting domains:", support_domains)

print("Contradicting domains:", contradiction_domains)

print("\nIMPORTANT NOTES:")

print("1. Keyword matching alone does not prove truth.")

print("2. Different domains do not guarantee independent ownership.")

print("3. Manual verification of sources is required.")

print("4. This is an evidence-assisted system,")
print("   not a fully automated fact-checker.")

print("\n" + "=" * 60)

print("           VERIFICATION COMPLETED")

print("=" * 60)