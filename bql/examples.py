"""BQL Example Queries"""

EXAMPLE_QUERIES = {
    "simple_extraction": """
        query {
            page(url: "https://example.com") {
                title
                description: text(css: "meta[name='description']")
                links: select(css: "a") {
                    text
                    href: attr(name: "href")
                }
            }
        }
    """,
    
    "news_scraping": """
        query NewsArticles {
            page(url: "https://news.ycombinator.com") {
                articles: select(css: ".athing") {
                    title: text(css: ".storylink")
                    url: attr(css: ".storylink", name: "href")
                    points: text(css: ".score")
                    author: text(css: ".hnuser")
                }
            }
        }
    """,
    
    "form_automation": """
        mutation FillLoginForm {
            navigate(url: "https://example.com/login")
            wait(duration: 2000)
            fill(selector: "#username", value: "john@example.com")
            fill(selector: "#password", value: "secret123")
            click(selector: "button[type='submit']")
            wait(duration: 3000)
        }
    """,
    
    "complex_workflow": """
        mutation DownloadReport {
            navigate(url: "https://app.example.com")
            fill(selector: "#username", value: "user")
            fill(selector: "#password", value: "pass")
            click(selector: "#login-btn")
            wait(duration: 2000)
            click(selector: "a[href*='reports']")
            wait(duration: 1000)
            click(selector: ".download-pdf")
        }
    """
}
