#!/usr/bin/env python3
"""
URL Resolver + Form Fill - Kompleksowy przykład

Scenariusz: User podaje TYLKO nazwę domeny i pełne polecenie.
System sam:
1. Wchodzi na stronę
2. Znajduje formularz kontaktowy
3. Wypełnia go danymi z polecenia
4. Wysyła formularz

Przykłady zapytań:

curllm "Wejdź na prototypowanie.pl i wyślij wiadomość przez formularz 
        z zapytaniem o dostępność usługi prototypowania 3d 
        z adresem email info@softreck.com i nazwiskiem Sapletta"

curllm "Otwórz morele.net, znajdź kontakt i napisz wiadomość 
        z pytaniem o status zamówienia #12345, 
        email: jan.kowalski@gmail.com, tel: 123456789"

curllm "Wejdź na x-kom.pl i wypełnij formularz kontaktowy 
        z reklamacją produktu - laptop nie działa, 
        dane: Anna Nowak, anna@example.com"
"""

import asyncio
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from curllm_core.url_resolver import UrlResolver, TaskGoal
from browser_helper import create_browser, close_browser

# Kompleksowe przykłady - pełne polecenia
EXAMPLES = [
    {
        "command": """Wejdź na prototypowanie.pl i wyślij wiadomość przez formularz 
                      z zapytaniem o dostępność usługi prototypowania 3d 
                      z adresem email info@softreck.com i nazwiskiem Sapletta""",
        "expected_flow": [
            "1. Nawiguj do https://prototypowanie.pl",
            "2. Znajdź formularz kontaktowy",
            "3. Wypełnij: email=info@softreck.com, nazwisko=Sapletta",
            "4. Wiadomość: zapytanie o prototypowanie 3d",
            "5. Wyślij formularz"
        ]
    },
    {
        "command": """Otwórz stronę morele.net i znajdź kontakt, 
                      napisz wiadomość z pytaniem o status zamówienia numer 12345,
                      podaj email jan.kowalski@gmail.com i telefon 123456789""",
        "expected_flow": [
            "1. Nawiguj do https://morele.net",
            "2. Znajdź stronę kontaktową",
            "3. Wypełnij: email=jan.kowalski@gmail.com, tel=123456789",
            "4. Wiadomość: status zamówienia #12345",
            "5. Wyślij formularz"
        ]
    },
    {
        "command": """Wejdź na x-kom.pl i wypełnij formularz kontaktowy 
                      z reklamacją - laptop Dell nie uruchamia się po 2 tygodniach,
                      dane kontaktowe: Anna Nowak, anna.nowak@example.com, 
                      numer zamówienia XK-98765""",
        "expected_flow": [
            "1. Nawiguj do https://x-kom.pl",
            "2. Znajdź formularz kontaktowy/reklamacji",
            "3. Wypełnij: imię=Anna Nowak, email=anna.nowak@example.com",
            "4. Temat: reklamacja, nr zamówienia XK-98765",
            "5. Opis: laptop Dell nie uruchamia się",
            "6. Wyślij formularz"
        ]
    },
    {
        "command": """Przejdź do sklepu euro.com.pl i skontaktuj się 
                      w sprawie gwarancji na telewizor Samsung,
                      moje dane: Piotr Wiśniewski, piotr.w@mail.pl, 
                      numer paragonu: 2024/11/12345""",
        "expected_flow": [
            "1. Nawiguj do https://euro.com.pl",
            "2. Znajdź kontakt/gwarancja",
            "3. Wypełnij dane klienta",
            "4. Temat: gwarancja telewizor Samsung",
            "5. Wyślij"
        ]
    },
]
def parse_command(command: str) -> dict:
    """
    Parsuje polecenie użytkownika i wyciąga:
    - domenę
    - cel (kontakt, formularz, etc.)
    - dane do wypełnienia (email, nazwisko, telefon, etc.)
    - treść wiadomości
    """
    command_lower = command.lower()
    
    # Wyciągnij domenę
    domain_patterns = [
        r'(?:wejdź na|otwórz|przejdź do|idź na|odwiedź)\s+(?:stronę\s+)?([a-zA-Z0-9.-]+\.[a-z]{2,})',
        r'(?:na|do)\s+(?:sklepu\s+)?([a-zA-Z0-9.-]+\.[a-z]{2,})',
        r'([a-zA-Z0-9.-]+\.(?:pl|com|net|eu|org))',
    ]
    
    domain = None
    for pattern in domain_patterns:
        match = re.search(pattern, command_lower)
        if match:
            domain = match.group(1)
            break
    
    # Wyciągnij email
    email_match = re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', command)
    email = email_match.group(0) if email_match else None
    
    # Wyciągnij telefon
    phone_match = re.search(r'\b(\d{9}|\d{3}[-\s]?\d{3}[-\s]?\d{3})\b', command)
    phone = phone_match.group(0) if phone_match else None
    
    # Wyciągnij nazwisko/imię
    name_patterns = [
        r'nazwisk(?:o|iem)\s+(\w+)',
        r'imi(?:ę|eniem)\s+(\w+(?:\s+\w+)?)',
        r'dane[:\s]+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?)',
    ]
    
    name = None
    for pattern in name_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            name = match.group(1)
            break
    
    # Wyciągnij numer zamówienia
    order_patterns = [
        r'(?:zamówieni[ae]|nr|numer)\s*[:#]?\s*([A-Z0-9/-]+)',
        r'(?:paragon|faktur[ay])\s*[:#]?\s*([A-Z0-9/-]+)',
    ]
    
    order_number = None
    for pattern in order_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            order_number = match.group(1)
            break
    
    # Określ cel
    if any(x in command_lower for x in ['kontakt', 'formularz', 'napisz', 'wyślij', 'wiadomość']):
        goal = TaskGoal.FIND_CONTACT_FORM
    elif any(x in command_lower for x in ['reklamacja', 'zwrot', 'gwarancja']):
        goal = TaskGoal.FIND_RETURNS  # lub kontakt w sprawie reklamacji
    else:
        goal = TaskGoal.FIND_CONTACT_FORM
    
    # Wyciągnij treść wiadomości (to co jest "z zapytaniem o", "w sprawie", etc.)
    message_patterns = [
        r'(?:z\s+)?(?:zapytaniem|pytaniem)\s+o\s+(.+?)(?:,|z\s+adresem|z\s+email|$)',
        r'w\s+sprawie\s+(.+?)(?:,|dane|moje|$)',
        r'(?:wiadomość|napisz)\s+(?:z\s+)?(.+?)(?:,|dane|email|$)',
    ]
    
    message = None
    for pattern in message_patterns:
        match = re.search(pattern, command_lower)
        if match:
            message = match.group(1).strip()
            break
    
    return {
        'domain': domain,
        'url': f"https://{domain}" if domain else None,
        'goal': goal,
        'email': email,
        'phone': phone,
        'name': name,
        'order_number': order_number,
        'message': message,
        'original_command': command
    }
