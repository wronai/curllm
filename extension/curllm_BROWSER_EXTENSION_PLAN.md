# 🔌 curllm Browser Extension - Architektura i Plan Implementacji

## 🎯 Koncepcja

**curllm Extension** - wtyczka do Chrome/Firefox która:
- ✅ Wykorzystuje aktywną sesję użytkownika (cookies, localStorage)
- ✅ Wykonuje automatyzacje bez ponownego logowania
- ✅ Komunikuje się z lokalnym serwerem curllm
- ✅ Oferuje visual picker do wyboru elementów
- ✅ Nagrywa i odtwarza workflow

## 🏗️ Architektura

```
┌─────────────────────────────────────────────────────┐
│                   Browser Tab                        │
│  ┌─────────────────────────────────────────────┐    │
│  │            Website (Active Session)          │    │
│  │                                              │    │
│  │  ┌────────────────────────────────────┐     │    │
│  │  │     Content Script (injected)       │     │    │
│  │  │  - DOM manipulation                 │     │    │
│  │  │  - Element selection               │     │    │
│  │  │  - Event simulation                │     │    │
│  │  └──────────────┬─────────────────────┘     │    │
│  └─────────────────┼────────────────────────────┘   │
│                    │                                 │
│  ┌─────────────────▼────────────────────────────┐   │
│  │           Background Script                   │   │
│  │  - Session management                        │   │
│  │  - API communication                         │   │
│  │  - Task orchestration                        │   │
│  └─────────────────┬────────────────────────────┘   │
└────────────────────┼─────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │  Local curllm Server    │
        │  - LLM processing       │
        │  - Complex workflows    │
        │  - Data persistence     │
        └─────────────────────────┘
```

## 📦 Struktura Projektu

```
browser-extension/
├── manifest.json              # Extension manifest (v3)
├── src/
│   ├── background/
│   │   ├── service-worker.js # Background service worker
│   │   ├── api-client.js     # curllm API communication
│   │   └── session-manager.js # Session handling
│   │
│   ├── content/
│   │   ├── content.js        # Main content script
│   │   ├── dom-observer.js   # DOM mutation observer
│   │   ├── element-picker.js # Visual element selector
│   │   ├── recorder.js       # Action recorder
│   │   └── executor.js       # Action executor
│   │
│   ├── popup/
│   │   ├── popup.html        # Extension popup UI
│   │   ├── popup.js          # Popup logic
│   │   └── popup.css         # Styling
│   │
│   ├── sidepanel/            # Chrome Side Panel API
│   │   ├── panel.html        # Side panel UI
│   │   ├── panel.js          # Panel controller
│   │   └── components/       # UI components
│   │
│   ├── options/
│   │   ├── options.html      # Settings page
│   │   └── options.js        # Settings logic
│   │
│   └── shared/
│       ├── constants.js      # Shared constants
│       ├── storage.js        # Chrome storage API
│       └── utils.js          # Helper functions
│
├── assets/
│   ├── icons/                # Extension icons
│   └── styles/               # Global styles
│
├── lib/                      # Third-party libraries
├── dist/                     # Build output
└── tests/                    # Extension tests
```

## 🚀 Kluczowe Funkcje

### 1. Smart Session Hijacking
```javascript
// background/session-manager.js
class SessionManager {
    async captureSession(tabId) {
        // Pobierz cookies dla aktywnej domeny
        const cookies = await chrome.cookies.getAll({
            url: await this.getTabUrl(tabId)
        });
        
        // Pobierz localStorage przez content script
        const localStorage = await chrome.tabs.sendMessage(tabId, {
            action: 'getLocalStorage'
        });
        
        // Pobierz sessionStorage
        const sessionStorage = await chrome.tabs.sendMessage(tabId, {
            action: 'getSessionStorage'
        });
        
        return {
            cookies,
            localStorage,
            sessionStorage,
            userAgent: navigator.userAgent,
            timestamp: Date.now()
        };
    }
    
    async injectSession(session, targetUrl) {
        // Przywróć sesję w nowej karcie
        const tab = await chrome.tabs.create({ url: targetUrl });
        
        // Ustaw cookies
        for (const cookie of session.cookies) {
            await chrome.cookies.set({
                url: targetUrl,
                ...cookie
            });
        }
        
        // Inject storage via content script
        await chrome.tabs.sendMessage(tab.id, {
            action: 'restoreStorage',
            data: {
                localStorage: session.localStorage,
                sessionStorage: session.sessionStorage
            }
        });
    }
}
```

