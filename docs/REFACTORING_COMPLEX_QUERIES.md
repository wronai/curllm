# Refaktoryzacja curllm - Obsługa Złożonych Zapytań

## Analiza obecnego stanu

### Problem
Obecna architektura nie jest zoptymalizowana pod kompleksowe polecenia typu:
```
curllm "Wejdź na prototypowanie.pl i wyślij wiadomość przez formularz 
        z zapytaniem o dostępność usługi prototypowania 3d 
        z adresem email info@softreck.com i nazwiskiem Sapletta"
```

### Obecny flow (niewystarczający):
```
User → instruction → task_runner → (keywords) → form_fill/extract → result
```

### Problemy:
1. **Brak parsowania strukturalnego** - polecenie traktowane jako string
2. **Wykrywanie zadania na podstawie keywords** - błędne klasyfikacje
3. **Brak rozdzielenia kroków** - wszystko w jednym execute_workflow
4. **URL Resolver nie zintegrowany** - osobny komponent
5. **Brak kontekstu strony przed decyzją** - reagowanie na keywords

---

## Proponowana architektura

### Nowy flow:
```
User → CommandParser → TaskPlanner → Orchestrator → Executors → Result
          ↓                ↓             ↓
      parsed_cmd      task_plan     step-by-step
```

### Nowe komponenty:

#### 1. CommandParser (`curllm_core/command_parser.py`)
Parsuje naturalne polecenie na strukturę:

```python
@dataclass
class ParsedCommand:
    # Cel główny
    primary_goal: TaskGoal
    secondary_goals: List[TaskGoal]
    
    # Nawigacja
    target_domain: str
    target_url: Optional[str]
    
    # Dane do wypełnienia
    form_data: Dict[str, str]  # email, name, phone, etc.
    message_content: str
    
    # Dodatkowe informacje
    order_number: Optional[str]
    product_info: Optional[str]
    
    # Oryginalne polecenie
    original_instruction: str
    confidence: float
```

#### 2. TaskPlanner (`curllm_core/task_planner.py`)
Tworzy plan wykonania:

```python
@dataclass
class TaskStep:
    step_type: str  # navigate, resolve, analyze, fill, extract, submit
    params: Dict[str, Any]
    dependencies: List[int]  # indeksy poprzednich kroków
    fallback: Optional['TaskStep']

@dataclass
class TaskPlan:
    steps: List[TaskStep]
    expected_outcome: str
    timeout_seconds: int
    retry_policy: RetryPolicy

class TaskPlanner:
    def plan(self, parsed: ParsedCommand, page_context: PageContext) -> TaskPlan:
        """
        Tworzy plan na podstawie:
        1. Sparsowanego polecenia
        2. Kontekstu aktualnej strony
        3. Historii poprzednich akcji
        """
```

Przykładowy plan dla polecenia kontaktowego:
```python
TaskPlan(steps=[
    TaskStep(type="navigate", params={"url": "https://prototypowanie.pl"}),
    TaskStep(type="resolve", params={"goal": "find_contact_form"}),
    TaskStep(type="analyze", params={"expected": "form_fields"}),
    TaskStep(type="fill", params={"data": {"email": "...", "name": "..."}}),
    TaskStep(type="fill_message", params={"content": "..."}),
    TaskStep(type="submit", params={"confirm": True}),
    TaskStep(type="verify", params={"expected": "success_message"}),
])
```

#### 3. Orchestrator (`curllm_core/orchestrator.py`)
Wykonuje plan krok po kroku:

```python
class Orchestrator:
    def __init__(self, executor, url_resolver, planner):
        self.executor = executor
        self.url_resolver = url_resolver
        self.planner = planner
    
    async def execute(
        self, 
        command: str,
        config: OrchestratorConfig
    ) -> OrchestratorResult:
        # 1. Parse command
        parsed = self.command_parser.parse(command)
        
        # 2. Initial navigation
        await self.navigate(parsed.target_url)
        
        # 3. Analyze page
        page_context = await self.analyze_page()
        
        # 4. Create plan based on page + command
        plan = self.planner.plan(parsed, page_context)
        
        # 5. Execute plan step by step
        for step in plan.steps:
            result = await self.execute_step(step)
            if not result.success:
                # Try fallback or retry
                ...
        
        # 6. Verify outcome
        return self.verify_result(plan.expected_outcome)
```

