#!/usr/bin/env python3
"""
Streamware Quick Start - Get started with CurLLM component architecture

This file demonstrates the basic usage of Streamware components.
"""

from curllm_core.streamware import (
    flow,
    enable_diagnostics,
    list_available_components,
    describe_component
)


def main():
    """Quick start examples"""
    
    print("=" * 60)
    print("Streamware Quick Start")
    print("=" * 60)
    
    # Enable diagnostics for detailed logging
    enable_diagnostics("INFO")
    
    # 1. List available components
    print("\n1. Available Components:")
    print("-" * 40)
    schemes = list_available_components()
    print(f"Registered schemes: {', '.join(schemes)}")
    
    # 2. Describe a component
    print("\n2. Component Details:")
    print("-" * 40)
    curllm_info = describe_component('curllm')
    if curllm_info:
        print(f"Component: {curllm_info['class']}")
        print(f"Scheme: {curllm_info['scheme']}")
        print(f"Input: {curllm_info['input_mime']}")
        print(f"Output: {curllm_info['output_mime']}")
    
    # 3. Simple file operations
    print("\n3. File Operations:")
    print("-" * 40)
    
    # Write data to file
    data = {
        "message": "Hello from Streamware!",
        "timestamp": "2024-01-01T00:00:00Z",
        "items": [1, 2, 3, 4, 5]
    }
    
    result = (
        flow("file://write?path=/tmp/streamware_test.json")
        .with_data(data)
        .run()
    )
    print(f"File write result: {result}")
    
    # Read data back
    read_data = flow("file://read?path=/tmp/streamware_test.json").run()
    print(f"File read result: {read_data}")
    
    # 4. Data transformation
    print("\n4. Data Transformation:")
    print("-" * 40)
    
    # Extract with JSONPath
    extracted = (
        flow("transform://jsonpath?query=$.items[*]")
        .with_data(data)
        .run()
    )
    print(f"JSONPath extraction: {extracted}")
    
    # Convert to CSV
    csv_data = [
        {"name": "Alice", "age": 30, "city": "New York"},
        {"name": "Bob", "age": 25, "city": "London"},
        {"name": "Charlie", "age": 35, "city": "Paris"}
    ]
    
    csv_output = (
        flow("transform://csv?delimiter=,")
        .with_data(csv_data)
        .run()
    )
    print(f"CSV output:\n{csv_output}")
    
    # 5. Pipeline composition
    print("\n5. Pipeline Composition:")
    print("-" * 40)
    
    result = (
        flow("file://read?path=/tmp/streamware_test.json")
        | "transform://jsonpath?query=$.items"
        | "transform://normalize"
        | "file://write?path=/tmp/streamware_pipeline.json"
    ).run()
    print(f"Pipeline result: {result}")
    
    # 6. HTTP request (example - commented out to avoid actual requests)
    print("\n6. HTTP Request Example:")
    print("-" * 40)
    print("""
    # GET request
    result = flow("http://httpbin.org/json").run()
    
    # POST request
    result = (
        flow("http://httpbin.org/post?method=post")
        .with_data({"key": "value"})
        .run()
    )
    """)
    
    # 7. CurLLM example (commented out - requires running server)
    print("\n7. CurLLM Usage Example:")
    print("-" * 40)
    print("""
    # Browse webpage
    result = flow("curllm://browse?url=https://example.com&stealth=true").run()
    
    # Extract data
    result = (
        flow("curllm://extract?url=https://example.com&instruction=Get all links")
        | "transform://csv"
        | "file://write?path=links.csv"
    ).run()
    
    # Fill form
    form_data = {"name": "John", "email": "john@example.com"}
    result = (
        flow("curllm://fill_form?url=https://example.com/contact")
        .with_data(form_data)
        .run()
    )
    """)
    
    print("\n" + "=" * 60)
    print("Quick Start Complete!")
    print("=" * 60)
    print("\nNext Steps:")
    print("- Check examples/streamware_examples.py for more examples")
    print("- Read docs/STREAMWARE.md for full documentation")
    print("- Create custom components with @register decorator")


if __name__ == "__main__":
    main()