### 2. Visual Element Picker
```javascript
// content/element-picker.js
class ElementPicker {
    constructor() {
        this.overlay = null;
        this.highlighter = null;
        this.selectedElements = [];
    }
    
    enable() {
        this.createOverlay();
        document.addEventListener('mouseover', this.highlight);
        document.addEventListener('click', this.select);
    }
    
    highlight = (e) => {
        e.stopPropagation();
        const rect = e.target.getBoundingClientRect();
        
        this.highlighter.style.left = rect.left + 'px';
        this.highlighter.style.top = rect.top + 'px';
        this.highlighter.style.width = rect.width + 'px';
        this.highlighter.style.height = rect.height + 'px';
        
        // Show element info
        this.showElementInfo(e.target);
    }
    
    select = (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        const selector = this.generateSelector(e.target);
        const xpath = this.generateXPath(e.target);
        
        this.selectedElements.push({
            selector,
            xpath,
            text: e.target.innerText,
            attributes: this.getAttributes(e.target)
        });
        
        // Send to extension
        chrome.runtime.sendMessage({
            action: 'elementSelected',
            data: this.selectedElements
        });
    }
    
    generateSelector(element) {
        // Smart selector generation
        if (element.id) return `#${element.id}`;
        if (element.className) {
            const classes = element.className.split(' ').join('.');
            return `${element.tagName.toLowerCase()}.${classes}`;
        }
        // Fallback to nth-child
        return this.getNthChildSelector(element);
    }
}
```

### 3. Workflow Recorder
```javascript
// content/recorder.js
class WorkflowRecorder {
    constructor() {
        this.recording = false;
        this.actions = [];
        this.startTime = null;
    }
    
    startRecording() {
        this.recording = true;
        this.startTime = Date.now();
        this.actions = [];
        
        // Attach listeners
        this.attachListeners();
        
        // Start mutation observer
        this.observeMutations();
    }
    
    attachListeners() {
        // Click events
        document.addEventListener('click', this.recordClick, true);
        
        // Form inputs
        document.addEventListener('input', this.recordInput, true);
        document.addEventListener('change', this.recordChange, true);
        
        // Keyboard
        document.addEventListener('keydown', this.recordKeypress, true);
        
        // Scroll
        document.addEventListener('scroll', this.recordScroll, true);
        
        // Page navigation
        window.addEventListener('beforeunload', this.recordNavigation);
    }
    
    recordClick = (e) => {
        this.actions.push({
            type: 'click',
            selector: this.getSelector(e.target),
            timestamp: Date.now() - this.startTime,
            position: { x: e.clientX, y: e.clientY },
            text: e.target.innerText?.substring(0, 50)
        });
    }
    
    recordInput = (e) => {
        this.actions.push({
            type: 'input',
            selector: this.getSelector(e.target),
            value: e.target.value,
            timestamp: Date.now() - this.startTime
        });
    }
    
    generateWorkflow() {
        return {
            url: window.location.href,
            actions: this.optimizeActions(this.actions),
            duration: Date.now() - this.startTime,
            metadata: {
                title: document.title,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            }
        };
    }
    
