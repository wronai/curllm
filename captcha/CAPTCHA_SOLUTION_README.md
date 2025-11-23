# 🔧 Rozwiązanie CAPTCHA dla curllm

## Problem

Allegro i inne serwisy używają zaawansowanych CAPTCHA typu:
- **Sliding Puzzle** - układanka przesuwna (jak na screenie)
- **Image Selection** - wybieranie obrazków
- **Audio CAPTCHA** - przepisywanie liczb z audio
- **reCAPTCHA v2/v3**
- **hCaptcha**

## Rozwiązanie

Stworzyłem kompleksowy solver CAPTCHA który:
1. **Automatycznie wykrywa** typ CAPTCHA
2. **Rozwiązuje lokalnie** używając Computer Vision
3. **Fallback do 2captcha** gdy lokalne rozwiązanie zawiedzie
4. **Integruje się z curllm**

## Instalacja

```bash
# Podstawowe wymagania
pip install opencv-python pillow numpy playwright

# Opcjonalne - dla audio CAPTCHA
pip install SpeechRecognition pydub

# Opcjonalne - dla lepszego OCR
pip install pytesseract easyocr

# Opcjonalne - dla 2captcha
pip install 2captcha-python

# Dla Ubuntu/Debian - zainstaluj tesseract
sudo apt-get install tesseract-ocr tesseract-ocr-pol
```

## Integracja z curllm

### 1. Zaktualizuj curllm_server.py

```python
# Dodaj import na początku pliku
from captcha_solver import CurllmCaptchaExtension

class CurllmExecutor:
    def __init__(self):
        # ... existing code ...
        
        # Dodaj CAPTCHA solver
        self.captcha_solver = CurllmCaptchaExtension(
            api_key_2captcha=os.getenv('CAPTCHA_API_KEY')  # Opcjonalne
        )
    
    async def execute_automation(self, page, instruction):
        # Przed wykonaniem instrukcji, sprawdź CAPTCHA
        captcha_solved = await self.captcha_solver.handle_page(page)
        
        if not captcha_solved:
            logger.warning("Could not solve CAPTCHA, trying alternative methods...")
            # Spróbuj metody audio lub 2captcha
            
        # Kontynuuj normalną automatyzację...
        return await self.original_execute(page, instruction)
```

### 2. Użycie standalone

```python
import asyncio
from playwright.async_api import async_playwright
from captcha_solver import CaptchaSolver, CaptchaConfig

async def solve_allegro_captcha():
    # Konfiguracja
    config = CaptchaConfig(
        use_2captcha=False,  # True jeśli masz konto
        api_key_2captcha="YOUR_API_KEY",
        debug_mode=True,
        screenshot_dir=Path("./captcha_debug")
    )
    
    solver = CaptchaSolver(config)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # False aby widzieć co się dzieje
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pl-PL',
            timezone_id='Europe/Warsaw'
        )
        
        # Usuń wykrywanie webdriver
        await context.add_init_script("""
            // Overwrite the navigator.webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Pass the Chrome Test
            window.chrome = {
                runtime: {}
            };
            
            // Pass the Permissions Test
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Pass the Plugins Length Test
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Pass the Languages Test
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pl-PL', 'pl', 'en-US', 'en']
            });
        """)
        
        page = await context.new_page()
        
        # Idź do Allegro
        await page.goto('https://allegro.pl', wait_until='networkidle')
        
        # Czekaj na CAPTCHA
        await asyncio.sleep(3)
        
        # Rozwiąż CAPTCHA
        success = await solver.solve(page)
        
        if success:
            print("✅ CAPTCHA rozwiązana!")
            # Kontynuuj automatyzację
            await page.wait_for_selector('input[type="search"]')
            await page.fill('input[type="search"]', 'laptop dell')
            await page.press('input[type="search"]', 'Enter')
            
            # Czekaj na wyniki
            await page.wait_for_selector('[data-role="offer"]')
            
            # Wyciągnij pierwszy produkt
            first_product = await page.query_selector('[data-role="offer"]')
            if first_product:
                title = await first_product.query_selector('h2')
                price = await first_product.query_selector('[aria-label*="cena"]')
                
                if title and price:
                    title_text = await title.inner_text()
                    price_text = await price.inner_text()
                    print(f"Produkt: {title_text}")
                    print(f"Cena: {price_text}")
        else:
            print("❌ Nie udało się rozwiązać CAPTCHA")
        
        await browser.close()

# Uruchom
asyncio.run(solve_allegro_captcha())
```

## Specyfika Sliding Puzzle (Allegro)

### Jak działa solver:

1. **Wykrywanie elementów**:
   - Znajduje canvas z puzzlem
   - Lokalizuje suwak do przesuwania
   - Identyfikuje brakujący element

2. **Analiza obrazu** (Computer Vision):
   ```python
   # Używa edge detection do znalezienia krawędzi
   edges = cv2.Canny(gray, 50, 150)
   
   # Template matching do znalezienia gdzie pasuje element
   result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
   ```

3. **Symulacja człowieka**:
   - Ruch myszą po krzywej Beziera
   - Losowe opóźnienia
   - Drobne "przestrzelenie" i korekta

