"""
DOM Snapshot Fix Components - Fix issues with DOM value extraction

Addresses the critical bug where form field values are not captured correctly.
"""

from typing import Any, Dict, List
from ..core import Component, TransformComponent
from ..uri import StreamwareURI
from ..registry import register
from ..exceptions import ComponentError
from ...diagnostics import get_logger

logger = get_logger(__name__)


@register("dom-snapshot")
class DOMSnapshotComponent(Component):
    """
    Enhanced DOM snapshot with correct value extraction
    
    URI: dom-snapshot://capture?include_values=true&include_computed=false
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Dict[str, Any]:
        """
        Capture DOM snapshot with enhanced value extraction
        
        This fixes the bug where field values are always empty
        """
        if not isinstance(data, dict) or 'page' not in data:
            raise ComponentError("Input must contain 'page' (Playwright page object)")
            
        page = data['page']
        include_values = self.uri.get_param('include_values', True)
        include_computed = self.uri.get_param('include_computed', False)
        
        try:
            # Extract forms with actual values
            forms = self._extract_forms_with_values(page, include_values)
            
            snapshot = {
                'title': page.title(),
                'url': page.url,
                'forms': forms,
                'links': self._extract_links(page),
                'text': page.inner_text('body')[:5000],  # Limit text
            }
            
            if include_computed:
                snapshot['computed_styles'] = self._extract_computed_styles(page)
            
            # Preserve other keys from input (except 'page') for chaining
            for key, value in data.items():
                if key != 'page' and key not in snapshot:
                    snapshot[key] = value
                
            return snapshot
            
        except Exception as e:
            logger.error(f"DOM snapshot error: {e}")
            raise ComponentError(f"Failed to capture DOM snapshot: {e}")
            
    def _extract_forms_with_values(self, page, include_values: bool) -> List[Dict]:
        """Extract forms with ACTUAL field values"""
        try:
            # JavaScript to extract form data with actual values
            js_code = """
            () => {
                const forms = Array.from(document.querySelectorAll('form'));
                return forms.map(form => {
                    const fields = Array.from(form.querySelectorAll('input, textarea, select'));
                    return {
                        id: form.id || null,
                        action: form.action || null,
                        method: form.method || 'get',
                        fields: fields.map(field => {
                            // Get ACTUAL value from DOM property, not attribute
                            let value = '';
                            if (field.tagName === 'INPUT') {
                                if (field.type === 'checkbox' || field.type === 'radio') {
                                    value = field.checked ? field.value || 'on' : '';
                                } else {
                                    value = field.value || '';  // Use .value property
                                }
                            } else if (field.tagName === 'TEXTAREA') {
                                value = field.value || '';
                            } else if (field.tagName === 'SELECT') {
                                value = field.value || '';
                            }
                            
                            return {
                                name: field.name || field.id || null,
                                type: field.type || field.tagName.toLowerCase(),
                                value: value,  // ACTUAL current value
                                placeholder: field.placeholder || '',
                                required: field.required || false,
                                disabled: field.disabled || false,
                                visible: field.offsetParent !== null,
                                selector: field.name ? `[name="${field.name}"]` : `#${field.id}`
                            };
                        })
                    };
                });
            }
            """
            
            forms = page.evaluate(js_code)
            return forms
            
        except Exception as e:
            logger.error(f"Form extraction error: {e}")
            return []
            
    def _extract_links(self, page) -> List[Dict]:
        """Extract links from page"""
        try:
            js_code = """
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links.slice(0, 50).map(link => ({
                    text: link.textContent.trim().substring(0, 100),
                    url: link.href,
                    external: !link.href.startsWith(window.location.origin)
                }));
            }
            """
            return page.evaluate(js_code)
        except:
            return []
            
    def _extract_computed_styles(self, page) -> Dict:
        """Extract computed styles for key elements"""
        # Optional: extract computed styles for debugging
        return {}


@register("dom-diff")
class DOMDiffComponent(TransformComponent):
    """
    Calculate difference between two DOM snapshots
    
    URI: dom-diff://calculate?focus=forms|all
    """
    
    def transform(self, data: Any) -> Dict[str, Any]:
        """Calculate DOM diff"""
        if not isinstance(data, dict) or 'before' not in data or 'after' not in data:
            raise ComponentError("Input must contain 'before' and 'after' snapshots")
            
        before = data['before']
        after = data['after']
        focus = self.uri.get_param('focus', 'forms')
        
        diff = {
            'url_changed': before.get('url') != after.get('url'),
            'title_changed': before.get('title') != after.get('title'),
        }
        
        if focus == 'forms' or focus == 'all':
            diff['forms'] = self._diff_forms(
                before.get('forms', []),
                after.get('forms', [])
            )
            
        if focus == 'all':
            diff['text_changed'] = before.get('text') != after.get('text')
            diff['links_changed'] = len(before.get('links', [])) != len(after.get('links', []))
            
        return diff
        
    def _diff_forms(self, before_forms: List, after_forms: List) -> Dict:
        """Calculate form differences"""
        if len(before_forms) != len(after_forms):
            return {'changed': True, 'reason': 'form_count_different'}
            
        changed_fields = []
        
        for i, (before_form, after_form) in enumerate(zip(before_forms, after_forms)):
            before_fields = {f['name']: f.get('value', '') for f in before_form.get('fields', [])}
            after_fields = {f['name']: f.get('value', '') for f in after_form.get('fields', [])}
            
            for field_name in before_fields:
                if field_name in after_fields:
                    if before_fields[field_name] != after_fields[field_name]:
                        changed_fields.append({
                            'form_index': i,
                            'field': field_name,
                            'before': before_fields[field_name],
                            'after': after_fields[field_name]
                        })
                        
        return {
            'changed': len(changed_fields) > 0,
            'changed_fields': changed_fields,
            'change_count': len(changed_fields)
        }


@register("dom-validate")
class DOMValidateComponent(Component):
    """
    Validate DOM state against expectations
    
    URI: dom-validate://check?type=form_filled|navigation|content
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Dict[str, Any]:
        """Validate DOM state"""
        if not isinstance(data, dict) or 'snapshot' not in data:
            raise ComponentError("Input must contain 'snapshot'")
            
        snapshot = data['snapshot']
        expectations = data.get('expectations', {})
        validation_type = self.uri.get_param('type', 'form_filled')
        
        if validation_type == 'form_filled':
            return self._validate_form_filled(snapshot, expectations)
        elif validation_type == 'navigation':
            return self._validate_navigation(snapshot, expectations)
        elif validation_type == 'content':
            return self._validate_content(snapshot, expectations)
        else:
            return {'valid': False, 'reason': 'unknown_validation_type'}
            
    def _validate_form_filled(self, snapshot: Dict, expectations: Dict) -> Dict:
        """Validate that form fields are filled correctly"""
        forms = snapshot.get('forms', [])
        if not forms:
            return {'valid': False, 'reason': 'no_forms_found'}
            
        expected_fields = expectations.get('fields', {})
        validation_results = []
        
        for form in forms:
            for field in form.get('fields', []):
                field_name = field.get('name')
                field_value = field.get('value', '')
                
                if field_name in expected_fields:
                    expected_value = expected_fields[field_name]
                    is_valid = field_value == expected_value or (expected_value and len(field_value) > 0)
                    
                    validation_results.append({
                        'field': field_name,
                        'expected': expected_value,
                        'actual': field_value,
                        'valid': is_valid
                    })
                    
        all_valid = all(r['valid'] for r in validation_results)
        
        return {
            'valid': all_valid,
            'results': validation_results,
            'validated_count': len(validation_results)
        }
        
    def _validate_navigation(self, snapshot: Dict, expectations: Dict) -> Dict:
        """Validate navigation occurred"""
        expected_url = expectations.get('url', '')
        actual_url = snapshot.get('url', '')
        
        valid = expected_url in actual_url if expected_url else True
        
        return {
            'valid': valid,
            'expected_url': expected_url,
            'actual_url': actual_url
        }
        
    def _validate_content(self, snapshot: Dict, expectations: Dict) -> Dict:
        """Validate page content"""
        expected_text = expectations.get('contains_text', '')
        actual_text = snapshot.get('text', '')
        
        valid = expected_text.lower() in actual_text.lower() if expected_text else True
        
        return {
            'valid': valid,
            'expected_text': expected_text,
            'found': valid
        }


