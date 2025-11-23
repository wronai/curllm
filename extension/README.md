# 🔌 curllm Browser Extension

## Wtyczka przeglądarkowa dla automatyzacji z lokalnym AI

### ✨ Kluczowe funkcje

- **🔐 Wykorzystuje aktywną sesję** - nie musisz się logować ponownie
- **🤖 AI w przeglądarce** - lokalne LLM bezpośrednio w Chrome/Firefox
- **🎬 Nagrywanie workflow** - nagraj raz, odtwarzaj wielokrotnie
- **🎯 Visual picker** - wskaż element myszką
- **💾 Offline first** - wszystko działa lokalnie

## 📦 Instalacja

### Metoda 1: Chrome Web Store (wkrótce)
```
Wtyczka zostanie opublikowana w Chrome Web Store
```

### Metoda 2: Instalacja deweloperska

1. **Pobierz rozszerzenie**
```bash
git clone https://github.com/softreck/curllm-extension
cd curllm-extension
```

2. **Zainstaluj w Chrome**
- Otwórz `chrome://extensions/`
- Włącz "Tryb dewelopera"
- Kliknij "Załaduj rozpakowane"
- Wybierz folder `curllm-extension`

3. **Zainstaluj w Firefox**
- Otwórz `about:debugging`
- Kliknij "This Firefox"
- Kliknij "Load Temporary Add-on"
- Wybierz `manifest.json`

## 🚀 Pierwsze użycie

### 1. Uruchom serwer curllm
```bash
# Upewnij się, że serwer działa
curllm --start-services
```

### 2. Otwórz stronę do automatyzacji
```
Np. https://allegro.pl
```

### 3. Kliknij ikonę wtyczki
- Wpisz polecenie: "znajdź najtańszy laptop Dell"
- Naciśnij Enter
- Obserwuj magię! ✨

## 📖 Przykłady użycia

### Proste polecenia tekstowe
```javascript
// W popup wtyczki wpisz:
"wyciągnij wszystkie emaile"
"wypełnij formularz testowymi danymi"
"kliknij przycisk Dalej"
"pobierz tabelę jako Excel"
```

### Nagrywanie workflow
1. Kliknij **🔴 Record**
2. Wykonaj akcje na stronie
3. Kliknij **⏹ Stop**
4. Workflow zapisany!

### Używanie Side Panel (Chrome 114+)
1. Kliknij prawym na ikonie wtyczki
2. Wybierz "Open side panel"
3. Buduj workflow vizualnie

## 🎯 Przypadki użycia

### E-commerce (Allegro/OLX)
```javascript
// Automatyczny monitoring cen
"sprawdzaj cenę tego produktu co godzinę i powiadom gdy spadnie"

// Masowe dodawanie ogłoszeń
"dodaj 50 ogłoszeń z pliku CSV"

// Analiza konkurencji
"znajdź wszystkich sprzedawców laptopów i porównaj ceny"
```

### Banking
```javascript
// Pobieranie wyciągów (z zachowaniem sesji!)
"pobierz wyciąg za ostatni miesiąc jako PDF"

// Automatyczne kategoryzowanie transakcji
"oznacz wszystkie płatności w Biedronce jako 'Zakupy spożywcze'"
```

### Social Media
```javascript
// Cross-posting
"opublikuj ten post na Facebook, LinkedIn i Twitter"

// Bulk operations
"polub wszystkie posty z ostatniego tygodnia"
```

### Urzędy (ePUAP)
```javascript
// Wypełnianie wniosków
"wypełnij wniosek o 500+ używając danych z pliku"

// Sprawdzanie statusów
"sprawdź status wszystkich moich wniosków"
```

## ⚙️ Konfiguracja

### config.json
```json
{
  "server": {
    "url": "http://localhost:8000",
    "apiKey": null
  },
  "ollama": {
    "url": "http://localhost:11434",
    "model": "qwen2.5:7b"
  },
  "features": {
    "recording": true,
    "visualPicker": true,
    "aiChat": true,
    "sidePanel": true,
    "contextMenu": true
  },
  "automation": {
    "defaultTimeout": 5000,
    "stepDelay": 500,
    "screenshotOnError": true,
    "retryOnFailure": 3
  },
  "privacy": {
    "storePasswords": false,
    "encryptStorage": true,
    "telemetry": false
  },
  "shortcuts": {
    "quickCommand": "Ctrl+Shift+Space",
    "toggleRecording": "Ctrl+Shift+R",
    "elementPicker": "Ctrl+Shift+E"
  }
}
```

