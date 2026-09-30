import csv
import time
import statistics
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ==============================
# CONFIGURATION
# ==============================

BASE_URL = "https://books.toscrape.com/"
OUTPUT_FILE = "books.csv"

# Number of pages to scrape
MAX_PAGES = 5

# Delay between requests
DELAY = 1.0

# Retry configuration
MAX_RETRIES = 3

# Custom headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}


# ==============================
# FETCH WEB PAGE
# ==============================

def fetch_page(url):
    """
    Download a webpage with retry logic.
    """

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            # Raise error for 4xx/5xx responses
            response.raise_for_status()

            return response.text

        except requests.RequestException as error:

            print(
                f"Request failed "
                f"(attempt {attempt}/{MAX_RETRIES}): {error}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(2)

    print(f"Could not download: {url}")

    return None


# ==============================
# PARSE BOOK DATA
# ==============================

def parse_books(html, page_url):
    """
    Extract book information from HTML.
    """

    soup = BeautifulSoup(html, "html.parser")

    books = []

    book_items = soup.select("article.product_pod")

    for item in book_items:

        # --------------------------
        # Title
        # --------------------------

        title_tag = item.select_one("h3 a")

        title = (
            title_tag.get("title", "").strip()
            if title_tag
            else ""
        )

        # --------------------------
        # Price
        # --------------------------

        price_tag = item.select_one(".price_color")

        price_text = (
            price_tag.get_text(strip=True)
            if price_tag
            else ""
        )

        # Convert £51.77 -> 51.77
        try:
            price = float(
                price_text.replace("£", "").strip()
            )
        except ValueError:
            price = None

        # --------------------------
        # Availability
        # --------------------------

        availability_tag = item.select_one(
            ".availability"
        )

        availability = (
            availability_tag.get_text(
                " ",
                strip=True
            )
            if availability_tag
            else ""
        )

        # --------------------------
        # Rating
        # --------------------------

        rating_tag = item.select_one(".star-rating")

        if rating_tag:

            rating_classes = rating_tag.get("class", [])

            rating_words = [
                "One",
                "Two",
                "Three",
                "Four",
                "Five"
            ]

            rating = "Unknown"

            for word in rating_words:

                if word in rating_classes:
                    rating = word
                    break

        else:
            rating = "Unknown"

        # --------------------------
        # Product URL
        # --------------------------

        if title_tag and title_tag.get("href"):

            product_url = urljoin(
                page_url,
                title_tag.get("href")
            )

        else:
            product_url = ""

        # --------------------------
        # Store data
        # --------------------------

        books.append({
            "title": title,
            "price_gbp": price,
            "rating": rating,
            "availability": availability,
            "url": product_url
        })

    return books


# ==============================
# SAVE DATA TO CSV
# ==============================

def save_to_csv(books):
    """
    Save scraped data into CSV file.
    """

    if not books:
        print("No data available to save.")

        return

    fieldnames = [
        "title",
        "price_gbp",
        "rating",
        "availability",
        "url"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(books)

    print(
        f"\nData successfully saved to "
        f"{OUTPUT_FILE}"
    )


# ==============================
# SUMMARY REPORT
# ==============================

def generate_summary(books):
    """
    Generate automated statistics report.
    """

    print("\n" + "=" * 50)
    print("AUTOMATED SCRAPING SUMMARY")
    print("=" * 50)

    if not books:

        print("No records found.")

        return

    # Total records
    total_books = len(books)

    # Prices
    prices = [
        book["price_gbp"]
        for book in books
        if book["price_gbp"] is not None
    ]

    print(f"Total books scraped : {total_books}")

    if prices:

        print(
            f"Minimum price       : £{min(prices):.2f}"
        )

        print(
            f"Maximum price       : £{max(prices):.2f}"
        )

        print(
            f"Average price       : £{statistics.mean(prices):.2f}"
        )

        print(
            f"Median price        : £{statistics.median(prices):.2f}"
        )

    # Rating statistics
    rating_counts = {}

    for book in books:

        rating = book["rating"]

        rating_counts[rating] = (
            rating_counts.get(rating, 0) + 1
        )

    print("\nRating distribution:")

    for rating, count in sorted(
        rating_counts.items()
    ):

        print(
            f"  {rating}: {count}"
        )

    # Availability
    available = sum(
        1
        for book in books
        if "In stock" in book["availability"]
    )

    print(
        f"\nBooks in stock      : {available}"
    )

    print(
        f"Books not in stock  : "
        f"{total_books - available}"
    )

    print("=" * 50)


# ==============================
# MAIN SCRAPER
# ==============================

def main():

    print("=" * 50)
    print("BOOK WEB SCRAPER")
    print("=" * 50)

    all_books = []

    for page_number in range(
        1,
        MAX_PAGES + 1
    ):

        # First page URL
        if page_number == 1:

            url = BASE_URL + "index.html"

        else:

            url = (
                BASE_URL
                + f"catalogue/page-{page_number}.html"
            )

        print(
            f"\nScraping page {page_number}: {url}"
        )

        # --------------------------
        # Download HTML
        # --------------------------

        html = fetch_page(url)

        if html is None:

            print(
                "Skipping this page."
            )

            continue

        # --------------------------
        # Parse HTML
        # --------------------------

        books = parse_books(
            html,
            url
        )

        print(
            f"Books found: {len(books)}"
        )

        all_books.extend(books)

        # --------------------------
        # Rate limiting
        # --------------------------

        if page_number < MAX_PAGES:

            print(
                f"Waiting {DELAY} seconds..."
            )

            time.sleep(DELAY)

    # --------------------------
    # Save CSV
    # --------------------------

    save_to_csv(all_books)

    # --------------------------
    # Summary
    # --------------------------

    generate_summary(all_books)

    print(
        "\nScraping completed successfully!"
    )


# ==============================
# PROGRAM START
# ==============================

if __name__ == "__main__":
    main()
