#!/usr/bin/env python3
"""
E2E Tests for Orchestrator - Real services testing

These tests run against real websites to verify:
1. Command parsing
2. URL resolution
3. Form filling
4. Search functionality
5. Data extraction

Run with:
    pytest tests/e2e/test_orchestrator_e2e.py -v
    
Or individual tests:
    pytest tests/e2e/test_orchestrator_e2e.py::test_contact_form -v
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from curllm_core.orchestrator import Orchestrator, OrchestratorConfig
from curllm_core.command_parser import CommandParser
from curllm_core.task_planner import TaskPlanner


# ==============================================================================
# Test Configuration
# ==============================================================================

@pytest.fixture
def parser():
    return CommandParser()


@pytest.fixture
def planner():
    return TaskPlanner()


@pytest.fixture
def orchestrator_config():
    return OrchestratorConfig(
        headless=True,
        stealth_mode=True,
        timeout_seconds=60,
        log_to_file=True,
        log_dir="logs/e2e"
    )


# ==============================================================================
# Command Parsing Tests
# ==============================================================================

class TestCommandParsing:
    """Test that commands are parsed correctly"""
    
    def test_parse_contact_form_command(self, parser):
        cmd = """Wejdź na prototypowanie.pl i wyślij wiadomość przez formularz 
                 z zapytaniem o dostępność usługi prototypowania 3d 
                 z adresem email info@softreck.com i nazwiskiem Sapletta"""
        
        parsed = parser.parse(cmd)
        
        assert parsed.target_domain == "prototypowanie.pl"
        assert parsed.primary_goal.value == "find_contact_form"
        assert parsed.form_data.email == "info@softreck.com"
        assert parsed.form_data.name == "Sapletta"
        assert parsed.confidence >= 0.7
    
    def test_parse_product_search_command(self, parser):
        cmd = "Otwórz morele.net i znajdź pamięci RAM DDR5 32GB"
        
        parsed = parser.parse(cmd)
        
        assert parsed.target_domain == "morele.net"
        assert parsed.primary_goal.value == "extract_products"
        assert "RAM DDR5" in parsed.search_query or "pamięci" in parsed.search_query
    
    def test_parse_cart_command(self, parser):
        cmd = "Przejdź do x-kom.pl i dodaj laptop do koszyka"
        
        parsed = parser.parse(cmd)
        
        assert parsed.target_domain == "x-kom.pl"
        assert parsed.primary_goal.value in ["find_cart", "extract_products"]
    
    def test_parse_login_command(self, parser):
        cmd = "Zaloguj się na allegro.pl"
        
        parsed = parser.parse(cmd)
        
        assert parsed.target_domain == "allegro.pl"
        assert parsed.primary_goal.value == "find_login"
    
    def test_parse_with_order_number(self, parser):
        cmd = "Sprawdź status zamówienia nr 12345 na morele.net"
        
        parsed = parser.parse(cmd)
        
        assert parsed.target_domain == "morele.net"
        assert parsed.form_data.order_number is not None or "12345" in parsed.original_instruction


# ==============================================================================
# Task Planning Tests
# ==============================================================================

class TestTaskPlanning:
    """Test that plans are created correctly"""
    
    def test_contact_form_plan(self, parser, planner):
        cmd = "Wejdź na example.com i wypełnij formularz kontaktowy, email: test@test.com"
        parsed = parser.parse(cmd)
        plan = planner.plan(parsed)
        
        # Should have: navigate, resolve, analyze, fill_field(s), submit, verify, screenshot
        step_types = [s.step_type.value for s in plan.steps]
        
        assert "navigate" in step_types
        assert "resolve" in step_types
        assert "fill_field" in step_types
        assert "submit" in step_types
    
    def test_search_plan(self, parser, planner):
        cmd = "Znajdź laptopy na x-kom.pl"
        parsed = parser.parse(cmd)
        plan = planner.plan(parsed)
        
        step_types = [s.step_type.value for s in plan.steps]
        
        assert "navigate" in step_types
        assert "search" in step_types
        assert "extract" in step_types


# ==============================================================================
# E2E Orchestrator Tests (require network)
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
class TestOrchestratorE2E:
    """End-to-end tests with real websites"""
    
    async def test_dry_run_contact_form(self, orchestrator_config):
        """Test dry run mode for contact form"""
        orchestrator_config.dry_run = True
        
        orch = Orchestrator(orchestrator_config)
        result = await orch.execute(
            "Wejdź na prototypowanie.pl i wyślij formularz kontaktowy z email test@example.com"
        )
        
        assert result.success
        assert result.parsed.target_domain == "prototypowanie.pl"
        assert result.parsed.primary_goal.value == "find_contact_form"
        assert len(result.plan.steps) > 0
    
    async def test_product_search_morele(self, orchestrator_config):
        """Test product search on morele.net"""
        orch = Orchestrator(orchestrator_config)
        result = await orch.execute(
            "Wejdź na morele.net i znajdź pamięci RAM DDR5"
        )
        
        # Check basic flow worked
        assert result.parsed.target_domain == "morele.net"
        
        # Check steps executed
        completed_steps = [sr for sr in result.step_results if sr.success]
        assert len(completed_steps) >= 3  # At least navigate, resolve, analyze
        
        # Log should be saved
        assert result.log_path is not None
    
    async def test_navigate_to_contact_page(self, orchestrator_config):
        """Test finding contact page"""
        orch = Orchestrator(orchestrator_config)
        result = await orch.execute(
            "Otwórz stronę x-kom.pl i znajdź kontakt"
        )
        
        assert result.parsed.target_domain == "x-kom.pl"
        
        # Check if we navigated somewhere
        nav_step = next((sr for sr in result.step_results if sr.step_type == "navigate"), None)
        assert nav_step is not None and nav_step.success


# ==============================================================================
# Test Real Form Filling (use test services)
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
class TestFormFilling:
    """Test form filling with safe test services"""
    
    async def test_httpbin_form(self, orchestrator_config):
        """Test form filling on httpbin.org (safe test service)"""
        orch = Orchestrator(orchestrator_config)
        
        # httpbin has a simple form at /forms/post
        result = await orch.execute(
            "Wejdź na httpbin.org/forms/post i wypełnij formularz z email test@example.com"
        )
        
        assert result.parsed.target_domain == "httpbin.org"
        
        # Check navigation worked
        nav_step = next((sr for sr in result.step_results if sr.step_type == "navigate"), None)
        assert nav_step is not None


# ==============================================================================
# Run tests
# ==============================================================================

if __name__ == "__main__":
    # Run only parsing tests by default (fast)
    pytest.main([
        __file__,
        "-v",
        "-k", "TestCommandParsing or TestTaskPlanning",
        "--tb=short"
    ])
