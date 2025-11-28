#!/usr/bin/env python3
"""
CurLLM Streamware Examples - Refactored using modular component architecture

This file demonstrates how to use the new Streamware architecture for
common CurLLM tasks. All examples use the composable pipeline syntax.
"""

from curllm_core.streamware import (
    flow,
    pipeline,
    split,
    join,
    multicast,
    choose,
    enable_diagnostics,
    run_yaml_flow
)


def example_1_simple_browse():
    """
    Example 1: Simple webpage browsing
    
    Equivalent legacy code:
        executor = CurllmExecutor()
        result = executor.execute({"url": "https://example.com", "data": "browse"})
    """
    print("\n=== Example 1: Simple Browse ===")
    
    result = flow("curllm://browse?url=https://example.com&stealth=true").run()
    print(f"Result: {result.get('status', 'completed')}")


def example_2_data_extraction():
    """
    Example 2: Extract data from webpage and save to file
    
    New: Complete pipeline with transformation and file output
    """
    print("\n=== Example 2: Data Extraction Pipeline ===")
    
    result = (
        flow("curllm://extract?url=https://news.ycombinator.com&instruction=Get top 5 story titles")
        | "transform://normalize"
        | "file://write?path=/tmp/hn_stories.json"
    ).run()
    
    print(f"Saved to: {result['path']}")


def example_3_form_filling():
    """
    Example 3: Fill web form
    
    New: Simplified form filling with data passing
    """
    print("\n=== Example 3: Form Filling ===")
    
    form_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "message": "Test automation message"
    }
    
    result = (
        flow("curllm://fill_form?url=https://example.com/contact&visual=true")
        .with_data(form_data)
        .run()
    )
    
    print(f"Form filled: {result.get('status')}")


