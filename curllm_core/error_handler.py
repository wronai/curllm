"""
User-Friendly Error Handler.

Converts technical errors into helpful messages with actionable suggestions.
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def format_user_friendly_error(
    error: Exception, 
    context: str = "general",
    technical_details: Optional[str] = None
) -> Dict:
    """
    Convert technical error to user-friendly message.
    
    Args:
        error: The exception that occurred
        context: Context where error occurred (e.g., "form_fill", "navigation")
        technical_details: Additional technical information
        
    Returns:
        Dictionary with user-friendly error information:
        {
            "message": str,          # User-friendly message
            "suggestion": str,       # Actionable suggestion
            "technical": str,        # Technical details
            "severity": str,         # "critical", "error", "warning"
            "can_retry": bool        # Whether retry might help
        }
    """
    error_str = str(error)
    
    # Try to match against known error patterns
    for pattern, friendly_error in ERROR_MAPPINGS.items():
        if pattern.lower() in error_str.lower():
            result = friendly_error.copy()
            result["technical"] = technical_details or error_str
            logger.debug(f"Mapped error to user-friendly: {result['message']}")
            return result
    
    # Default fallback for unknown errors
    return {
        "message": "Wystąpił nieoczekiwany błąd podczas wykonywania zadania",
        "suggestion": "Sprawdź logi techniczne lub spróbuj ponownie",
        "technical": technical_details or error_str,
        "severity": "error",
        "can_retry": True
    }


# Error mappings: pattern -> user-friendly info
ERROR_MAPPINGS = {
    # Configuration errors
    "domain_dir": {
        "message": "Błąd wewnętrznej konfiguracji wypełniania formularzy",
        "suggestion": "Zrestartuj serwis curllm: ./curllm --stop-services && ./curllm --start-services",
        "severity": "critical",
        "can_retry": False
    },
    
    # Network/timeout errors
    "timeout": {
        "message": "Strona zbyt długo odpowiadała",
        "suggestion": "Sprawdź połączenie internetowe lub czy strona jest dostępna. Spróbuj ponownie.",
        "severity": "warning",
        "can_retry": True
    },
    "connection refused": {
        "message": "Nie można połączyć się ze stroną",
        "suggestion": "Sprawdź czy URL jest poprawny i czy strona jest dostępna",
        "severity": "error",
        "can_retry": True
    },
    "network error": {
        "message": "Błąd połączenia sieciowego",
        "suggestion": "Sprawdź połączenie internetowe i spróbuj ponownie",
        "severity": "error",
        "can_retry": True
    },
    
    # Browser/page errors
    "target closed": {
        "message": "Przeglądarka została zamknięta podczas operacji",
        "suggestion": "Uruchom zadanie ponownie",
        "severity": "error",
        "can_retry": True
    },
    "navigation failed": {
        "message": "Nie można załadować strony",
        "suggestion": "Sprawdź czy URL jest poprawny i czy strona jest dostępna",
        "severity": "error",
        "can_retry": True
    },
    
    # Form filling errors
    "no form found": {
        "message": "Nie znaleziono formularza na stronie",
        "suggestion": "Sprawdź czy URL prowadzi do strony z formularzem",
        "severity": "error",
        "can_retry": False
    },
    "field not found": {
        "message": "Nie znaleziono wymaganego pola w formularzu",
        "suggestion": "Sprawdź czy formularz zawiera wszystkie wymagane pola",
        "severity": "error",
        "can_retry": False
    },
    "invalid email": {
        "message": "Podany adres email jest nieprawidłowy",
        "suggestion": "Sprawdź format adresu email (np. user@example.com)",
        "severity": "warning",
        "can_retry": False
    },
    "required field": {
        "message": "Nie wypełniono wymaganego pola",
        "suggestion": "Upewnij się, że wszystkie wymagane pola są podane w instrukcji",
        "severity": "warning",
        "can_retry": False
    },
    
    # Captcha errors
    "captcha": {
        "message": "Wykryto CAPTCHA - wymagana interakcja użytkownika",
        "suggestion": "CAPTCHA nie może być automatycznie rozwiązana. Wykonaj to ręcznie lub poczekaj.",
        "severity": "warning",
        "can_retry": False
    },
    "recaptcha": {
        "message": "Wykryto reCAPTCHA",
        "suggestion": "reCAPTCHA wymaga ręcznego rozwiązania",
        "severity": "warning",
        "can_retry": False
    },
    
    # Human verification
    "human verification": {
        "message": "Strona wymaga weryfikacji ludzkiej",
        "suggestion": "Niektóre strony blokują automatyzację. Spróbuj trybu stealth.",
        "severity": "warning",
        "can_retry": True
    },
    "cloudflare": {
        "message": "Wykryto zabezpieczenie Cloudflare",
        "suggestion": "Użyj parametru --stealth aby ominąć zabezpieczenia",
        "severity": "warning",
        "can_retry": True
    },
    
    # LLM errors
    "llm timeout": {
        "message": "Model językowy zbyt długo odpowiadał",
        "suggestion": "Spróbuj ponownie lub użyj szybszego modelu",
        "severity": "error",
        "can_retry": True
    },
    "model not found": {
        "message": "Model językowy nie jest dostępny",
        "suggestion": "Sprawdź czy model jest zainstalowany: ollama list",
        "severity": "critical",
        "can_retry": False
    },
    "ollama": {
        "message": "Błąd komunikacji z Ollama",
        "suggestion": "Sprawdź czy Ollama jest uruchomiona: ollama serve",
        "severity": "critical",
        "can_retry": False
    },
    
    # Permission errors
    "permission denied": {
        "message": "Brak uprawnień do wykonania operacji",
        "suggestion": "Sprawdź uprawnienia plików lub uruchom z odpowiednimi prawami",
        "severity": "error",
        "can_retry": False
    },
    
    # Generic selectors
    "selector": {
        "message": "Nie znaleziono elementu na stronie",
        "suggestion": "Element może nie istnieć lub strona się zmieniła",
        "severity": "warning",
        "can_retry": True
    },
}


def get_error_category(error: Exception) -> str:
    """
    Categorize error type.
    
    Returns:
        Category name: "network", "browser", "form", "llm", "captcha", "unknown"
    """
    error_str = str(error).lower()
    
    if any(k in error_str for k in ["timeout", "connection", "network"]):
        return "network"
    elif any(k in error_str for k in ["browser", "target", "navigation"]):
        return "browser"
    elif any(k in error_str for k in ["form", "field", "email"]):
        return "form"
    elif any(k in error_str for k in ["llm", "model", "ollama"]):
        return "llm"
    elif any(k in error_str for k in ["captcha", "recaptcha"]):
        return "captcha"
    else:
        return "unknown"


def should_retry_error(error: Exception) -> bool:
    """
    Determine if error suggests a retry might help.
    
    Args:
        error: The exception that occurred
        
    Returns:
        True if retry is recommended
    """
    friendly = format_user_friendly_error(error)
    return friendly.get("can_retry", False)


def format_error_for_logging(error: Exception, context: str = "") -> str:
    """
    Format error for structured logging.
    
    Args:
        error: The exception
        context: Additional context
        
    Returns:
        Formatted error string for logs
    """
    friendly = format_user_friendly_error(error, context)
    
    lines = [
        f"❌ {friendly['message']}",
        f"💡 {friendly['suggestion']}",
        f"🔧 Technical: {friendly['technical']}"
    ]
    
    if context:
        lines.insert(0, f"📍 Context: {context}")
    
    return "\n".join(lines)


def create_error_response(
    error: Exception,
    context: str = "",
    include_stacktrace: bool = False
) -> Dict:
    """
    Create standardized error response for API/CLI.
    
    Args:
        error: The exception
        context: Where the error occurred
        include_stacktrace: Whether to include full stacktrace
        
    Returns:
        Standardized error response dictionary
    """
    import traceback
    
    friendly = format_user_friendly_error(error, context)
    
    response = {
        "success": False,
        "error": {
            "message": friendly["message"],
            "suggestion": friendly["suggestion"],
            "severity": friendly["severity"],
            "can_retry": friendly["can_retry"],
            "category": get_error_category(error),
        }
    }
    
    if include_stacktrace:
        response["error"]["stacktrace"] = traceback.format_exc()
        response["error"]["technical_details"] = friendly["technical"]
    
    return response
