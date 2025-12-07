#!/usr/bin/env python3
"""
Tests for LLMConfig multi-provider support
"""

import os
import pytest
from unittest.mock import patch


# Import from curllm_core
from curllm_core.llm_config import (
    LLMConfig,
    LLMPresets,
    PROVIDER_ENV_VARS,
    PROVIDER_BASE_URLS,
    DEFAULT_MODELS,
)


class TestLLMConfigBasic:
    """Basic LLMConfig functionality tests"""
    
    def test_default_config(self):
        """Default config should use Ollama"""
        config = LLMConfig()
        assert config.provider_name == "ollama"
        assert config.model_name == "qwen2.5:7b"
        assert config.is_local is True
        assert config.requires_api_key is False
    
    def test_provider_parsing(self):
        """Test provider string parsing"""
        config = LLMConfig(provider="openai/gpt-4o-mini")
        assert config.provider_name == "openai"
        assert config.model_name == "gpt-4o-mini"
        
        config = LLMConfig(provider="anthropic/claude-3-haiku-20240307")
        assert config.provider_name == "anthropic"
        assert config.model_name == "claude-3-haiku-20240307"
    
    def test_provider_only(self):
        """Test when only provider is specified (uses default model)"""
        config = LLMConfig(provider="openai")
        assert config.provider_name == "openai"
        assert config.model_name == DEFAULT_MODELS["openai"]
    
    def test_base_url_defaults(self):
        """Test base URL defaults for each provider"""
        for provider, url in PROVIDER_BASE_URLS.items():
            config = LLMConfig(provider=f"{provider}/test-model")
            assert config.base_url == url
    
    def test_custom_base_url(self):
        """Test custom base URL override"""
        custom_url = "https://custom.api.com/v1"
        config = LLMConfig(provider="openai/gpt-4o", base_url=custom_url)
        assert config.base_url == custom_url