def example_4_bql_query():
    """
    Example 4: Execute BQL (Browser Query Language) query
    
    New: Direct BQL execution through component
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
    
    result = (
        flow("curllm://bql")
        .with_data({"query": bql_query})
        | "file://write?path=/tmp/bql_result.json"
    ).run()
    
    print(f"BQL result saved to: {result['path']}")


def example_5_multi_format_export():
    """
    Example 5: Extract data and export in multiple formats
    
    New: Multicast pattern for multiple outputs
    """
    print("\n=== Example 5: Multi-format Export ===")
    
    results = (
        flow("curllm://extract?url=https://example.com&instruction=Get all links")
        | multicast([
            "file://write?path=/tmp/links.json",
            "transform://csv",
            "file://write?path=/tmp/links.csv"
        ])
    ).run()
    
    print(f"Exported to {len(results)} formats")


def example_6_batch_processing():
    """
    Example 6: Process multiple URLs with split/join
    
    New: Advanced pattern for batch operations
    """
    print("\n=== Example 6: Batch Processing ===")
    
    urls = {
        "urls": [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com"
        ]
    }
    
    result = (
        flow("transform://normalize")
        .with_data(urls)
        | split("$.urls[*]")
        | "curllm://browse?stealth=true"
        | join()
        | "file://write?path=/tmp/batch_results.json"
    ).run()
    
    print(f"Processed batch, saved to: {result['path']}")


def example_7_conditional_routing():
    """
    Example 7: Route data based on conditions
    
    New: Choose/when pattern for conditional logic
    """
    print("\n=== Example 7: Conditional Routing ===")
    
    # This would route based on extracted data properties
    result = (
        flow("curllm://extract?url=https://example.com&instruction=Get article priority")
        | choose()
            .when("$.priority == 'high'", "file://write?path=/tmp/high_priority.json")
            .when("$.priority == 'low'", "file://write?path=/tmp/low_priority.json")
            .otherwise("file://write?path=/tmp/normal_priority.json")
    ).run()
    
    print(f"Routed to: {result['path']}")


def example_8_scraping_pipeline():
    """
    Example 8: Complete web scraping pipeline
    
    New: Full end-to-end pipeline with all steps
    """
    print("\n=== Example 8: Complete Scraping Pipeline ===")
    
    result = pipeline(
        "curllm://browse?url=https://news.ycombinator.com&stealth=true",
        "curllm://extract?instruction=Get all articles with score > 50",
        "transform://jsonpath?query=$.items[*]",
        "transform://csv?delimiter=,",
        "file://write?path=/tmp/scraped_articles.csv"
    ).with_diagnostics(trace=True).run()
    
    print(f"Scraping complete: {result['path']}")


def example_9_yaml_flow():
    """
    Example 9: Run flow from YAML definition
    
    New: Execute pre-defined YAML flows
    """
    print("\n=== Example 9: YAML Flow ===")
    
    # Run a YAML flow with custom variables
    try:
        result = run_yaml_flow(
            "flows/example_extraction.yaml",
            variables={
                "url": "https://news.ycombinator.com",
                "instruction": "Extract top 5 stories"
            }
        )
        print(f"YAML flow completed: {result}")
    except Exception as e:
        print(f"YAML flow not found (expected in development): {e}")


def example_10_http_to_scraping():
    """
    Example 10: Get URLs from API, then scrape
    
    New: Combining HTTP and CurLLM components
    """
    print("\n=== Example 10: API to Scraping ===")
    
    # Example: Get URLs from API endpoint, then scrape each
    result = (
        flow("http://httpbin.org/json")
        | "transform://jsonpath?query=$.slideshow.slides[*].title"
        | "file://write?path=/tmp/api_result.json"
    ).run()
    
    print(f"API data processed: {result}")


def example_11_screenshot_capture():
    """
    Example 11: Capture webpage screenshots
    
    New: Screenshot component
    """
    print("\n=== Example 11: Screenshot ===")
    
    result = (
        flow("curllm://screenshot?url=https://example.com")
        | "file://write?path=/tmp/screenshot_meta.json"
    ).run()
    
    print(f"Screenshot captured: {result}")


def example_12_data_validation():
    """
    Example 12: Extract and filter data
    
    New: Filter pattern for data validation
    """
    print("\n=== Example 12: Data Validation ===")
    
    # Extract products and filter by price
    data = [
        {"name": "Product A", "price": 10},
        {"name": "Product B", "price": 50},
        {"name": "Product C", "price": 25}
    ]
    
    result = (
        flow("filter://condition?field=price&min=20&max=60")
        .with_data(data)
        | "file://write?path=/tmp/filtered_products.json"
    ).run()
    
    print(f"Filtered products: {result}")


def example_13_file_operations():
    """
    Example 13: File I/O operations
    
    New: File component for reading/writing
    """
    print("\n=== Example 13: File Operations ===")
    
    # Write data
    data = {"message": "Hello Streamware", "items": [1, 2, 3]}
    
    write_result = (
        flow("file://write?path=/tmp/test_data.json")
        .with_data(data)
        .run()
    )
    print(f"Written: {write_result}")
    
    # Read data back
    read_result = flow("file://read?path=/tmp/test_data.json").run()
    print(f"Read back: {read_result}")


def example_14_transform_pipeline():
    """
    Example 14: Data transformation pipeline
    
    New: Multiple transformations in sequence
    """
    print("\n=== Example 14: Transform Pipeline ===")
    
    data = {
        "items": [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200},
            {"name": "Item 3", "value": 300}
        ]
    }
    
    result = (
        flow("transform://jsonpath?query=$.items[*]")
        .with_data(data)
        | "transform://csv?delimiter=,"
        | "file://write?path=/tmp/transformed.csv"
    ).run()
    
    print(f"Transform pipeline complete: {result}")


def example_15_metrics_tracking():
    """
    Example 15: Track pipeline metrics
    
    New: Built-in metrics for monitoring
    """
    print("\n=== Example 15: Metrics Tracking ===")
    
    from curllm_core.streamware import metrics
    
    with metrics.track("example_pipeline"):
        result = (
            flow("curllm://browse?url=https://example.com")
            | "file://write?path=/tmp/metrics_test.json"
        ).run()
    
    stats = metrics.get_stats("example_pipeline")
    print(f"Pipeline stats: {stats}")


if __name__ == "__main__":
    # Enable detailed logging
    enable_diagnostics("INFO")
    
    print("=" * 70)
    print("CurLLM Streamware Examples - Modular Component Architecture")
    print("=" * 70)
    
    # Run examples (uncomment to test specific examples)
    
    # Basic examples
    # example_1_simple_browse()
    # example_2_data_extraction()
    # example_3_form_filling()
    # example_4_bql_query()
    
    # Advanced patterns
    # example_5_multi_format_export()
    # example_6_batch_processing()
    # example_7_conditional_routing()
    # example_8_scraping_pipeline()
    
    # Integration
    # example_9_yaml_flow()
    # example_10_http_to_scraping()
    
    # Utilities
    # example_11_screenshot_capture()
    # example_12_data_validation()
    # example_13_file_operations()
    # example_14_transform_pipeline()
    # example_15_metrics_tracking()
    
    print("\n" + "=" * 70)
    print("Examples complete!")
    print("\nTo run individual examples:")
    print("  1. Uncomment the example you want to run")
    print("  2. Ensure CurLLM server is running (for curllm:// components)")
    print("  3. Run: python examples_streamware.py")
    print("\nTo use YAML flows:")
    print("  curllm-flow run flows/example_browse.yaml")
    print("=" * 70)