async def execute_command(command: str, dry_run: bool = True):
    """
    Wykonuje kompleksowe polecenie:
    1. Parsuje polecenie
    2. Używa URL Resolver do znalezienia odpowiedniej strony
    3. (Opcjonalnie) Wypełnia formularz
    """
    print(f"\n{'='*70}")
    print(f"📝 POLECENIE:")
    print(f"   {command[:100]}...")
    print(f"{'='*70}")
    
    # Parsuj polecenie
    parsed = parse_command(command)
    
    print(f"\n🔍 ANALIZA POLECENIA:")
    print(f"   Domena: {parsed['domain']}")
    print(f"   URL: {parsed['url']}")
    print(f"   Cel: {parsed['goal'].value}")
    print(f"   Email: {parsed['email']}")
    print(f"   Telefon: {parsed['phone']}")
    print(f"   Nazwisko/Imię: {parsed['name']}")
    print(f"   Nr zamówienia: {parsed['order_number']}")
    print(f"   Treść: {parsed['message']}")
    
    if not parsed['url']:
        print(f"\n❌ Nie udało się wyciągnąć domeny z polecenia")
        return False
    
    if dry_run:
        print(f"\n🔄 DRY RUN - symulacja bez wykonania")
        print(f"   Kroki które zostałyby wykonane:")
        print(f"   1. Nawiguj do {parsed['url']}")
        print(f"   2. Znajdź {parsed['goal'].value}")
        print(f"   3. Wypełnij formularz danymi:")
        if parsed['email']:
            print(f"      - Email: {parsed['email']}")
        if parsed['name']:
            print(f"      - Nazwisko: {parsed['name']}")
        if parsed['phone']:
            print(f"      - Telefon: {parsed['phone']}")
        if parsed['message']:
            print(f"      - Wiadomość: {parsed['message']}")
        print(f"   4. Wyślij formularz")
        return True
    
    # Rzeczywiste wykonanie
    playwright = None
    browser = None
    try:
        browser, context = await setup_browser(stealth_mode=True, headless=False)  # headless=False żeby widzieć
        
        
        
        
        # Krok 1: Użyj URL Resolver
        print(f"\n🔍 Krok 1: Szukam formularza kontaktowego...")
        resolver = UrlResolver(page=page, llm=None)
        result = await resolver.resolve_for_goal(parsed['url'], parsed['goal'])
        
        print(f"   Sukces: {'✅' if result.success else '❌'}")
        print(f"   Znaleziony URL: {result.resolved_url}")
        
        if result.success:
            # Krok 2: Analiza formularza
            print(f"\n📋 Krok 2: Analiza formularza...")
            form_info = await page.evaluate("""
                () => {
                    const forms = document.querySelectorAll('form');
                    const inputs = document.querySelectorAll('input, textarea, select');
                    
                    const fields = [];
                    inputs.forEach(inp => {
                        const name = inp.name || inp.id || inp.placeholder || '';
                        const type = inp.type || inp.tagName.toLowerCase();
                        if (name && type !== 'hidden' && type !== 'submit') {
                            fields.push({name, type, placeholder: inp.placeholder || ''});
                        }
                    });
                    
                    return {
                        formCount: forms.length,
                        fields: fields.slice(0, 10)
                    };
                }
            """)
            
            print(f"   Znaleziono formularzy: {form_info['formCount']}")
            print(f"   Pola formularza:")
            for field in form_info['fields']:
                print(f"      - {field['name']} ({field['type']})")
            
            # Tu można dodać logikę wypełniania formularza
            # używając curllm_core.executor lub streamware
            
        await close_browser(playwright, browser, context, page)
        
        
        
        return result.success
        
    except Exception as e:
        print(f"   ❌ Błąd: {e}")
        await close_browser(playwright, browser)
        return False