## 🔧 API dla developerów

### Używanie w własnych skryptach
```javascript
// Połącz się z wtyczką
const curllm = await chrome.runtime.connect({ name: 'curllm' });

// Wykonaj automatyzację
curllm.postMessage({
  action: 'execute',
  data: {
    instruction: 'Fill form with test data',
    visual: true
  }
});

// Odbierz wynik
curllm.onMessage.addListener((response) => {
  console.log('Result:', response);
});
```

### Custom workflows
```javascript
// workflow.js
const myWorkflow = {
  name: 'Daily Allegro Check',
  triggers: ['daily', '09:00'],
  steps: [
    { action: 'navigate', url: 'https://allegro.pl/moje-allegro' },
    { action: 'login', auto: true },
    { action: 'extract', selector: '.sales-summary' },
    { action: 'notify', channel: 'email' }
  ]
};

// Register workflow
chrome.storage.local.set({ workflows: [myWorkflow] });
```

### Integracja z zewnętrznymi narzędziami
```javascript
// Zapier webhook
const zapierHook = 'https://hooks.zapier.com/...';

curllm.onDataExtracted.addListener(async (data) => {
  await fetch(zapierHook, {
    method: 'POST',
    body: JSON.stringify(data)
  });
});
```

## 🔒 Bezpieczeństwo

### Co robimy dla Twojej prywatności:
- ✅ **100% lokalnie** - żadne dane nie idą do chmury
- ✅ **Szyfrowanie storage** - AES-256 dla zapisanych danych
- ✅ **No tracking** - zero telemetrii
- ✅ **Open source** - sprawdź kod sam

### Uprawnienia których potrzebujemy:
- `activeTab` - do interakcji z aktywną kartą
- `storage` - do zapisywania workflow
- `cookies` - do wykorzystania sesji (opcjonalne)
- `webNavigation` - do nawigacji między stronami

## 🐛 Rozwiązywanie problemów

### "curllm server not found"
```bash
# Sprawdź czy serwer działa
curl http://localhost:8000/health

# Jeśli nie, uruchom:
curllm --start-services
```

### "Permission denied"
- Sprawdź czy wtyczka ma uprawnienia do strony
- Niektóre strony (bank, Google) mogą blokować wtyczki

### "AI not responding"
```bash
# Sprawdź Ollama
curl http://localhost:11434/api/tags

# Pobierz model jeśli brak
ollama pull qwen2.5:7b
```

## 📊 Metryki wydajności

| Operacja | Czas | CPU | RAM |
|----------|------|-----|-----|
| Start wtyczki | <100ms | 1% | 50MB |
| Wykonanie polecenia | 1-3s | 5% | 100MB |
| Nagrywanie (per action) | <10ms | 1% | +5MB |
| AI analysis | 2-5s | 20% | 200MB |

## 🗺️ Roadmap

### v1.1 (Q1 2025)
- [ ] Firefox pełne wsparcie
- [ ] Safari (MacOS)
- [ ] Cloud sync (opcjonalny)
- [ ] Marketplace dla workflow

### v1.2 (Q2 2025)
- [ ] Mobile browsers (Kiwi, Firefox Mobile)
- [ ] Team sharing
- [ ] Visual workflow designer
- [ ] Zapier/Make integration

### v2.0 (Q3 2025)
- [ ] Multi-tab orchestration
- [ ] Conditional logic
- [ ] Variables & data transformation
- [ ] Custom JavaScript execution

## 🤝 Contributing

```bash
# Fork & clone
git clone https://github.com/YOUR_USER/curllm-extension

# Install deps
npm install

# Development mode
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

## 📄 Licencja

MIT - możesz używać komercyjnie!

## 🆘 Wsparcie

- 📧 Email: extension@curllm.io
- 💬 Discord: [discord.gg/curllm](https://discord.gg/curllm)
- 🐛 Issues: [GitHub](https://github.com/softreck/curllm-extension/issues)
- 📚 Docs: [docs.curllm.io/extension](https://docs.curllm.io/extension)

---

### ⭐ Jeśli podoba Ci się projekt, zostaw gwiazdkę na GitHub!

**curllm Extension** - Where Your Browser Becomes Intelligent 🧠✨