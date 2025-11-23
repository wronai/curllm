#!/usr/bin/env python3
"""
Prosty przykład rozwiązywania Allegro CAPTCHA
Testowane z sliding puzzle CAPTCHA
"""

import asyncio
import time
from pathlib import Path
from playwright.async_api import async_playwright
import cv2
import numpy as np


class AllegroSlidingPuzzleSolver:
    """Specjalny solver dla Allegro sliding puzzle"""
    
    async def solve_allegro_puzzle(self, page):
        """
        Rozwiązuje sliding puzzle na Allegro
        """
        print("🔍 Szukam CAPTCHA na stronie...")
        
        # Sprawdź czy jesteśmy w iframe z CAPTCHA
        frames = page.frames
        captcha_frame = None
        
        for frame in frames:
            if 'captcha' in frame.url.lower() or 'geo.captcha' in frame.url:
                captcha_frame = frame
                print(f"✅ Znaleziono iframe CAPTCHA: {frame.url[:50]}...")
                break
        
        if not captcha_frame:
            print("❌ Nie znaleziono iframe z CAPTCHA")
            return False
        
        # Pracujemy w iframe
        try:
            # Najpierw spróbuj kliknąć POTWIERDZAM jeśli jest
            try:
                confirm_button = await captcha_frame.wait_for_selector(
                    'button:has-text("POTWIERDZAM")',
                    timeout=2000
                )
                if confirm_button:
                    print("🖱️ Klikam przycisk POTWIERDZAM...")
                    await confirm_button.click()
                    await asyncio.sleep(2)
            except:
                pass
            
            # Szukaj elementów sliding puzzle
            print("🧩 Szukam elementów układanki...")
            
            # Znajdź canvas z puzzlem
            canvas = await captcha_frame.wait_for_selector('canvas', timeout=5000)
            if not canvas:
                print("❌ Nie znaleziono canvas z puzzlem")
                return False
            
            # Zrób screenshot do analizy
            screenshot_path = Path(f"puzzle_{int(time.time())}.png")
            await canvas.screenshot(path=str(screenshot_path))
            print(f"📸 Screenshot zapisany: {screenshot_path}")
            
            # Znajdź suwak
            slider = None
            slider_selectors = [
                '[draggable="true"]',
                'div[class*="slider"]',
                'div[class*="handle"]',
                'div[class*="drag"]'
            ]
            
            for selector in slider_selectors:
                try:
                    slider = await captcha_frame.wait_for_selector(selector, timeout=2000)
                    if slider:
                        print(f"✅ Znaleziono suwak: {selector}")
                        break
                except:
                    continue
            
            if not slider:
                print("❌ Nie znaleziono suwaka")
                return False
            
            # Analizuj puzzle (prostsza metoda)
            distance = self.analyze_puzzle_simple(screenshot_path)
            
            # Wykonaj przesunięcie
            print(f"🎯 Przesuwam suwak o {distance}px...")
            success = await self.drag_slider(captcha_frame, slider, distance)
            
            if success:
                print("✅ Puzzle rozwiązane!")
                await asyncio.sleep(2)
                return True
            else:
                print("❌ Nie udało się rozwiązać puzzle")
                
                # Spróbuj metody brute force
                print("🔄 Próbuję metody brute force...")
                return await self.brute_force_solve(captcha_frame, slider)
                
        except Exception as e:
            print(f"❌ Błąd podczas rozwiązywania: {e}")
            return False
    
    def analyze_puzzle_simple(self, image_path):
        """
        Prosta analiza puzzle - szacuje odległość do przesunięcia
        """
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return 200  # Domyślna wartość
            
            # Konwertuj do grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Wykryj krawędzie
            edges = cv2.Canny(gray, 50, 150)
            
            # Znajdź kontury
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) > 1:
                # Znajdź dwa największe kontury (tło i element)
                contours = sorted(contours, key=cv2.contourArea, reverse=True)[:2]
                
                # Pobierz pozycje
                x1, _, w1, _ = cv2.boundingRect(contours[0])
                x2, _, w2, _ = cv2.boundingRect(contours[1])
                
                # Szacuj odległość
                distance = abs(x2 - x1)
                
                # Allegro zazwyczaj wymaga przesunięcia 200-300px
                if distance < 50 or distance > 400:
                    distance = 250  # Wartość domyślna dla Allegro
                    
                return distance
            
        except Exception as e:
            print(f"⚠️ Błąd analizy obrazu: {e}")
        
        # Wartość domyślna dla Allegro
        return 250
    
    async def drag_slider(self, frame, slider, distance):
        """
        Przeciąga suwak o określoną odległość
        """
        try:
            # Pobierz pozycję suwaka
            box = await slider.bounding_box()
            if not box:
                return False
            
            start_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] / 2
            end_x = start_x + distance
            end_y = start_y
            
            # Przesuń mysz do początku
            await frame.mouse.move(start_x, start_y)
            await asyncio.sleep(0.1)
            
            # Wciśnij przycisk myszy
            await frame.mouse.down()
            await asyncio.sleep(0.1)
            
            # Przesuń z symulacją ludzkiego ruchu
            steps = 20
            for i in range(steps):
                progress = (i + 1) / steps
                # Dodaj losowość do ruchu
                current_x = start_x + (distance * progress) + np.random.randint(-2, 2)
                current_y = start_y + np.random.randint(-1, 1)
                
                await frame.mouse.move(current_x, current_y)
                await asyncio.sleep(0.02 + np.random.random() * 0.03)
            
            # Drobna korekta na końcu
            await frame.mouse.move(end_x, end_y)
            await asyncio.sleep(0.1)
            
            # Puść przycisk myszy
            await frame.mouse.up()
            await asyncio.sleep(1)
            
            # Sprawdź czy się udało
            try:
                error = await frame.wait_for_selector(
                    'text="Spróbuj ponownie"',
                    timeout=1000
                )
                if error:
                    return False
            except:
                # Brak błędu = sukces
                return True
                
            return True
            
        except Exception as e:
            print(f"❌ Błąd podczas przesuwania: {e}")
            return False
    
    async def brute_force_solve(self, frame, slider):
        """
        Metoda brute force - próbuje różnych odległości
        """
        print("🔨 Rozpoczynam brute force...")
        
        distances = [150, 200, 250, 280, 300, 320, 350]
        
        for distance in distances:
            print(f"  Próbuję dystans: {distance}px")
            
            # Reset pozycji (odśwież stronę w iframe)
            try:
                await frame.evaluate('window.location.reload()')
                await asyncio.sleep(3)
                
                # Znajdź suwak ponownie
                slider = await frame.wait_for_selector('[draggable="true"]', timeout=3000)
                if not slider:
                    continue
                    
            except:
                pass
            
            # Spróbuj przesunąć
            success = await self.drag_slider(frame, slider, distance)
            
            if success:
                print(f"✅ Sukces z dystansem {distance}px!")
                return True
                
            await asyncio.sleep(1)
        
        return False


