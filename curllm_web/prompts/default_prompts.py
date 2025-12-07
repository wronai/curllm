"""Default prompts for curllm web interface"""

DEFAULT_PROMPTS = [
    {
        "id": "extract_all",
        "name": "Wyciągnij wszystkie dane",
        "prompt": "Extract all important data from this page including links, emails, phones, and products"
    },
    {
        "id": "extract_products",
        "name": "Wyciągnij produkty",
        "prompt": "Extract all products with names, prices, and descriptions"
    },
    {
        "id": "extract_products_cheap",
        "name": "Produkty poniżej 100zł",
        "prompt": "Find all products priced under 100 PLN and extract their names, prices, and URLs"
    },
    {
        "id": "extract_articles",
        "name": "Wyciągnij artykuły",
        "prompt": "Extract all articles with titles, authors, dates, and content"
    },
    {
        "id": "extract_news",
        "name": "Najnowsze wiadomości",
        "prompt": "Extract the latest 10 news articles with headlines, summaries, and publication dates"
    },
    {
        "id": "extract_contacts",
        "name": "Wyciągnij kontakty",
        "prompt": "Extract all contact information including emails, phones, and addresses"
    },
    {
        "id": "extract_links",
        "name": "Wyciągnij linki",
        "prompt": "Extract all links from this page with their anchor text and URLs"
    },
    {
        "id": "extract_images",
        "name": "Wyciągnij obrazy",
        "prompt": "Extract all images from this page with their URLs, alt text, and dimensions if available"
    },
    {
        "id": "extract_tables",
        "name": "Wyciągnij tabele",
        "prompt": "Extract all tables from this page and convert them to structured data"
    },
    {
        "id": "extract_forms",
        "name": "Wykryj formularze",
        "prompt": "Find all forms on this page and list their fields, labels, and required status"
    },
    {
        "id": "fill_form",
        "name": "Wypełnij formularz",
        "prompt": "Fill the form on this page with provided data"
    },
    {
        "id": "fill_contact_form",
        "name": "Wypełnij formularz kontaktowy",
        "prompt": "Fill contact form with: name=Jan Kowalski, email=jan@example.com, phone=+48123456789, message=Test wiadomości"
    },
    {
        "id": "search_on_page",
        "name": "Szukaj na stronie",
        "prompt": "Search for specific keyword or phrase on this page and extract relevant context"
    },
    {
        "id": "compare_prices",
        "name": "Porównaj ceny",
        "prompt": "Find and compare prices for similar products on this page"
    },
    {
        "id": "extract_reviews",
        "name": "Wyciągnij opinie",
        "prompt": "Extract all user reviews with ratings, author names, dates, and review text"
    },
    {
        "id": "screenshot",
        "name": "Zrób screenshot",
        "prompt": "Take a screenshot of the page"
    },
    {
        "id": "navigate_and_extract",
        "name": "Nawiguj i wyciągnij",
        "prompt": "Navigate through multiple pages and extract data from each page"
    },
    {
        "id": "login_and_extract",
        "name": "Zaloguj i wyciągnij",
        "prompt": "Login to the website and extract data from authenticated pages"
    },
    {
        "id": "custom",
        "name": "Własny prompt",
        "prompt": ""
    }
]