---

## Zmiany w istniejących komponentach

### 1. CurllmExecutor - rozszerzenie

```python
class CurllmExecutor:
    async def execute_workflow(
        self,
        instruction: str,
        url: Optional[str] = None,
        # Nowe parametry:
        parsed_command: Optional[ParsedCommand] = None,
        task_plan: Optional[TaskPlan] = None,
        orchestrator_mode: bool = False,
        ...
    ):
        # Jeśli orchestrator_mode=True, użyj nowego flow
        if orchestrator_mode or parsed_command:
            return await self._execute_orchestrated(
                instruction, url, parsed_command, task_plan
            )
        
        # Zachowaj kompatybilność wsteczną
        return await self._execute_legacy(instruction, url, ...)
```

### 2. IntentDetector - ulepszenie

```python
class IntentDetector:
    async def detect_intent(
        self,
        instruction: str,
        page_context: Optional[Dict] = None,
        parsed_command: Optional[ParsedCommand] = None,  # Nowe
    ) -> IntentResult:
        # Jeśli mamy parsed_command, użyj go jako źródła prawdy
        if parsed_command:
            return self._intent_from_parsed(parsed_command, page_context)
        
        # Fallback do starej logiki
        ...
```

### 3. UrlResolver - integracja

```python
class UrlResolver:
    # Dodaj metodę do użycia w orchestratorze
    async def resolve_from_parsed(
        self,
        parsed: ParsedCommand
    ) -> ResolvedUrl:
        """
        Użyj sparsowanej komendy do lepszego rozwiązywania URL.
        Zna dokładny cel i kontekst.
        """
```

---

## Nowe CLI

### Rozszerzone polecenie curllm:

```bash
# Tryb prosty (legacy)
curllm -u "https://example.com" -i "Extract products"

# Tryb kompleksowy (orchestrator)
curllm "Wejdź na example.com i wyślij formularz..."

# Z parsowaniem debug
curllm --parse-only "Wejdź na example.com i wyślij formularz..."

# Z planem debug  
curllm --plan-only "Wejdź na example.com i wyślij formularz..."
```

### Nowy entry point:

```python
# curllm (bin/curllm)
def main():
    args = parse_args()
    
    if args.instruction and not args.url:
        # Kompleksowy tryb - wykryj URL z instrukcji
        parser = CommandParser()
        parsed = parser.parse(args.instruction)
        
        orchestrator = Orchestrator(...)
        result = orchestrator.execute(parsed)
    else:
        # Legacy tryb
        executor = CurllmExecutor()
        result = executor.execute_workflow(...)
```

---

## Struktura katalogów po refaktoryzacji

```
curllm_core/
├── __init__.py
├── config.py
├── executor.py              # CurllmExecutor (zachowany)
├── task_runner.py           # (zachowany, używany przez executor)
│
├── # NOWE KOMPONENTY
├── command_parser.py        # Parsowanie poleceń NL
├── task_planner.py          # Planowanie kroków
├── orchestrator.py          # Główny orkiestrator
├── step_executor.py         # Wykonywanie pojedynczych kroków
│
├── # ISTNIEJĄCE (rozszerzone)
├── intent_detector.py       # Wykrywanie intencji
├── url_resolver.py          # Rozwiązywanie URL
│
├── orchestrators/           # Specjalizowane orkiestratory
│   ├── master.py           # (istniejący)
│   ├── form.py             # Dla formularzy
│   ├── extraction.py       # Dla ekstrakcji
│   └── shopping.py         # Dla zakupów
│
├── tools/                   # Narzędzia atomowe
│   ├── navigation/
│   ├── forms/
│   └── extraction/
```

