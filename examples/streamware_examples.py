"""
Streamware Examples - Demonstrating CurLLM component architecture

These examples show how to use the Streamware component system for
building composable web automation pipelines.
"""

from curllm_core.streamware import (
    flow,
    split,
    join,
    multicast,
    choose,
    enable_diagnostics,
    pipeline,
    metrics
)
from curllm_core.streamware.components.curllm import (
    browse,
    extract_data,
    fill_form,
    execute_bql
)


def example_1_simple_browse():
    """
    Example 1: Simple web browsing
    """
    print("\n=== Example 1: Simple Browse ===")
    
    result = (
        flow("curllm://browse?url=https://example.com&visual=false")
        .run()
    )
    
    print(f"Result: {result}")


def example_2_data_extraction():
    """
    Example 2: Extract data from webpage
    """
    print("\n=== Example 2: Data Extraction ===")
    
    result = (
        flow("curllm://extract?url=https://news.ycombinator.com&instruction=Extract top 5 story titles")
        | "transform://normalize"
        | "file://write?path=/tmp/hn_stories.json"
    ).run()
    
    print(f"Saved to: {result}")


def example_3_form_filling():
    """
    Example 3: Fill web form
    """
    print("\n=== Example 3: Form Filling ===")
    
    form_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "message": "Test message"
    }
    
    result = (
        flow("curllm://fill_form?url=https://example.com/contact&visual=true")
        .with_data(form_data)
        .run()
    )
    
    print(f"Form filled: {result}")


def example_4_bql_query():
    """
    Example 4: Execute BQL query
    """
    print("\n=== Example 4: BQL Query ===")
    
    bql_query = """
    page(url: "https://example.com") {
        title
        links {
            text
            url
        }
    }
    """
    
    result = flow("curllm://bql").with_data({"query": bql_query}).run()
    
    print(f"BQL Result: {result}")


def example_5_pipeline_composition():
    """
    Example 5: Complex pipeline with transformations
    """
    print("\n=== Example 5: Pipeline Composition ===")
    
    result = pipeline(
        "curllm://extract?url=https://news.ycombinator.com&instruction=Get all article titles",
        "transform://jsonpath?query=$.items[*]",
        "file://write?path=/tmp/articles.json"
    ).run()
    
    print(f"Pipeline result: {result}")


def example_6_split_join():
    """
    Example 6: Split/Join pattern for batch processing
    """
    print("\n=== Example 6: Split/Join Pattern ===")
    
    # Sample data
    urls = [
        "https://example.com",
        "https://httpbin.org",
        "https://jsonplaceholder.typicode.com"
    ]
    
    result = (
        flow("http://localhost:8000/dummy")  # Dummy start
        .with_data({"urls": urls})
        | split("urls", split_type="field")
        | "curllm://browse?instruction=Get page title"
        | join()
        | "file://write?path=/tmp/batch_results.json"
    ).run()
    
    print(f"Batch processing complete: {result}")


def example_7_multicast():
    """
    Example 7: Multicast - send to multiple destinations
    """
    print("\n=== Example 7: Multicast ===")
    
    data = {"message": "Test data"}
    
    result = (
        flow("http://httpbin.org/json")
        | multicast([
            "file://write?path=/tmp/output1.json",
            "file://write?path=/tmp/output2.json",
            "transform://csv"
        ])
    ).run()
    
    print(f"Multicast results: {result}")


def example_8_conditional_routing():
    """
    Example 8: Conditional routing with choose
    """
    print("\n=== Example 8: Conditional Routing ===")
    
    result = (
        flow("http://httpbin.org/json")
        | choose()
            .when("$.priority == 'high'", "file://write?path=/tmp/high.json")
            .when("$.priority == 'low'", "file://write?path=/tmp/low.json")
            .otherwise("file://write?path=/tmp/default.json")
    ).run()
    
    print(f"Routed to: {result}")


