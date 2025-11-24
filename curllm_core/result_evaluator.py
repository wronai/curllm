#!/usr/bin/env python3
"""
Intelligent result evaluation - determines if task execution was truly successful.

Prevents false positives like:
- "success: True" when navigation failed (403, 404, timeout)
- "success: True" when zero actions were taken
- "success: True" when form was not submitted
- "success: True" when no data was extracted
"""

from typing import Dict, Any, Tuple


def evaluate_run_success(
    result: Dict[str, Any],
    instruction: str,
    run_logger=None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Intelligently evaluate if task execution was successful.
    
    Args:
        result: Task execution result from run_task()
        instruction: Original user instruction
        run_logger: Optional logger
    
    Returns:
        (success: bool, reason: str, metadata: dict)
    """
    metadata = {
        "evaluated": True,
        "checks_performed": [],
        "failures": [],
        "warnings": []
    }
    
    instruction_lower = (instruction or "").lower()
    data = result.get("data")
    steps = result.get("steps", 0)
    
    # Check 1: Navigation errors (403, 404, timeout)
    if isinstance(data, dict) and "error" in data:
        error_data = data["error"]
        if isinstance(error_data, dict):
            error_type = error_data.get("type", "")
            error_msg = error_data.get("message", "")
            diagnostics = error_data.get("diagnostics", {})
            
            metadata["checks_performed"].append("navigation_error_check")
            
            # Check for 403 Forbidden
            if isinstance(diagnostics, dict):
                http_probe = diagnostics.get("http_probe", {})
                https_probe = diagnostics.get("https_probe", {})
                
                if http_probe.get("status") == 403 or https_probe.get("status") == 403:
                    metadata["failures"].append("HTTP 403 Forbidden - site blocking access")
                    if run_logger:
                        run_logger.log_text("❌ FAILURE: HTTP 403 Forbidden detected")
                        run_logger.log_text("   Site is blocking access (bot detection / WAF / Cloudflare)")
                    return (
                        False,
                        "Navigation failed: HTTP 403 Forbidden (site blocking access)",
                        metadata
                    )
                
                # Check for 404 Not Found
                if http_probe.get("status") == 404 or https_probe.get("status") == 404:
                    metadata["failures"].append("HTTP 404 Not Found")
                    if run_logger:
                        run_logger.log_text("❌ FAILURE: HTTP 404 Not Found")
                    return (
                        False,
                        "Navigation failed: HTTP 404 Not Found (page does not exist)",
                        metadata
                    )
                
                # Check for 500 errors
                http_status = http_probe.get("status", 0)
                https_status = https_probe.get("status", 0)
                if http_status >= 500 or https_status >= 500:
                    metadata["failures"].append(f"HTTP {max(http_status, https_status)} Server Error")
                    if run_logger:
                        run_logger.log_text(f"❌ FAILURE: HTTP {max(http_status, https_status)} Server Error")
                    return (
                        False,
                        f"Navigation failed: HTTP {max(http_status, https_status)} Server Error",
                        metadata
                    )
            
            # Check for timeout
            if "timeout" in error_msg.lower() or "timeout" in error_type.lower():
                metadata["failures"].append("Navigation timeout")
                if run_logger:
                    run_logger.log_text("❌ FAILURE: Navigation timeout")
                    run_logger.log_text("   Page took too long to load (> 30s)")
                return (
                    False,
                    "Navigation failed: Timeout exceeded (page took too long to load)",
                    metadata
                )
    
    # Check 2: Zero steps taken
    metadata["checks_performed"].append("steps_check")
    if steps == 0:
        metadata["warnings"].append("Zero steps executed")
        if run_logger:
            run_logger.log_text("⚠️  WARNING: Zero steps executed")
    
    # Check 3: Form filling tasks
    if any(kw in instruction_lower for kw in ["fill", "form", "formularz", "wypełnij", "submit"]):
        metadata["checks_performed"].append("form_task_check")
        
        # Check if form.fill was called
        if isinstance(data, dict) and "form_fill" in data:
            form_fill_data = data["form_fill"]
            
            if isinstance(form_fill_data, dict):
                submitted = form_fill_data.get("submitted", False)
                filled = form_fill_data.get("filled", {})
                errors = form_fill_data.get("errors", {})
                
                # Check if form was submitted
                if not submitted:
                    metadata["failures"].append("Form not submitted")
                    failure_reason = "Form detected but not submitted"
                    
                    # Add specific error details
                    if isinstance(errors, dict):
                        if errors.get("invalid_email"):
                            failure_reason += " (invalid email)"
                        if errors.get("required_missing"):
                            failure_reason += " (required fields missing)"
                        if errors.get("consent_required"):
                            failure_reason += " (consent checkbox not checked)"
                    
                    if run_logger:
                        run_logger.log_text("❌ FAILURE: Form not submitted")
                        run_logger.log_text(f"   Fields filled: {list(filled.keys()) if isinstance(filled, dict) else 'unknown'}")
                        run_logger.log_text(f"   Errors: {errors}")
                    
                    return (
                        False,
                        f"Form filling failed: {failure_reason}",
                        metadata
                    )
                else:
                    # Form submitted successfully
                    if run_logger:
                        run_logger.log_text("✓ SUCCESS: Form submitted successfully")
                        run_logger.log_text(f"   Fields filled: {list(filled.keys()) if isinstance(filled, dict) else 'unknown'}")
                    metadata["checks_performed"].append("form_submitted")
                    return (
                        True,
                        "Form submitted successfully",
                        metadata
                    )
        else:
            # Form task but no form.fill called
            if steps == 0:
                metadata["failures"].append("Form task but no form interaction")
                if run_logger:
                    run_logger.log_text("❌ FAILURE: Form task specified but no form was filled")
                return (
                    False,
                    "Form task failed: No form interaction detected",
                    metadata
                )
    
    # Check 4: Data extraction tasks
    if any(kw in instruction_lower for kw in ["extract", "get", "scrape", "find", "wyciągnij", "pobierz"]):
        metadata["checks_performed"].append("extraction_task_check")
        
        # Check if data was extracted
        if data is None or data == {}:
            metadata["failures"].append("No data extracted")
            if run_logger:
                run_logger.log_text("❌ FAILURE: Data extraction task but no data returned")
            return (
                False,
                "Data extraction failed: No data returned",
                metadata
            )
        
        # Check for empty results
        if isinstance(data, dict):
            # Check common extraction result keys
            extraction_keys = ["links", "emails", "phones", "articles", "products"]
            has_data = False
            for key in extraction_keys:
                if key in data and data[key]:
                    has_data = True
                    break
            
            if not has_data and not data.get("form_fill"):
                metadata["warnings"].append("Extraction task but minimal data returned")
                if run_logger:
                    run_logger.log_text("⚠️  WARNING: Extraction task but minimal data returned")
    
    # Check 5: Navigation tasks
    if any(kw in instruction_lower for kw in ["navigate", "go to", "open", "visit", "przejdź"]):
        metadata["checks_performed"].append("navigation_task_check")
        
        # If navigation was the only task and we got here without errors, it's success
        if steps >= 0 and not metadata["failures"]:
            if run_logger:
                run_logger.log_text("✓ SUCCESS: Navigation completed")
            return (
                True,
                "Navigation completed successfully",
                metadata
            )
    
    # Default: If no specific failures detected
    if not metadata["failures"]:
        # Check if any meaningful data was returned
        if data is not None and data != {}:
            if run_logger:
                run_logger.log_text(f"✓ SUCCESS: Task completed ({steps} steps taken)")
            return (
                True,
                f"Task completed successfully ({steps} steps taken)",
                metadata
            )
        elif steps > 0:
            # Steps were taken but no data - partial success
            metadata["warnings"].append("Steps executed but no data returned")
            if run_logger:
                run_logger.log_text(f"⚠️  PARTIAL SUCCESS: {steps} steps executed but no data returned")
            return (
                True,
                f"Task partially completed ({steps} steps taken, no data returned)",
                metadata
            )
        else:
            # No steps, no data
            metadata["failures"].append("No steps taken and no data returned")
            if run_logger:
                run_logger.log_text("❌ FAILURE: No steps taken and no data returned")
            return (
                False,
                "Task failed: No actions were performed",
                metadata
            )
    else:
        # Failures detected
        failure_summary = "; ".join(metadata["failures"])
        if run_logger:
            run_logger.log_text(f"❌ FAILURE: {failure_summary}")
        return (
            False,
            f"Task failed: {failure_summary}",
            metadata
        )
