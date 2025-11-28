#!/usr/bin/env python3
"""
Mock Ollama Server for Testing

Simulates Ollama API responses for deterministic testing.
Returns pre-defined JSON/YAML commands based on input.
"""

from flask import Flask, request, jsonify
import json
import time

app = Flask(__name__)

# Mock responses for different scenarios
MOCK_RESPONSES = {
    'fill_form': {
        'action': 'analyze_form',
        'components': [
            {'type': 'dom-snapshot', 'params': {'include_values': True}},
            {'type': 'field-mapper', 'params': {'strategy': 'fuzzy'}},
            {'type': 'action-plan', 'params': {'strategy': 'smart'}}
        ]
    },
    'extract_products': {
        'action': 'extract_data',
        'type': 'text',
        'selector': '.product'
    },
    'login': {
        'action': 'execute_flow',
        'steps': [
            {'type': 'dom-snapshot', 'params': {'include_values': True}},
            {'type': 'fill', 'selector': '#username', 'value': 'testuser'},
            {'type': 'fill', 'selector': '#password', 'value': 'testpass'},
            {'type': 'click', 'selector': 'button[type="submit"]'}
        ]
    }
}


@app.route('/api/generate', methods=['POST'])
def generate():
    """Mock Ollama generate endpoint"""
    data = request.json
    prompt = data.get('prompt', '')
    
    # Determine response based on prompt content
    response_data = _get_response_for_prompt(prompt)
    
    # Simulate thinking time
    time.sleep(0.1)
    
    return jsonify({
        'model': 'qwen2.5:7b',
        'created_at': time.time(),
        'response': json.dumps(response_data),
        'done': True
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """Mock Ollama chat endpoint"""
    data = request.json
    messages = data.get('messages', [])
    
    last_message = messages[-1].get('content', '') if messages else ''
    response_data = _get_response_for_prompt(last_message)
    
    return jsonify({
        'model': 'qwen2.5:7b',
        'created_at': time.time(),
        'message': {
            'role': 'assistant',
            'content': json.dumps(response_data)
        },
        'done': True
    })


@app.route('/api/tags', methods=['GET'])
def tags():
    """Mock model list"""
    return jsonify({
        'models': [
            {
                'name': 'qwen2.5:7b',
                'size': 4661211648,
                'digest': 'mock123'
            }
        ]
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'mode': 'mock'})


def _get_response_for_prompt(prompt: str) -> dict:
    """Generate appropriate response based on prompt"""
    prompt_lower = prompt.lower()
    
    if 'fill' in prompt_lower and 'form' in prompt_lower:
        return {
            'action': 'fill_field',
            'field': 'name' if 'name' in prompt_lower else 'email',
            'value': _extract_value_from_prompt(prompt),
            'strategy': 'smart'
        }
    elif 'extract' in prompt_lower or 'get' in prompt_lower:
        return {
            'action': 'extract_data',
            'type': 'forms' if 'form' in prompt_lower else 'text'
        }
    elif 'login' in prompt_lower:
        return MOCK_RESPONSES['login']
    elif 'validate' in prompt_lower or 'check' in prompt_lower:
        return {
            'action': 'validate_state',
            'type': 'form_filled',
            'expectations': {}
        }
    elif 'plan' in prompt_lower or 'next' in prompt_lower:
        return {
            'action': 'plan_action',
            'strategy': 'smart',
            'instruction': prompt
        }
    else:
        # Default: return form analysis
        return MOCK_RESPONSES['fill_form']


def _extract_value_from_prompt(prompt: str) -> str:
    """Extract value from prompt (simple extraction)"""
    # Look for patterns like "name=John" or "email=test@example.com"
    import re
    match = re.search(r'[=:]\s*([^\s,]+)', prompt)
    return match.group(1) if match else 'test_value'


if __name__ == '__main__':
    print("Starting Mock Ollama Server on http://0.0.0.0:11434")
    app.run(host='0.0.0.0', port=11434, debug=False)