### Alternatywne metody:

#### Metoda 1: Brute Force z małymi krokami
```python
async def brute_force_slide(page, slider):
    """Próbuj różnych pozycji aż zadziała"""
    start_x = 50  # Pozycja startowa
    max_x = 300  # Maksymalna pozycja
    step = 20     # Krok
    
    for x in range(start_x, max_x, step):
        await page.mouse.move(start_x, 100)
        await page.mouse.down()
        await page.mouse.move(x, 100, steps=10)
        await page.mouse.up()
        
        # Sprawdź czy rozwiązane
        error = await page.query_selector('.error')
        if not error:
            return True
        
        await asyncio.sleep(0.5)
    
    return False
```

#### Metoda 2: Użyj Audio CAPTCHA
```python
async def switch_to_audio(page):
    """Przełącz na audio jeśli dostępne"""
    audio_button = await page.query_selector('[aria-label*="audio"]')
    if audio_button:
        await audio_button.click()
        # Użyj speech recognition
        return await solve_audio_captcha(page)
    return False
```

#### Metoda 3: 2captcha API
```python
# Konfiguracja
CAPTCHA_API_KEY = "your_2captcha_api_key"

# W .env
echo "CAPTCHA_API_KEY=your_key_here" >> .env

# Użycie
solver = TwoCaptcha(CAPTCHA_API_KEY)
result = solver.coordinates(
    'captcha_image.png',
    lang='pl',
    hint_text='Przesuń puzzle'
)
```

## Debugging

### Zapisywanie screenów dla analizy:
```python
# W captcha_solver.py jest już to zaimplementowane
config = CaptchaConfig(
    debug_mode=True,
    screenshot_dir=Path("./captcha_screenshots")
)

# Screeny będą zapisane z timestampem
# puzzle_1234567890.png
```

### Analiza dlaczego nie działa:
```python
# Sprawdź czy jesteś w iframe
frames = page.frames
for frame in frames:
    print(f"Frame URL: {frame.url}")
    if 'captcha' in frame.url:
        # Pracuj w tym frame
        element = await frame.query_selector('canvas')
```

## Tips & Tricks

### 1. Stealth Mode
```python
# Użyj playwright-stealth
from playwright_stealth import stealth_async

await stealth_async(page)
```

### 2. Rotating User Agents
```python
import random

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
]

user_agent = random.choice(USER_AGENTS)
```

### 3. Proxy Rotation
```python
# Użyj proxy żeby uniknąć blokad IP
context = await browser.new_context(
    proxy={
        "server": "http://proxy.example.com:8080",
        "username": "user",
        "password": "pass"
    }
)
```

### 4. Cookies z prawdziwej sesji
```python
# Zapisz cookies z manualnej sesji
cookies = await context.cookies()
with open('cookies.json', 'w') as f:
    json.dump(cookies, f)

# Załaduj w automatyzacji
with open('cookies.json', 'r') as f:
    cookies = json.load(f)
await context.add_cookies(cookies)
```

## Testowanie

### Test lokalny:
```bash
# Uruchom test
python captcha_solver.py

# Z debugowaniem
CAPTCHA_DEBUG=true python captcha_solver.py

# Z 2captcha
CAPTCHA_API_KEY=your_key python captcha_solver.py
```

### Test z curllm:
```bash
# Dodaj do curllm
curllm --captcha "https://allegro.pl" \
  -d "znajdź najtańszy laptop Dell"
```

## Znane problemy i rozwiązania

### Problem: "Spróbuj ponownie"
**Rozwiązanie**: Puzzle nie zostało przesunięte dokładnie
- Zwiększ precyzję wykrywania
- Użyj mniejszych kroków
- Spróbuj audio CAPTCHA

### Problem: Wykrycie bota mimo rozwiązania
**Rozwiązanie**: Browser fingerprint
- Użyj undetected-chromedriver
- Rotuj IP przez proxy
- Dodaj losowe opóźnienia

### Problem: Canvas jest pusty
**Rozwiązanie**: JavaScript nie załadował się
- Zwiększ timeout
- Sprawdź czy nie jesteś w iframe
- Wyłącz headless mode do debugowania

## Alternatywy komercyjne

Jeśli lokalne rozwiązania nie działają:

1. **2captcha.com** - $2.99 per 1000 CAPTCHA
2. **Anti-captcha.com** - $2 per 1000
3. **DeathByCaptcha** - $1.39 per 1000
4. **CapMonster Cloud** - $0.6 per 1000

## Podsumowanie

✅ **Co mamy**:
- Kompleksowy solver dla sliding puzzle
- Wsparcie dla audio CAPTCHA
- Integracja z 2captcha
- Human-like mouse movements

⚠️ **Ograniczenia**:
- Sliding puzzle wymaga dobrego CV
- Audio może być nieczytelne
- Niektóre CAPTCHA wymagają płatnego API

🎯 **Rekomendacje**:
1. Zacznij od lokalnego solvera
2. Dodaj 2captcha jako fallback
3. Używaj proxy i rotation
4. Zapisuj screeny do analizy

---

**Pytania?** Daj znać co dokładnie nie działa, prześlę bardziej specyficzne rozwiązanie!