class TestLLMConfigAPIToken:
    """API token resolution tests"""
    
    def test_explicit_api_token(self):
        """Test explicit API token"""
        config = LLMConfig(provider="openai/gpt-4o", api_token="sk-test-token")
        assert config.resolved_api_token == "sk-test-token"
    
    def test_env_prefix_api_token(self):
        """Test env: prefix for API token"""
        with patch.dict(os.environ, {"MY_CUSTOM_KEY": "custom-token-value"}):
            config = LLMConfig(provider="openai/gpt-4o", api_token="env:MY_CUSTOM_KEY")
            assert config.resolved_api_token == "custom-token-value"
    
    def test_auto_env_resolution(self):
        """Test automatic environment variable resolution"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "auto-resolved-token"}):
            config = LLMConfig(provider="openai/gpt-4o")
            assert config.resolved_api_token == "auto-resolved-token"
    
    def test_env_var_mapping(self):
        """Test each provider has correct env var mapping"""
        expected = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }
        for provider, env_var in expected.items():
            assert PROVIDER_ENV_VARS.get(provider) == env_var
    
    def test_ollama_no_api_key(self):
        """Ollama should not require API key"""
        config = LLMConfig(provider="ollama/llama3")
        assert config.requires_api_key is False
        assert PROVIDER_ENV_VARS.get("ollama") is None


class TestLLMConfigValidation:
    """Validation tests"""
    
    def test_validate_with_api_key(self):
        """Validation should pass when API key is present"""
        config = LLMConfig(provider="openai/gpt-4o", api_token="sk-test")
        assert config.validate() is True
    
    def test_validate_without_api_key_for_cloud(self):
        """Validation should fail for cloud providers without API key"""
        with patch.dict(os.environ, {}, clear=True):
            # Clear relevant env vars
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
                os.environ.pop(key, None)
            
            config = LLMConfig(provider="openai/gpt-4o")
            with pytest.raises(ValueError, match="API token required"):
                config.validate()
    
    def test_validate_ollama_without_key(self):
        """Ollama should validate without API key"""
        config = LLMConfig(provider="ollama/llama3")
        assert config.validate() is True


class TestLLMConfigSerialization:
    """Serialization tests"""
    
    def test_to_dict(self):
        """Test to_dict serialization"""
        config = LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token="sk-test",
            temperature=0.5,
            max_tokens=2048
        )
        d = config.to_dict()
        
        assert d["provider"] == "openai/gpt-4o-mini"
        assert d["provider_name"] == "openai"
        assert d["model_name"] == "gpt-4o-mini"
        assert d["temperature"] == 0.5
        assert d["max_tokens"] == 2048
        assert d["has_api_token"] is True
        assert d["is_local"] is False
    
    def test_from_env(self):
        """Test from_env factory method"""
        env_vars = {
            "CURLLM_LLM_PROVIDER": "groq/llama3-8b-8192",
            "GROQ_API_KEY": "test-groq-key",
            "CURLLM_TEMPERATURE": "0.7",
        }
        with patch.dict(os.environ, env_vars):
            config = LLMConfig.from_env()
            
            assert config.provider_name == "groq"
            assert config.model_name == "llama3-8b-8192"
            assert config.temperature == 0.7


class TestLLMPresets:
    """LLMPresets tests"""
    
    def test_local_presets(self):
        """Test local Ollama presets"""
        fast = LLMPresets.local_fast()
        assert fast.provider_name == "ollama"
        assert "3b" in fast.model_name
        
        balanced = LLMPresets.local_balanced()
        assert balanced.provider_name == "ollama"
        assert "7b" in balanced.model_name
        
        smart = LLMPresets.local_smart()
        assert smart.provider_name == "ollama"
        assert "14b" in smart.model_name
    
    def test_openai_presets(self):
        """Test OpenAI presets"""
        fast = LLMPresets.openai_fast()
        assert fast.provider_name == "openai"
        assert "mini" in fast.model_name
        
        smart = LLMPresets.openai_smart()
        assert smart.provider_name == "openai"
        assert "gpt-4o" in smart.model_name
    
    def test_anthropic_presets(self):
        """Test Anthropic presets"""
        fast = LLMPresets.anthropic_fast()
        assert fast.provider_name == "anthropic"
        assert "haiku" in fast.model_name
        
        smart = LLMPresets.anthropic_smart()
        assert smart.provider_name == "anthropic"
        assert "sonnet" in smart.model_name
    
    def test_other_presets(self):
        """Test other provider presets"""
        gemini = LLMPresets.gemini_fast()
        assert gemini.provider_name == "gemini"
        
        groq_fast = LLMPresets.groq_fast()
        assert groq_fast.provider_name == "groq"
        assert "8b" in groq_fast.model_name
        
        groq_smart = LLMPresets.groq_smart()
        assert groq_smart.provider_name == "groq"
        assert "70b" in groq_smart.model_name
        
        deepseek = LLMPresets.deepseek()
        assert deepseek.provider_name == "deepseek"


class TestLLMConfigIntegration:
    """Integration tests for LLMConfig with factory"""
    
    def test_setup_llm_with_ollama(self):
        """Test setup_llm with Ollama config"""
        from curllm_core.llm_factory import setup_llm
        from curllm_core.llm import SimpleOllama
        
        config = LLMConfig(provider="ollama/test-model")
        llm = setup_llm(config)
        
        assert isinstance(llm, SimpleOllama)
        assert llm.model == "test-model"
    
    def test_setup_llm_with_openai(self):
        """Test setup_llm with OpenAI config"""
        from curllm_core.llm_factory import setup_llm, LiteLLMClient, OpenAICompatibleClient, LITELLM_AVAILABLE
        
        config = LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token="sk-test-token"
        )
        llm = setup_llm(config)
        
        # LiteLLM is used when available, otherwise OpenAICompatibleClient
        if LITELLM_AVAILABLE:
            assert isinstance(llm, LiteLLMClient)
        else:
            assert isinstance(llm, OpenAICompatibleClient)
        assert "gpt-4o-mini" in llm.model
    
    def test_setup_llm_with_anthropic(self):
        """Test setup_llm with Anthropic config"""
        from curllm_core.llm_factory import setup_llm, LiteLLMClient, AnthropicClient, LITELLM_AVAILABLE
        
        config = LLMConfig(
            provider="anthropic/claude-3-haiku-20240307",
            api_token="sk-ant-test"
        )
        llm = setup_llm(config)
        
        # LiteLLM is used when available, otherwise AnthropicClient
        if LITELLM_AVAILABLE:
            assert isinstance(llm, LiteLLMClient)
        else:
            assert isinstance(llm, AnthropicClient)
        assert "claude" in llm.model
    
    def test_setup_llm_with_gemini(self):
        """Test setup_llm with Gemini config"""
        from curllm_core.llm_factory import setup_llm, LiteLLMClient, GeminiClient, LITELLM_AVAILABLE
        
        config = LLMConfig(
            provider="gemini/gemini-2.0-flash",
            api_token="test-gemini-key"
        )
        llm = setup_llm(config)
        
        # LiteLLM is used when available, otherwise GeminiClient
        if LITELLM_AVAILABLE:
            assert isinstance(llm, LiteLLMClient)
        else:
            assert isinstance(llm, GeminiClient)
        assert "gemini" in llm.model
    
    def test_setup_llm_with_groq(self):
        """Test setup_llm with Groq config (OpenAI-compatible)"""
        from curllm_core.llm_factory import setup_llm, LiteLLMClient, OpenAICompatibleClient, LITELLM_AVAILABLE
        
        config = LLMConfig(
            provider="groq/llama3-70b-8192",
            api_token="gsk_test"
        )
        llm = setup_llm(config)
        
        # LiteLLM is used when available, otherwise OpenAICompatibleClient
        if LITELLM_AVAILABLE:
            assert isinstance(llm, LiteLLMClient)
        else:
            assert isinstance(llm, OpenAICompatibleClient)
        assert "llama" in llm.model
    
    def test_setup_llm_legacy_mode(self):
        """Test legacy mode without LLMConfig"""
        from curllm_core.llm_factory import setup_llm
        from curllm_core.llm import SimpleOllama
        
        # When no config and no CURLLM_LLM_PROVIDER, should use legacy Ollama
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CURLLM_LLM_PROVIDER", None)
            llm = setup_llm()
            assert isinstance(llm, SimpleOllama)
