"""curllm API client"""

import asyncio
import logging
import os
from typing import Dict

import aiohttp

logger = logging.getLogger(__name__)


async def call_curllm_api(url: str, instruction: str, options: Dict) -> Dict:
    """Call curllm API server"""
    api_host = os.getenv('CURLLM_API_HOST', 'http://localhost:8000')
    
    payload = {
        'url': url,
        'data': instruction,  # API server expects 'data' not 'instruction'
        'visual_mode': options.get('visual_mode', False),
        'stealth_mode': options.get('stealth_mode', False),
        'captcha_solver': options.get('captcha_solver', False),
        'use_bql': options.get('use_bql', False),
        'export_format': options.get('export_format', 'json')
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{api_host}/api/execute', 
                json=payload, 
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {
                        'error': f'API error: {resp.status}', 
                        'details': error_text,
                        'help': f'Sprawdź czy serwer curllm API działa na {api_host}. Uruchom: python curllm_server.py'
                    }
    except aiohttp.ClientConnectorError as e:
        logger.error(f"Cannot connect to curllm API at {api_host}: {e}")
        return {
            'error': f'Nie można połączyć z API serwrem na {api_host}',
            'details': str(e),
            'help': 'Uruchom serwer API w osobnym terminalu: python curllm_server.py'
        }
    except asyncio.TimeoutError:
        logger.error("API request timeout")
        return {
            'error': 'Timeout - zadanie trwało zbyt długo (max 5 minut)',
            'help': 'Spróbuj prostszej instrukcji lub włącz tryb wizualny'
        }
    except Exception as e:
        logger.error(f"Error calling curllm API: {e}")
        return {
            'error': f'Błąd wywołania API: {str(e)}',
            'help': f'Sprawdź czy serwer działa: curl {api_host}/health'
        }
