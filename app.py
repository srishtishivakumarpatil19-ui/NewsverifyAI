import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

import streamlit as st
from urllib.parse import urlparse

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="NewsVerify AI",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 NewsVerify AI")
st.subheader("Smart News Verification System")

st.markdown("""
Welcome to *NewsVerify AI*!

Search a news headline, compare reports from
different sources and manually evaluate evidence
to generate a verification verdict.
""")

st.info(
    "This is an evidence-assisted verification system. "
    "Keyword matching alone cannot prove whether news is true."
)


# ==========================================
# TEXT CLEANING
# ==========================================

def clean_text(text):

    text = html.unescape(str(text or ""))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# ==========================================
# KEYWORD EXTRACTION
# ==========================================

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


# ==========================================
# SOURCE DOMAIN EXTRACTION
# ==========================================

def get_domain(url):

    try:

        host = urlparse(url).hostname

        if not host:
            return ""

        return host.lower().removeprefix("www.")

    except Exception:

        return ""


# ==========================================
# NEWS SEARCHING
# DDGS + GOOGLE NEWS RSS BACKUP
# ==========================================

def search_news(headline):

    articles = []

    # FIRST METHOD: DDGS

    if DDGS is not None:

        try:

            with DDGS() as ddgs:

                results = ddgs.text(
                    headline,
                    max_results=8
                )

                articles = list(results)

            if articles:
                return articles

        except Exception as error:

            st.warning(
                f"DDGS search unavailable: {error}"
            )

    # SECOND METHOD: GOOGLE NEWS RSS

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

        return articles

    except Exception as error:

        st.error(
            f"Google News RSS search failed: {error}"
        )

        return []


# ==========================================
# REMOVE DUPLICATE ARTICLES
# ==========================================

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

        link = str(
            result.get("href", "")
        ).strip()

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


# ==========================================
# SESSION STATE
# ==========================================

if "articles" not in st.session_state:
    st.session_state.articles = []

if "headline" not in st.session_state:
    st.session_state.headline = ""

if "verdict" not in st.session_state:
    st.session_state.verdict = None


# ==========================================
# MAIN WEBSITE
# ==========================================

st.markdown("---")

st.header("📰 News Headline Verification")

headline = st.text_input(
    "Enter a news headline:",
    placeholder="Example: India wins the 2026 T20 World Cup"
)

search_button = st.button(
    "🔍 Search News Reports",
    type="primary",
    use_container_width=True
)


# ==========================================
# SEARCH BUTTON
# ==========================================

if search_button:

    if not headline.strip():

        st.warning("Please enter a news headline.")

    else:

        st.session_state.articles = []
        st.session_state.verdict = None

        with st.spinner("Searching news reports..."):

            results = search_news(headline.strip())

            articles = clean_articles(results)

            if articles:

                headline_keywords = get_keywords(
                    headline
                )

                for article in articles:

                    article_text = (
                        article["title"]
                        + " "
                        + article["description"]
                    )

                    article_keywords = get_keywords(
                        article_text
                    )

                    matched = (
                        headline_keywords
                        & article_keywords
                    )

                    score = (
                        len(matched)
                        / len(headline_keywords)
                        * 100
                        if headline_keywords
                        else 0
                    )

                    article["score"] = score
                    article["matched"] = matched

                st.session_state.articles = articles

                st.session_state.headline = headline.strip()

            else:

                st.error(
                    "No usable news reports found. "
                    "Please check your internet connection "
                    "or try another headline."
                )


# ==========================================
# DISPLAY SEARCH RESULTS
# ==========================================

articles = st.session_state.articles

if articles:

    st.markdown("---")

    st.header("📊 Search Summary")

    average_score = sum(
        article["score"]
        for article in articles
    ) / len(articles)

    unique_domains = {
        article["domain"]
        for article in articles
    }

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Reports Compared",
        len(articles)
    )

    col2.metric(
        "Average Keyword Match",
        f"{average_score:.1f}%"
    )

    col3.metric(
        "Unique Domains",
        len(unique_domains)
    )

    st.markdown("---")

    st.header("🌐 Retrieved News Articles")

    for i, article in enumerate(articles, 1):

        with st.expander(
            f"{i}. {article['title']}",
            expanded=True
        ):

            st.write(
                "*Source:*",
                article["domain"]
            )

            st.write(
                "*Description:*",
                article["description"]
            )

            st.write(
                f"*Keyword Match:* "
                f"{article['score']:.1f}%"
            )

            st.write(
                "*Matched Keywords:*",
                ", ".join(
                    sorted(article["matched"])
                )
            )

            st.link_button(
                "Open Original News Article",
                article["link"]
            )


    # ======================================
    # MANUAL VERIFICATION
    # ======================================

    st.markdown("---")

    st.header("🧠 Manual Evidence Verification")

    st.write(
        "Read each original article carefully. "
        "Select whether it supports or contradicts "
        "the entered headline."
    )

    st.warning(
        "Do not select an article based only on its "
        "keyword match percentage."
    )

    choices = {}

    for i, article in enumerate(articles, 1):

        choices[i] = st.selectbox(

            f"Article {i}: {article['domain']}",

            [
                "Not evaluated",
                "Supports the headline",
                "Contradicts the headline"
            ],

            key=f"article_{i}"
        )


    # ======================================
    # GENERATE VERDICT
    # ======================================

    if st.button(
        "🏆 Generate Final Verdict",
        type="primary",
        use_container_width=True
    ):

        support_domains = {

            articles[i - 1]["domain"]

            for i, choice in choices.items()

            if choice == "Supports the headline"

        }

        contradiction_domains = {

            articles[i - 1]["domain"]

            for i, choice in choices.items()

            if choice == "Contradicts the headline"

        }

        support = len(support_domains)

        contradiction = len(contradiction_domains)


        # VERDICT LOGIC

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


        st.session_state.verdict = verdict

        # ==================================
        # FINAL VERDICT DISPLAY
        # ==================================

        st.markdown("---")

        st.header("🏆 FINAL VERIFICATION RESULT")

        st.subheader(
            st.session_state.headline
        )

        if verdict == "REAL":

            st.success("VERDICT: REAL")

        elif verdict == "FAKE":

            st.error("VERDICT: FAKE")

        else:

            st.warning("VERDICT: UNVERIFIED")

        st.write(
            "*Explanation:*",
            explanation
        )

        st.write(
            "*Reports compared:*",
            len(articles)
        )

        st.write(
            "*Average keyword match:*",
            f"{average_score:.1f}%"
        )

        st.write(
            "*Supporting domains:*",
            ", ".join(sorted(support_domains))
            or "None"
        )

        st.write(
            "*Contradicting domains:*",
            ", ".join(sorted(contradiction_domains))
            or "None"
        )

        st.info(
            "IMPORTANT NOTES:\n\n"
            "1. Keyword matching alone does not prove truth.\n\n"
            "2. Different domains do not guarantee independent ownership.\n\n"
            "3. Manual verification of sources is required.\n\n"
            "4. This is an evidence-assisted system, "
            "not a fully automated fact-checker."
        )


# ==========================================
# FOOTER
# ==========================================

st.markdown("---")

st.caption(
    "NewsVerify AI | Python-Based News Verification Project"
)