def example_9_streaming():
    """
    Example 9: Streaming processing
    """
    print("\n=== Example 9: Streaming ===")
    
    # Process multiple URLs in stream
    urls = [
        {"url": "https://example.com"},
        {"url": "https://httpbin.org"},
    ]
    
    for result in (
        flow("curllm-stream://browse")
        .with_data(urls)
    ).stream(iter(urls)):
        print(f"Processed: {result}")


def example_10_with_metrics():
    """
    Example 10: Pipeline with metrics
    """
    print("\n=== Example 10: With Metrics ===")
    
    with metrics.track("extraction_pipeline"):
        result = (
            flow("curllm://extract?url=https://example.com&instruction=Get title")
            | "transform://normalize"
            | "file://write?path=/tmp/metrics_test.json"
        ).run()
        
    stats = metrics.get_stats("extraction_pipeline")
    print(f"Metrics: {stats}")


def example_11_helper_functions():
    """
    Example 11: Using helper functions
    """
    print("\n=== Example 11: Helper Functions ===")
    
    # Using browse helper
    result = browse(
        "https://example.com",
        instruction="Get page title",
        visual=False,
        stealth=True
    )
    print(f"Browse result: {result}")
    
    # Using extract_data helper
    result = extract_data(
        "https://news.ycombinator.com",
        "Extract top 3 stories"
    )
    print(f"Extract result: {result}")


def example_12_web_scraping_pipeline():
    """
    Example 12: Complete web scraping pipeline
    """
    print("\n=== Example 12: Web Scraping Pipeline ===")
    
    result = (
        flow("curllm://browse?url=https://news.ycombinator.com&stealth=true")
        | "curllm://extract?instruction=Find all articles under rank 10"
        | "transform://jsonpath?query=$.items[*]"
        | "file://write?path=/tmp/scraped_articles.json"
        | "transform://csv"
        | "file://write?path=/tmp/scraped_articles.csv"
    ).with_diagnostics(trace=True).run()
    
    print(f"Scraping complete: {result}")


def example_13_error_handling():
    """
    Example 13: Error handling in pipelines
    """
    print("\n=== Example 13: Error Handling ===")
    
    try:
        result = (
            flow("curllm://browse?url=https://invalid-url-xyz.com")
            | "transform://json"
            | "file://write?path=/tmp/error_test.json"
        ).run()
    except Exception as e:
        print(f"Caught error: {e}")


def example_14_file_operations():
    """
    Example 14: File I/O operations
    """
    print("\n=== Example 14: File Operations ===")
    
    # Write
    data = {"message": "Hello from Streamware"}
    flow("file://write?path=/tmp/test.json").with_data(data).run()
    
    # Read
    result = flow("file://read?path=/tmp/test.json").run()
    print(f"Read from file: {result}")
    
    # Check exists
    exists = flow("file://exists?path=/tmp/test.json").run()
    print(f"File exists: {exists}")


def example_15_http_requests():
    """
    Example 15: HTTP/Web requests
    """
    print("\n=== Example 15: HTTP Requests ===")
    
    # GET request
    result = flow("http://httpbin.org/json").run()
    print(f"GET result: {result}")
    
    # POST request
    result = (
        flow("http://httpbin.org/post?method=post")
        .with_data({"key": "value"})
        .run()
    )
    print(f"POST result: {result}")


if __name__ == "__main__":
    # Enable detailed logging
    enable_diagnostics("INFO")
    
    print("=" * 60)
    print("Streamware Examples for CurLLM")
    print("=" * 60)
    
    # Run examples (uncomment to test specific examples)
    
    # Basic examples
    # example_1_simple_browse()
    # example_2_data_extraction()
    # example_3_form_filling()
    # example_4_bql_query()
    
    # Advanced patterns
    # example_5_pipeline_composition()
    # example_6_split_join()
    # example_7_multicast()
    # example_8_conditional_routing()
    # example_9_streaming()
    
    # Utilities
    # example_10_with_metrics()
    # example_11_helper_functions()
    
    # Real-world use cases
    # example_12_web_scraping_pipeline()
    # example_13_error_handling()
    # example_14_file_operations()
    # example_15_http_requests()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