---

## Plan wdrożenia

### Faza 1: CommandParser (1-2 dni)
- [ ] Implementacja `command_parser.py`
- [ ] Testy parsowania różnych formatów poleceń
- [ ] Integracja z CLI

### Faza 2: TaskPlanner (2-3 dni)
- [ ] Implementacja `task_planner.py`
- [ ] Szablony planów dla typowych zadań
- [ ] Logika fallbacków

### Faza 3: Orchestrator (3-4 dni)
- [ ] Implementacja głównego orchestratora
- [ ] Integracja z executor/url_resolver
- [ ] Step-by-step execution z logowaniem

### Faza 4: Integracja (2-3 dni)
- [ ] Aktualizacja CLI
- [ ] Testy end-to-end
- [ ] Dokumentacja

### Faza 5: Migracja (1-2 dni)
- [ ] Oznaczenie starego flow jako deprecated
- [ ] Migracja przykładów
- [ ] Testy regresji

---

## Zachowanie kompatybilności

```python
# Stary sposób - nadal działa
executor = CurllmExecutor()
result = await executor.execute_workflow(
    instruction="Extract product prices",
    url="https://example.com"
)

# Nowy sposób - orchestrator
orchestrator = Orchestrator()
result = await orchestrator.execute(
    "Wejdź na example.com i pobierz ceny produktów"
)

# CLI - automatyczne wykrywanie trybu
curllm -u "https://example.com" -i "Extract prices"  # Legacy
curllm "Wejdź na example.com i pobierz ceny"          # Orchestrator
```

---

## Przykłady użycia nowej architektury

### 1. Wysłanie formularza kontaktowego

```python
# Input
command = """
Wejdź na prototypowanie.pl i wyślij wiadomość przez formularz 
z zapytaniem o dostępność usługi prototypowania 3d 
z adresem email info@softreck.com i nazwiskiem Sapletta
"""

# Parsed
ParsedCommand(
    primary_goal=TaskGoal.FIND_CONTACT_FORM,
    target_domain="prototypowanie.pl",
    form_data={
        "email": "info@softreck.com",
        "name": "Sapletta"
    },
    message_content="zapytanie o dostępność usługi prototypowania 3d"
)

# Plan
TaskPlan(steps=[
    Step("navigate", url="https://prototypowanie.pl"),
    Step("resolve", goal=FIND_CONTACT_FORM),
    Step("fill", field="email", value="info@softreck.com"),
    Step("fill", field="name", value="Sapletta"),
    Step("fill", field="message", value="..."),
    Step("submit"),
    Step("verify", expected="thank_you")
])

# Execution log (logs/*.md)
```

### 2. Zakupy z koszykiem

```python
command = """
Otwórz morele.net, znajdź pamięć RAM DDR5 32GB Kingston, 
dodaj najtańszą do koszyka i przejdź do kasy
"""

# Parsed
ParsedCommand(
    primary_goal=TaskGoal.FIND_CART,
    secondary_goals=[TaskGoal.EXTRACT_PRODUCTS],
    target_domain="morele.net",
    product_info="pamięć RAM DDR5 32GB Kingston",
    action_sequence=["search", "select_cheapest", "add_to_cart", "checkout"]
)

# Plan
TaskPlan(steps=[
    Step("navigate", url="https://morele.net"),
    Step("search", query="RAM DDR5 32GB Kingston"),
    Step("extract", type="products", filter="price_asc"),
    Step("click", selector="[add-to-cart]:first"),
    Step("resolve", goal=FIND_CART),
    Step("resolve", goal=FIND_CHECKOUT)
])
```

---

## Podsumowanie

Refaktoryzacja wprowadza:
1. **Strukturalne parsowanie poleceń** - zamiast keywords
2. **Planowanie przed wykonaniem** - świadome kroki
3. **Orkiestracja z kontekstem** - analiza strony przed akcją
4. **Zachowanie kompatybilności** - stary kod nadal działa
5. **Lepsza debugowalność** - logi każdego kroku
