#!/usr/bin/env python3
"""
Form Field Detector - Wykrywa WSZYSTKIE pola w formularzu bez klasyfikacji.

Zwraca surowe dane o polach, które LLM może zanalizować i zaplanować wypełnienie.
"""

from typing import Dict, List, Any, Optional


async def detect_all_form_fields(page, target_form_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Wykrywa wszystkie pola w formularzu wraz z metadanymi.
    
    Zwraca:
    - detected_fields: Lista wszystkich pól z metadanymi
    - form_metadata: Informacje o formularzu
    """
    
    result = await page.evaluate(
        """
        (targetFormId) => {
          // Helper: Get form element
          const getForm = (el) => {
            if (!el) return null;
            let curr = el;
            while (curr && curr !== document.body) {
              if (curr.tagName === 'FORM') return curr;
              curr = curr.parentElement;
            }
            return null;
          };
          
          // Find target form
          let targetForm = null;
          if (targetFormId) {
            targetForm = document.getElementById(targetFormId);
            if (!targetForm) {
              targetForm = document.querySelector(`form[id*="${targetFormId}"]`);
            }
          }
          
          // If no form specified, find best form
          if (!targetForm) {
            const forms = Array.from(document.querySelectorAll('form'));
            if (forms.length === 1) {
              targetForm = forms[0];
            } else if (forms.length > 1) {
              // Choose form with most input fields
              let maxFields = 0;
              forms.forEach(form => {
                const fieldCount = form.querySelectorAll('input:not([type="hidden"]), textarea, select').length;
                if (fieldCount > maxFields) {
                  maxFields = fieldCount;
                  targetForm = form;
                }
              });
            }
          }
          
          if (!targetForm) {
            return {
              error: "No form found on page",
              detected_fields: [],
              form_metadata: {}
            };
          }
          
          const formMetadata = {
            form_id: targetForm.id || null,
            form_action: targetForm.action || null,
            form_method: targetForm.method || 'GET',
            form_classes: targetForm.className || null
          };
          
          // Detect form type from classes
          if (targetForm.className) {
            if (targetForm.className.includes('wpforms')) formMetadata.form_type = 'WPForms';
            else if (targetForm.className.includes('forminator')) formMetadata.form_type = 'Forminator';
            else if (targetForm.className.includes('wpcf7')) formMetadata.form_type = 'Contact Form 7';
            else if (targetForm.className.includes('gform')) formMetadata.form_type = 'Gravity Forms';
            else if (targetForm.className.includes('elementor')) formMetadata.form_type = 'Elementor';
            else formMetadata.form_type = 'Unknown';
          }
          
          const detectedFields = [];
          
          // Get all input, textarea, select elements
          const elements = targetForm.querySelectorAll('input, textarea, select');
          
          elements.forEach((el, idx) => {
            // Skip specific types
            if (el.type === 'hidden' || el.type === 'submit' || el.type === 'button' || el.type === 'image') {
              return;
            }
            
            const field = {
              index: idx,
              tag: el.tagName.toLowerCase(),
              type: el.type || 'text',
              id: el.id || null,
              name: el.name || null,
              placeholder: el.placeholder || null,
              required: el.required || el.getAttribute('aria-required') === 'true' || el.getAttribute('data-required') === 'true',
              value: el.value || '',
              visible: el.offsetParent !== null,
              
              // Additional attributes
              autocomplete: el.autocomplete || null,
              maxlength: el.maxLength > 0 ? el.maxLength : null,
              pattern: el.pattern || null,
              
              // Label detection
              label: null,
              label_text: null,
              
              // CSS classes for hints
              class_names: el.className || '',
              class_hints: []
            };
            
            // Try to find label
            if (el.id) {
              const label = document.querySelector(`label[for="${el.id}"]`);
              if (label) {
                field.label = el.id;
                field.label_text = label.innerText?.trim() || null;
              }
            }
            
            // If no label found by 'for' attribute, check parent/previous elements
            if (!field.label_text) {
              // Check if input is inside label
              const parentLabel = el.closest('label');
              if (parentLabel) {
                field.label_text = parentLabel.innerText?.trim() || null;
              }
              
              // Check for label in parent container
              if (!field.label_text) {
                const container = el.closest('.forminator-field, .wpforms-field, .gfield, .elementor-field, .form-group, .field-wrapper');
                if (container) {
                  const label = container.querySelector('label');
                  if (label) {
                    field.label_text = label.innerText?.trim() || null;
                  }
                }
              }
            }
            
            // Extract semantic hints from class names
            if (el.className) {
              const classes = el.className.toLowerCase().split(/\\s+/);
              
              // Name field hints
              if (classes.some(c => c.includes('first') && (c.includes('name') || c.includes('imi')))) {
                field.class_hints.push('first_name');
              }
              if (classes.some(c => c.includes('last') && (c.includes('name') || c.includes('nazwisk')))) {
                field.class_hints.push('last_name');
              }
              if (classes.some(c => c.includes('middle') && c.includes('name'))) {
                field.class_hints.push('middle_name');
              }
              if (classes.some(c => c.includes('full') && c.includes('name'))) {
                field.class_hints.push('full_name');
              }
              
              // Other field hints
              if (classes.some(c => c.includes('email') || c.includes('mail'))) {
                field.class_hints.push('email');
              }
              if (classes.some(c => c.includes('phone') || c.includes('tel'))) {
                field.class_hints.push('phone');
              }
              if (classes.some(c => c.includes('message') || c.includes('comment') || c.includes('wiadomosc'))) {
                field.class_hints.push('message');
              }
              if (classes.some(c => c.includes('subject') || c.includes('temat'))) {
                field.class_hints.push('subject');
              }
              if (classes.some(c => c.includes('consent') || c.includes('gdpr') || c.includes('privacy'))) {
                field.class_hints.push('consent');
              }
            }
            
            // Extract hints from name attribute
            if (el.name) {
              const nameLower = el.name.toLowerCase();
              if (nameLower.includes('first') && !field.class_hints.includes('first_name')) {
                field.class_hints.push('first_name');
              }
              if (nameLower.includes('last') && !field.class_hints.includes('last_name')) {
                field.class_hints.push('last_name');
              }
              if (nameLower.includes('email') && !field.class_hints.includes('email')) {
                field.class_hints.push('email');
              }
            }
            
            // Extract hints from label text
            if (field.label_text) {
              const labelLower = field.label_text.toLowerCase();
              if ((labelLower.includes('first') || labelLower.includes('imi')) && labelLower.includes('name')) {
                if (!field.class_hints.includes('first_name')) field.class_hints.push('first_name');
              }
              if ((labelLower.includes('last') || labelLower.includes('nazwisk')) && labelLower.includes('name')) {
                if (!field.class_hints.includes('last_name')) field.class_hints.push('last_name');
              }
              if (labelLower.includes('email') || labelLower.includes('e-mail')) {
                if (!field.class_hints.includes('email')) field.class_hints.push('email');
              }
            }
            
            detectedFields.push(field);
          });
          
          // Find submit button
          const submitBtn = targetForm.querySelector('button[type="submit"], input[type="submit"], button:not([type])');
          if (submitBtn) {
            formMetadata.submit_button = {
              id: submitBtn.id || null,
              text: submitBtn.innerText || submitBtn.value || 'Submit',
              type: submitBtn.type || 'submit'
            };
          }
          
          return {
            detected_fields: detectedFields,
            form_metadata: formMetadata,
            total_fields: detectedFields.length,
            required_fields_count: detectedFields.filter(f => f.required).length
          };
        }
        """,
        target_form_id
    )
    
    return result


async def analyze_field_relationships(fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analizuje relacje między polami (np. split name fields).
    """
    relationships = []
    
    # Detect split name fields
    first_name_fields = [f for f in fields if 'first_name' in f.get('class_hints', [])]
    last_name_fields = [f for f in fields if 'last_name' in f.get('class_hints', [])]
    
    if first_name_fields and last_name_fields:
        relationships.append({
            "type": "split_name",
            "fields": [first_name_fields[0]['id'], last_name_fields[0]['id']],
            "description": "Name field is split into First and Last name",
            "requires_splitting": True,
            "first_field": first_name_fields[0],
            "last_field": last_name_fields[0]
        })
    
    # Detect checkbox + label patterns (consent, terms)
    consent_fields = [f for f in fields if 'consent' in f.get('class_hints', []) and f['type'] == 'checkbox']
    if consent_fields:
        relationships.append({
            "type": "consent_checkbox",
            "field": consent_fields[0]['id'],
            "description": "GDPR/Privacy consent checkbox",
            "required": consent_fields[0].get('required', False)
        })
    
    return relationships


def create_llm_context(detection_result: Dict[str, Any], user_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Tworzy kontekst dla LLM na podstawie wykrytych pól i danych użytkownika.
    """
    fields = detection_result.get('detected_fields', [])
    
    # Simplify fields for LLM (only relevant data)
    simplified_fields = []
    for field in fields:
        simplified = {
            "index": field['index'],
            "id": field['id'],
            "type": field['type'],
            "label": field.get('label_text'),
            "required": field['required'],
            "hints": field.get('class_hints', []),
            "placeholder": field.get('placeholder')
        }
        simplified_fields.append(simplified)
    
    context = {
        "form_type": detection_result.get('form_metadata', {}).get('form_type', 'Unknown'),
        "total_fields": len(simplified_fields),
        "fields": simplified_fields,
        "user_data": user_data
    }
    
    return context