async def main():
    """
    Główna funkcja - przykład użycia
    """
    print("🚀 Start Allegro CAPTCHA Solver")
    print("=" * 50)
    
    solver = AllegroSlidingPuzzleSolver()
    
    async with async_playwright() as p:
        # Uruchom przeglądarkę
        browser = await p.chromium.launch(
            headless=False,  # Ustaw True dla trybu headless
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        
        # Stwórz kontekst ze stealth settings
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pl-PL',
            timezone_id='Europe/Warsaw'
        )
        
        # Dodaj skrypty anti-detection
        await context.add_init_script("""
            // Usuń webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Chrome runtime
            window.chrome = { runtime: {} };
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pl-PL', 'pl', 'en-US', 'en']
            });
            
            // Console.debug trick
            const originalDebug = console.debug;
            console.debug = function() {
                if (arguments[0] && arguments[0].includes('HeadlessChrome')) {
                    return;
                }
                return originalDebug.apply(console, arguments);
            };
        """)
        
        # Nowa strona
        page = await context.new_page()
        
        print("📍 Otwieram Allegro...")
        await page.goto('https://allegro.pl', wait_until='domcontentloaded')
        
        # Czekaj na załadowanie
        await asyncio.sleep(3)
        
        # Sprawdź czy jest CAPTCHA
        captcha_present = False
        try:
            # Szukaj typowych elementów CAPTCHA
            captcha_text = await page.wait_for_selector(
                'text="Potwierdź, że jesteś człowiekiem"',
                timeout=5000
            )
            if captcha_text:
                captcha_present = True
                print("⚠️ Wykryto CAPTCHA!")
        except:
            print("✅ Brak CAPTCHA - możesz kontynuować")
        
        if captcha_present:
            # Rozwiąż CAPTCHA
            solved = await solver.solve_allegro_puzzle(page)
            
            if solved:
                print("🎉 CAPTCHA rozwiązana pomyślnie!")
                print("\n📦 Kontynuuję automatyzację...")
                
                # Poczekaj na załadowanie głównej strony
                await page.wait_for_selector('input[type="search"]', timeout=10000)
                
                # Przykład: wyszukaj produkt
                print("🔍 Wyszukuję 'laptop dell'...")
                await page.fill('input[type="search"]', 'laptop dell')
                await page.press('input[type="search"]', 'Enter')
                
                # Czekaj na wyniki
                await page.wait_for_selector('[data-role="offer"]', timeout=10000)
                
                # Pobierz pierwszy produkt
                products = await page.query_selector_all('[data-role="offer"]')
                if products and len(products) > 0:
                    first = products[0]
                    
                    # Wyciągnij dane
                    title_elem = await first.query_selector('h2')
                    price_elem = await first.query_selector('[aria-label*="cena"]')
                    
                    if title_elem and price_elem:
                        title = await title_elem.inner_text()
                        price = await price_elem.inner_text()
                        
                        print("\n📊 Pierwszy produkt:")
                        print(f"  Tytuł: {title}")
                        print(f"  Cena: {price}")
            else:
                print("❌ Nie udało się rozwiązać CAPTCHA")
                print("\n💡 Wskazówki:")
                print("  1. Spróbuj ponownie")
                print("  2. Użyj proxy")
                print("  3. Dodaj 2captcha API")
        
        print("\n⏸️ Zatrzymuję za 10 sekund...")
        await asyncio.sleep(10)
        
        await browser.close()
        print("✅ Zakończono")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════╗
║     Allegro CAPTCHA Solver                ║  
║     Sliding Puzzle Edition                ║
╚═══════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
