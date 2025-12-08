import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from curllm_core.config import config
from curllm_core.logger import RunLogger
from curllm_core.llm_factory import setup_llm as setup_llm_factory
from curllm_core.llm_config import LLMConfig
from curllm_core.agent_factory import create_agent as create_agent_factory
from curllm_core.vision import VisionAnalyzer
from curllm_core.captcha import CaptchaSolver
from curllm_core.stealth import StealthConfig
from curllm_core.runtime import parse_runtime_from_instruction
from curllm_core.headers import normalize_headers
from curllm_core.browser_setup import setup_browser
from curllm_core.wordpress import WordPressAutomation
from curllm_core.proxy import resolve_proxy
from curllm_core.page_context import extract_page_context
from curllm_core.actions import execute_action
from curllm_core.result_evaluator import evaluate_run_success
from curllm_core.human_verify import handle_human_verification, looks_like_human_verify_text
from curllm_core.captcha_widget import handle_captcha_image as _handle_captcha_image_widget, handle_widget_captcha as _handle_widget_captcha
from curllm_core.page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies, is_block_page as _is_block_page
from curllm_core.extraction import generic_fastpath, direct_fastpath, product_heuristics, fallback_extract, extract_articles_eval, validate_with_llm, extract_links_by_selectors
from curllm_core.captcha_slider import attempt_slider_challenge
from curllm_core.slider_plugin import try_external_slider_solver
from curllm_core.bql import BQLExecutor
from curllm_core.validation_utils import should_validate
from curllm_core.screenshots import take_screenshot as _take_screenshot_func
from curllm_core.form_fill import deterministic_form_fill as _deterministic_form_fill_func, parse_form_pairs as _parse_form_pairs_func
from curllm_core.llm_field_filler import llm_guided_field_fill as _llm_guided_field_fill_func
from curllm_core.config_logger import log_all_config
from curllm_core.planner_progress import progress_tick as _progress_tick_func
from curllm_core.product_extract import multi_stage_product_extract as _multi_stage_product_extract_func
from curllm_core.bql_utils import parse_bql as _parse_bql_util
from curllm_core.dom_utils import detect_honeypot as _detect_honeypot_func
from curllm_core.diagnostics import diagnose_url_issue as _diagnose_url_issue_func
from curllm_core.navigation import open_page_with_prechecks as _open_page_with_prechecks_func
from curllm_core.rerun_cmd import build_rerun_curl as _build_rerun_curl_func
from curllm_core.task_runner import run_task as _run_task
from curllm_core.result_store import apply_diff_and_store as _apply_diff_and_store


def _should_validate(instruction: Optional[str], data: Optional[Any]) -> bool:
    return should_validate(instruction, data)