async def main():
    print("="*70)
    print("🚀 CURLLM - Kompleksowe polecenia")
    print("   Podaj domenę + pełne polecenie w naturalnym języku")
    print("="*70)
    
    # Tryb demonstracyjny - pokaż parsowanie
    print("\n📋 PRZYKŁADY POLECEŃ:\n")
    
    for i, example in enumerate(EXAMPLES, 1):
        print(f"\n{'─'*70}")
        print(f"Przykład {i}:")
        print(f"{'─'*70}")
        
        # Pokaż polecenie
        cmd = ' '.join(example['command'].split())
        print(f"\n💬 curllm \"{cmd}\"\n")
        
        # Parsuj i pokaż analizę
        parsed = parse_command(example['command'])
        
        print(f"📊 Analiza:")
        print(f"   🌐 Domena: {parsed['domain']}")
        print(f"   🎯 Cel: {parsed['goal'].value}")
        if parsed['email']:
            print(f"   📧 Email: {parsed['email']}")
        if parsed['name']:
            print(f"   👤 Nazwisko: {parsed['name']}")
        if parsed['phone']:
            print(f"   📞 Telefon: {parsed['phone']}")
        if parsed['order_number']:
            print(f"   📦 Nr zamówienia: {parsed['order_number']}")
        if parsed['message']:
            print(f"   💬 Treść: {parsed['message']}")
        
        print(f"\n🔄 Oczekiwany flow:")
        for step in example['expected_flow']:
            print(f"   {step}")
    
    # Interaktywny tryb
    print(f"\n{'='*70}")
    print("Chcesz przetestować własne polecenie?")
    choice = input("Wpisz polecenie lub [Q]uit: ").strip()
    
    if choice.lower() != 'q' and choice:
        await execute_command(choice, dry_run=True)
if __name__ == "__main__":
    asyncio.run(main())