    optimizeActions(actions) {
        // Merge consecutive input events
        // Remove redundant scrolls
        // Optimize wait times
        return actions.reduce((optimized, action, index) => {
            const prev = optimized[optimized.length - 1];
            
            if (prev?.type === 'input' && 
                action.type === 'input' && 
                prev.selector === action.selector) {
                // Merge inputs
                prev.value = action.value;
                prev.timestamp = action.timestamp;
            } else {
                optimized.push(action);
            }
            
            return optimized;
        }, []);
    }
}
```

### 4. AI Assistant Integration
```javascript
// popup/popup.js
class CurllmAssistant {
    constructor() {
        this.apiClient = new CurllmAPIClient();
    }
    
    async executeCommand(naturalLanguage) {
        // Send to local curllm server
        const response = await this.apiClient.interpret({
            instruction: naturalLanguage,
            context: await this.getPageContext()
        });
        
        // Execute actions in current tab
        const tab = await chrome.tabs.query({active: true, currentWindow: true});
        
        for (const action of response.actions) {
            await chrome.tabs.sendMessage(tab[0].id, {
                action: 'execute',
                data: action
            });
            
            // Wait between actions
            await this.wait(action.delay || 500);
        }
    }
    
    async getPageContext() {
        const tab = await chrome.tabs.query({active: true, currentWindow: true});
        
        return await chrome.tabs.sendMessage(tab[0].id, {
            action: 'getContext'
        });
    }
}

// Usage
const assistant = new CurllmAssistant();

// Natural language commands
document.getElementById('commandInput').addEventListener('submit', async (e) => {
    e.preventDefault();
    const command = e.target.command.value;
    
    // Examples:
    // "Fill all forms with test data"
    // "Extract all prices and save to Excel"
    // "Click next button until no more pages"
    // "Login using saved credentials"
    
    await assistant.executeCommand(command);
});
```

## 📋 Manifest Configuration

### Chrome Manifest V3
```json
{
    "manifest_version": 3,
    "name": "curllm Assistant",
    "version": "1.0.0",
    "description": "AI-powered browser automation using your active session",
    
    "permissions": [
        "activeTab",
        "storage",
        "cookies",
        "tabs",
        "webNavigation",
        "scripting",
        "sidePanel",
        "contextMenus",
        "notifications"
    ],
    
    "host_permissions": [
        "http://localhost:8000/*",
        "<all_urls>"
    ],
    
    "background": {
        "service_worker": "src/background/service-worker.js"
    },
    
    "content_scripts": [{
        "matches": ["<all_urls>"],
        "js": ["src/content/content.js"],
        "css": ["assets/styles/content.css"],
        "run_at": "document_idle"
    }],
    
    "action": {
        "default_popup": "src/popup/popup.html",
        "default_icon": {
            "16": "assets/icons/icon-16.png",
            "48": "assets/icons/icon-48.png",
            "128": "assets/icons/icon-128.png"
        }
    },
    
    "side_panel": {
        "default_path": "src/sidepanel/panel.html"
    },
    
    "options_page": "src/options/options.html",
    
    "commands": {
        "toggle-recorder": {
            "suggested_key": {
                "default": "Ctrl+Shift+R"
            },
            "description": "Toggle workflow recording"
        },
        "quick-command": {
            "suggested_key": {
                "default": "Ctrl+Shift+Space"
            },
            "description": "Open quick command"
        }
    },
    
    "web_accessible_resources": [{
        "resources": ["assets/*", "src/content/inject.js"],
        "matches": ["<all_urls>"]
    }]
}
```

## 🎨 UI Components

### 1. Popup Interface
```html
<!-- popup.html -->
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="popup.css">
</head>
<body>
    <div class="curllm-popup">
        <!-- Quick Actions -->
        <div class="quick-actions">
            <button id="record" class="btn-primary">
                🔴 Record Workflow
            </button>
            <button id="picker" class="btn-secondary">
                🎯 Pick Element
            </button>
        </div>
        
        <!-- Command Input -->
        <div class="command-input">
            <input type="text" 
                   id="command" 
                   placeholder="What should I do? (e.g., 'extract all emails')"
                   autocomplete="off">
            <button id="execute">▶️</button>
        </div>
        
        <!-- Saved Workflows -->
        <div class="workflows">
            <h3>Recent Workflows</h3>
            <div id="workflow-list"></div>
        </div>
        
        <!-- Status -->
        <div class="status">
            <span class="indicator"></span>
            <span id="status-text">Connected to curllm</span>
        </div>
    </div>
