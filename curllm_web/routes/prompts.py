"""Prompts routes - CRUD for prompts"""

from flask import Blueprint, request, jsonify

from curllm_web.prompts.prompt_manager import load_prompts, save_prompts

prompts_bp = Blueprint('prompts', __name__)


@prompts_bp.route('/api/prompts', methods=['GET'])
def get_prompts():
    """Get all prompts"""
    prompts = load_prompts()
    return jsonify({'prompts': prompts})


@prompts_bp.route('/api/prompts', methods=['POST'])
def add_prompt():
    """Add new prompt"""
    data = request.json
    prompts = load_prompts()
    
    new_prompt = {
        'id': data.get('id', f"custom_{len(prompts)}"),
        'name': data.get('name', 'Nowy prompt'),
        'prompt': data.get('prompt', '')
    }
    
    prompts.append(new_prompt)
    if save_prompts(prompts):
        return jsonify({'success': True, 'prompt': new_prompt})
    return jsonify({'success': False, 'error': 'Failed to save prompt'}), 500


@prompts_bp.route('/api/prompts/<prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Update existing prompt"""
    data = request.json
    prompts = load_prompts()
    
    for i, prompt in enumerate(prompts):
        if prompt['id'] == prompt_id:
            prompts[i]['name'] = data.get('name', prompt['name'])
            prompts[i]['prompt'] = data.get('prompt', prompt['prompt'])
            if save_prompts(prompts):
                return jsonify({'success': True, 'prompt': prompts[i]})
            return jsonify({'success': False, 'error': 'Failed to save prompt'}), 500
    
    return jsonify({'success': False, 'error': 'Prompt not found'}), 404


@prompts_bp.route('/api/prompts/<prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete prompt"""
    prompts = load_prompts()
    prompts = [p for p in prompts if p['id'] != prompt_id]
    
    if save_prompts(prompts):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Failed to save prompts'}), 500