@register("field-mapper")
class FieldMapperComponent(TransformComponent):
    """
    Map instruction fields to form fields intelligently
    
    URI: field-mapper://map?strategy=fuzzy|exact|semantic
    """
    
    def transform(self, data: Any) -> Dict[str, Any]:
        """Map instruction to form fields"""
        if not isinstance(data, dict):
            raise ComponentError("Input must be dictionary")
            
        instruction = data.get('instruction', '')
        forms = data.get('forms', [])
        strategy = self.uri.get_param('strategy', 'fuzzy')
        
        # Extract data from instruction
        extracted = self._extract_from_instruction(instruction)
        
        # Map to form fields
        mapping = self._map_to_fields(extracted, forms, strategy)
        
        return {
            'extracted_data': extracted,
            'field_mapping': mapping,
            'mapping_confidence': self._calculate_confidence(mapping)
        }
        
    def _extract_from_instruction(self, instruction: str) -> Dict[str, str]:
        """Extract field values from instruction - DEPRECATED, use LLM version"""
        # Try to use LLM-based extraction if available
        try:
            from .llm_decision import extract_fields_from_instruction_llm
            import asyncio
            
            # Check if we have LLM in context
            llm = getattr(self, '_llm', None)
            if llm:
                # Run async function
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in async context, can't use run_until_complete
                    # Fall back to simple extraction
                    pass
                else:
                    return loop.run_until_complete(
                        extract_fields_from_instruction_llm(llm, instruction)
                    )
        except ImportError:
            pass
        
        # Fallback: Simple parsing without regex patterns
        # Just extract obvious key=value pairs
        data = {}
        
        # Simple split-based extraction
        parts = instruction.replace(':', '=').split(',')
        for part in parts:
            if '=' in part:
                key_val = part.split('=', 1)
                if len(key_val) == 2:
                    key = key_val[0].strip().lower()
                    val = key_val[1].strip()
                    if key in ['name', 'email', 'phone', 'subject', 'message', 'first_name', 'last_name']:
                        data[key] = val
                
        return data
        
    def _map_to_fields(self, extracted: Dict, forms: List, strategy: str) -> List[Dict]:
        """Map extracted data to form fields - uses LLM for semantic strategy"""
        if not forms:
            return []
            
        mapping = []
        form = forms[0]  # Use first form
        fields = form.get('fields', [])
        
        for field_type, value in extracted.items():
            matched_field = self._find_matching_field(field_type, fields, strategy)
            
            if matched_field:
                field_name = matched_field.get('name', '')
                mapping.append({
                    'instruction_field': field_type,
                    'form_field': field_name,
                    'selector': matched_field.get('selector') or f"[name='{field_name}']",
                    'value': value,
                    'confidence': 0.9 if strategy == 'exact' else 0.7
                })
            else:
                logger.warning(f"Could not map field: {field_type}")
                mapping.append({
                    'instruction_field': field_type,
                    'form_field': None,
                    'value': value,
                    'confidence': 0.0,
                    'error': 'no_matching_field'
                })
                
        return mapping
    
    def _find_matching_field(self, field_type: str, fields: List, strategy: str) -> Dict:
        """Find matching form field for given field type"""
        field_type_lower = field_type.lower()
        
        for form_field in fields:
            field_name = (form_field.get('name') or '').lower()
            form_type = form_field.get('type', '').lower()
            
            if strategy == 'exact':
                if field_type_lower == field_name:
                    return form_field
            else:
                # Fuzzy/semantic matching
                if self._fields_match(field_type_lower, field_name, form_type):
                    return form_field
        
        return None
    
    def _fields_match(self, data_key: str, field_name: str, field_type: str) -> bool:
        """Check if data key matches field - semantic matching"""
        # Direct match
        if data_key in field_name or field_name in data_key:
            return True
        
        # Semantic concept groups for type-based matching
        # These are language-agnostic concepts, NOT hardcoded selectors
        phone_concepts = {'phone', 'tel', 'telephone', 'mobile', 'telefon', 'komórka'}
        message_concepts = {'message', 'msg', 'content', 'body', 'wiadomość', 'treść'}
        
        # Type-based matching with semantic concepts
        if data_key == 'email' and field_type == 'email':
            return True
        if data_key in phone_concepts and field_type == 'tel':
            return True
        if data_key in phone_concepts and any(p in field_name for p in phone_concepts):
            return True
        if data_key in message_concepts and field_type == 'textarea':
            return True
        
        return False
        
    def _calculate_confidence(self, mapping: List) -> float:
        """Calculate overall mapping confidence"""
        if not mapping:
            return 0.0
            
        confidences = [m.get('confidence', 0.0) for m in mapping]
        return sum(confidences) / len(confidences)