</body>
<script src="popup.js"></script>
</html>
```

### 2. Side Panel (Chrome 114+)
```javascript
// sidepanel/panel.js
class CurllmSidePanel {
    constructor() {
        this.workflows = [];
        this.activeWorkflow = null;
        this.initializeUI();
    }
    
    initializeUI() {
        // Workflow Builder
        this.workflowBuilder = new WorkflowBuilder('#workflow-builder');
        
        // Live Preview
        this.livePreview = new LivePreview('#live-preview');
        
        // Data Extractor
        this.dataExtractor = new DataExtractor('#data-extractor');
        
        // AI Chat
        this.aiChat = new AIChat('#ai-chat');
    }
    
    async runWorkflow(workflow) {
        this.activeWorkflow = workflow;
        
        for (const step of workflow.steps) {
            await this.executeStep(step);
            this.updateProgress(step);
            
            // Visual feedback
            this.highlightElement(step.selector);
        }
    }
}
```

## 🔧 Implementacja - Przykłady

### 1. Auto-Login z Saved Session
```javascript
// features/auto-login.js
class AutoLogin {
    async loginWithSavedSession(site) {
        // Get saved credentials from encrypted storage
        const credentials = await this.getCredentials(site);
        
        if (!credentials) {
            return this.promptForCredentials();
        }
        
        // Find login form
        const loginForm = await this.findLoginForm();
        
        // Fill credentials
        await this.fillForm(loginForm, credentials);
        
        // Handle 2FA if needed
        if (await this.requires2FA()) {
            await this.handle2FA();
        }
        
        return true;
    }
}
```

### 2. Bulk Data Extraction
```javascript
// features/data-extractor.js
class DataExtractor {
    async extractTableData() {
        const tables = document.querySelectorAll('table');
        const data = [];
        
        for (const table of tables) {
            const headers = Array.from(table.querySelectorAll('th'))
                .map(th => th.innerText);
            
            const rows = Array.from(table.querySelectorAll('tr'))
                .slice(1) // Skip header row
                .map(tr => {
                    const cells = Array.from(tr.querySelectorAll('td'));
                    return headers.reduce((obj, header, index) => {
                        obj[header] = cells[index]?.innerText || '';
                        return obj;
                    }, {});
                });
            
            data.push({ headers, rows });
        }
        
        // Send to curllm for processing
        return await this.processWithAI(data);
    }
    
    async processWithAI(data) {
        return await fetch('http://localhost:8000/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data,
                instruction: 'Analyze this data and provide insights'
            })
        }).then(r => r.json());
    }
}
```

### 3. Smart Form Filling
```javascript
// features/form-filler.js
class SmartFormFiller {
    async fillForm(formData = {}) {
        const inputs = document.querySelectorAll('input, select, textarea');
        
        for (const input of inputs) {
            const fieldType = this.detectFieldType(input);
            const value = formData[fieldType] || this.generateTestData(fieldType);
            
            // Skip honeypots
            if (this.isHoneypot(input)) continue;
            
            await this.fillField(input, value);
        }
    }
    
    detectFieldType(input) {
        // Use AI to detect field purpose
        const attributes = {
            name: input.name,
            id: input.id,
            placeholder: input.placeholder,
            label: this.getLabel(input),
            type: input.type
        };
        
        // Pattern matching
        if (/email/i.test(JSON.stringify(attributes))) return 'email';
        if (/phone|tel/i.test(JSON.stringify(attributes))) return 'phone';
        if (/name/i.test(JSON.stringify(attributes))) return 'name';
        // ... more patterns
        
        return 'generic';
    }
    
