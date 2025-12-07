"""
Field Mapping - Maps user-provided data to detected form fields.
No hardcoded selectors - uses heuristics based on field names/types.
"""
from typing import Dict, Any, List, Tuple
import re


# Field type keywords for matching
FIELD_KEYWORDS = {
    'email': ['email', 'mail', 'e-mail', 'poczta', 'adres'],
    'name': ['name', 'imię', 'imie', 'nazwisko', 'fullname', 'firstname', 'lastname'],
    'phone': ['phone', 'tel', 'telefon', 'mobile', 'komórka', 'komorka', 'numer'],
    'message': ['message', 'wiadomość', 'wiadomosc', 'treść', 'tresc', 'content', 'body', 'textarea', 'komentarz', 'comment'],
    'subject': ['subject', 'temat', 'title', 'tytuł', 'tytul'],
    'company': ['company', 'firma', 'organization', 'organizacja'],
    'address': ['address', 'adres', 'street', 'ulica', 'city', 'miasto'],
    'password': ['password', 'hasło', 'haslo', 'pass'],
}


def parse_instruction(instruction: str) -> Dict[str, str]:
    """
    Parse user instruction to extract key-value pairs.
    
    Formats supported:
    - "email=test@example.com, name=John"
    - "email = test@example.com, message = Hello"
    - "wypełnij: email=test@test.pl"
    
    Returns:
        Dict of field_name -> value
    """
    if not instruction:
        return {}
    
    result = {}
    
    # Pattern: key = value or key=value
    pattern = r'(\w+)\s*=\s*([^,]+?)(?:,|$)'
    matches = re.findall(pattern, instruction, re.UNICODE)
    
    for key, value in matches:
        result[key.strip().lower()] = value.strip()
    
    return result


def classify_field(field: Dict[str, Any]) -> str:
    """
    Classify a field into a known category based on its attributes.
    
    Args:
        field: Dict with name, id, type, tag, placeholder
    
    Returns:
        Field class (email, name, phone, message, etc.) or 'unknown'
    """
    # Collect all searchable text
    searchable = ' '.join([
        field.get('name', ''),
        field.get('id', ''),
        field.get('placeholder', ''),
        field.get('type', '')
    ]).lower()
    
    # Check explicit type first
    field_type = field.get('type', '').lower()
    if field_type == 'email':
        return 'email'
    if field_type == 'tel':
        return 'phone'
    if field_type == 'password':
        return 'password'
    
    # Check tag for textarea
    if field.get('tag', '').lower() == 'textarea':
        return 'message'
    
    # Match against keywords
    for field_class, keywords in FIELD_KEYWORDS.items():
        for keyword in keywords:
            if keyword in searchable:
                return field_class
    
    return 'unknown'


def map_user_data_to_fields(
    user_data: Dict[str, str],
    fields: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], str, str]]:
    """
    Map user-provided data to detected form fields.
    
    Args:
        user_data: Dict of field_class -> value (e.g., {'email': 'test@test.com'})
        fields: List of detected field dicts
    
    Returns:
        List of (field, field_class, value) tuples for matched fields
    """
    mappings = []
    used_fields = set()
    
    for field in fields:
        field_class = classify_field(field)
        
        if field_class == 'unknown':
            continue
        
        # Check if user provided data for this field class
        if field_class in user_data:
            value = user_data[field_class]
            field_key = field.get('selector') or field.get('id') or field.get('name')
            
            if field_key and field_key not in used_fields:
                mappings.append((field, field_class, value))
                used_fields.add(field_key)
    
    return mappings


def create_fill_plan(
    user_data: Dict[str, str],
    fields: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Create a fill plan from user data and detected fields.
    
    Returns:
        List of {selector, value, type, field_class} for filling
    """
    mappings = map_user_data_to_fields(user_data, fields)
    
    fill_plan = []
    for field, field_class, value in mappings:
        selector = field.get('selector')
        if not selector:
            # Build selector from id or name
            if field.get('id'):
                selector = f"#{field['id']}"
            elif field.get('name'):
                selector = f"[name=\"{field['name']}\"]"
            else:
                continue
        
        fill_plan.append({
            'selector': selector,
            'value': value,
            'type': field.get('type', 'text'),
            'field_class': field_class
        })
    
    return fill_plan