    isHoneypot(input) {
        const style = window.getComputedStyle(input);
        return (
            style.display === 'none' ||
            style.visibility === 'hidden' ||
            style.opacity === '0' ||
            input.offsetHeight === 0 ||
            input.hasAttribute('tabindex') && input.tabIndex < 0
        );
    }
}
```

## 🚀 Deployment

### Build Script
```json
// package.json
{
    "name": "curllm-extension",
    "version": "1.0.0",
    "scripts": {
        "dev": "webpack --mode development --watch",
        "build": "webpack --mode production",
        "build:chrome": "cross-env TARGET=chrome npm run build",
        "build:firefox": "cross-env TARGET=firefox npm run build",
        "test": "jest",
        "lint": "eslint src/",
        "package": "npm run build && web-ext build"
    },
    "devDependencies": {
        "webpack": "^5.88.0",
        "webpack-cli": "^5.1.4",
        "copy-webpack-plugin": "^11.0.0",
        "clean-webpack-plugin": "^4.0.0",
        "web-ext": "^7.6.2",
        "jest": "^29.5.0",
        "eslint": "^8.44.0"
    }
}
```

## 📊 Monetization

### Freemium Model
```javascript
// Free Tier
const FREE_FEATURES = {
    recordingsPerDay: 10,
    automationsPerDay: 50,
    storage: '10MB',
    workflows: 5
};

// Pro Tier ($9.99/month)
const PRO_FEATURES = {
    recordingsPerDay: 'unlimited',
    automationsPerDay: 'unlimited',
    storage: '1GB',
    workflows: 'unlimited',
    cloudSync: true,
    prioritySupport: true,
    advancedAI: true
};

// Team Tier ($29.99/month)
const TEAM_FEATURES = {
    ...PRO_FEATURES,
    teamSharing: true,
    analytics: true,
    customBranding: true,
    apiAccess: true
};
```

## 🔐 Security

### Permissions Model
```javascript
// Minimal permissions by default
const CORE_PERMISSIONS = ['activeTab', 'storage'];

// Request additional permissions as needed
async function requestPermission(permission) {
    const granted = await chrome.permissions.request({
        permissions: [permission]
    });
    
    if (!granted) {
        throw new Error(`Permission ${permission} not granted`);
    }
}

// Encrypt sensitive data
class SecureStorage {
    async save(key, value) {
        const encrypted = await this.encrypt(value);
        await chrome.storage.local.set({ [key]: encrypted });
    }
    
    async get(key) {
        const { [key]: encrypted } = await chrome.storage.local.get(key);
        return await this.decrypt(encrypted);
    }
    
    async encrypt(data) {
        // Use WebCrypto API
        const key = await this.getKey();
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const encoded = new TextEncoder().encode(JSON.stringify(data));
        
        const encrypted = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv },
            key,
            encoded
        );
        
        return { iv: Array.from(iv), data: Array.from(new Uint8Array(encrypted)) };
    }
}
```

## 📈 Analytics & Tracking

```javascript
// Usage analytics (privacy-friendly)
class Analytics {
    track(event, properties = {}) {
        // Only track aggregated, anonymous data
        const payload = {
            event,
            properties: {
                ...properties,
                version: chrome.runtime.getManifest().version,
                timestamp: Date.now()
            }
        };
        
        // Send to local curllm server, not external service
        fetch('http://localhost:8000/api/analytics', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
}
```

## 🎯 Use Cases

1. **E-commerce Automation**
   - Auto-refresh for limited drops
   - Price monitoring across sites
   - Bulk product listing

2. **Social Media Management**
   - Cross-posting content
   - Bulk follow/unfollow
   - Comment moderation

3. **Data Research**
   - Academic paper collection
   - Market research automation
   - Competitor analysis

4. **Testing & QA**
   - Regression testing
   - Form validation
   - Cross-browser testing

5. **Personal Productivity**
   - Auto-fill job applications
   - Calendar synchronization
   - Email filtering

---

**Extension = Game Changer** 

Wtyczka to brakujący element układanki - połączenie mocy lokalnego AI z wygodą przeglądarki! 🚀