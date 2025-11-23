// ============================================================================
// curllm Chrome Extension - Main Implementation
// ============================================================================

// manifest.json - Chrome Extension Manifest V3
const MANIFEST = {
    "manifest_version": 3,
    "name": "curllm Assistant - Browser Automation with AI",
    "version": "1.0.0",
    "description": "Use AI to automate any website using your active session - no login required!",
    
    "permissions": [
        "activeTab",
        "storage",
        "cookies",
        "tabs",
        "webNavigation",
        "scripting",
        "contextMenus",
        "notifications",
        "sidePanel"
    ],
    
    "host_permissions": [
        "http://localhost:8000/*",
        "http://localhost:11434/*",
        "<all_urls>"
    ],
    
    "background": {
        "service_worker": "background.js",
        "type": "module"
    },
    
    "content_scripts": [{
        "matches": ["<all_urls>"],
        "js": ["content.js"],
        "css": ["styles.css"],
        "run_at": "document_idle",
        "all_frames": false
    }],
    
    "action": {
        "default_popup": "popup.html",
        "default_icon": {
            "16": "icons/icon-16.png",
            "48": "icons/icon-48.png",
            "128": "icons/icon-128.png"
        }
    },
    
    "side_panel": {
        "default_path": "sidepanel.html"
    },
    
    "icons": {
        "16": "icons/icon-16.png",
        "48": "icons/icon-48.png",
        "128": "icons/icon-128.png"
    },
    
    "commands": {
        "execute-command": {
            "suggested_key": {
                "default": "Ctrl+Shift+Space",
                "mac": "Command+Shift+Space"
            },
            "description": "Open quick command palette"
        },
        "toggle-recording": {
            "suggested_key": {
                "default": "Ctrl+Shift+R",
                "mac": "Command+Shift+R"
            },
            "description": "Start/stop recording workflow"
        }
    },
    
    "web_accessible_resources": [{
        "resources": ["inject.js", "styles.css", "icons/*"],
        "matches": ["<all_urls>"]
    }]
};

// ============================================================================
// background.js - Service Worker
// ============================================================================

class CurllmExtension {
    constructor() {
        this.curllmAPI = 'http://localhost:8000';
        this.ollamaAPI = 'http://localhost:11434';
        this.recording = false;
        this.recordedActions = [];
        this.activeTabId = null;
        this.sessionData = {};
        
        this.init();
    }
    
    async init() {
        // Check if curllm server is running
        await this.checkServerStatus();
        
        // Set up event listeners
        this.setupListeners();
        
        // Initialize context menu
        this.setupContextMenu();
        
        // Set up side panel
        await this.setupSidePanel();
    }
    
    async checkServerStatus() {
        try {
            const response = await fetch(`${this.curllmAPI}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                this.setIcon('active');
                this.showNotification('curllm Connected', 'Ready for automation!');
            }
        } catch (error) {
            this.setIcon('inactive');
            this.showNotification('curllm Not Found', 'Please start curllm server');
        }
    }
    
    setupListeners() {
        // Message from content script or popup
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            this.handleMessage(request, sender, sendResponse);
            return true; // Keep channel open for async response
        });
        
        // Tab events
        chrome.tabs.onActivated.addListener(async (activeInfo) => {
            this.activeTabId = activeInfo.tabId;
            await this.captureTabSession(activeInfo.tabId);
        });
        
        // Command shortcuts
        chrome.commands.onCommand.addListener((command) => {
            this.handleCommand(command);
        });
        
        // Context menu clicks
        chrome.contextMenus.onClicked.addListener((info, tab) => {
            this.handleContextMenu(info, tab);
        });
        
        // Storage changes
        chrome.storage.onChanged.addListener((changes, namespace) => {
            this.handleStorageChange(changes, namespace);
        });
    }
    
    async handleMessage(request, sender, sendResponse) {
        switch (request.action) {
            case 'execute':
                const result = await this.executeAutomation(request.data);
                sendResponse(result);
                break;
                
            case 'startRecording':
                this.startRecording(sender.tab.id);
                sendResponse({ success: true });
                break;
                
            case 'stopRecording':
                const workflow = this.stopRecording();
                sendResponse({ success: true, workflow });
                break;
                
            case 'recordAction':
                this.recordAction(request.data);
                sendResponse({ success: true });
                break;
                
            case 'getSession':
                const session = await this.getTabSession(sender.tab.id);
                sendResponse(session);
                break;
                
            case 'analyzePageWithAI':
                const analysis = await this.analyzeWithAI(request.data);
                sendResponse(analysis);
                break;
                
            case 'extractData':
                const extracted = await this.extractData(request.data, sender.tab.id);
                sendResponse(extracted);
                break;
                
            default:
                sendResponse({ error: 'Unknown action' });
        }
    }
    
    async executeAutomation(data) {
        const { instruction, useVisual, useStealth, targetTab } = data;
        
        // Get current tab if not specified
        const tabId = targetTab || this.activeTabId;
        
        // Capture session
        const session = await this.captureTabSession(tabId);
        
        // Prepare request for curllm server
        const request = {
            method: 'POST',
            url: (await chrome.tabs.get(tabId)).url,
            data: instruction,
            visual_mode: useVisual || false,
            stealth_mode: useStealth || false,
            session: {
                cookies: session.cookies,
                localStorage: session.localStorage,
                sessionStorage: session.sessionStorage
            }
        };
        
        try {
            // Send to curllm API
            const response = await fetch(`${this.curllmAPI}/api/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(request)
            });
            
            const result = await response.json();
            
            // Execute actions in browser
            if (result.success && result.actions) {
                await this.executeActionsInTab(tabId, result.actions);
            }
            
            return result;
            
        } catch (error) {
            return { 
                success: false, 
                error: error.message,
                suggestion: 'Make sure curllm server is running (curllm --start-services)'
            };
        }
    }
    
    async captureTabSession(tabId) {
        const tab = await chrome.tabs.get(tabId);
        const url = new URL(tab.url);
        
        // Get cookies
        const cookies = await chrome.cookies.getAll({
            domain: url.hostname
        });
        
        // Get storage via content script
        const storageData = await chrome.tabs.sendMessage(tabId, {
            action: 'getStorage'
        }).catch(() => ({ localStorage: {}, sessionStorage: {} }));
        
        this.sessionData[tabId] = {
            url: tab.url,
            title: tab.title,
            cookies,
            ...storageData,
            timestamp: Date.now()
        };
        
        return this.sessionData[tabId];
    }
    
    async executeActionsInTab(tabId, actions) {
        for (const action of actions) {
            await chrome.tabs.sendMessage(tabId, {
                action: 'executeAction',
                data: action
            });
            
            // Wait between actions
            if (action.wait) {
                await new Promise(resolve => setTimeout(resolve, action.wait));
            }
        }
    }
    
    startRecording(tabId) {
        this.recording = true;
        this.recordedActions = [];
        this.recordingTabId = tabId;
        
        // Inject recording script
        chrome.tabs.sendMessage(tabId, {
            action: 'startRecording'
        });
        
        // Update icon
        this.setIcon('recording');
    }
    
    stopRecording() {
        this.recording = false;
        
        // Stop recording in content script
        chrome.tabs.sendMessage(this.recordingTabId, {
            action: 'stopRecording'
        });
        
        // Update icon
        this.setIcon('active');
        
        // Generate workflow
        return this.generateWorkflow(this.recordedActions);
    }
    
    recordAction(action) {
        if (this.recording) {
            this.recordedActions.push({
                ...action,
                timestamp: Date.now()
            });
        }
    }
    
    generateWorkflow(actions) {
        // Optimize and clean up actions
        const optimized = this.optimizeActions(actions);
        
        return {
            name: `Recording ${new Date().toISOString()}`,
            url: this.sessionData[this.recordingTabId]?.url,
            actions: optimized,
            created: Date.now()
        };
    }
    
    optimizeActions(actions) {
        return actions.reduce((optimized, action, index) => {
            const prev = optimized[optimized.length - 1];
            
            // Merge consecutive inputs
            if (prev?.type === 'input' && action.type === 'input' && 
                prev.selector === action.selector) {
                prev.value = action.value;
                return optimized;
            }
            
            // Remove redundant scrolls
            if (action.type === 'scroll' && prev?.type === 'scroll') {
                prev.position = action.position;
                return optimized;
            }
            
            // Add wait time based on timestamp difference
            if (prev && action.timestamp - prev.timestamp > 1000) {
                optimized.push({
                    type: 'wait',
                    duration: action.timestamp - prev.timestamp
                });
            }
            
            optimized.push(action);
            return optimized;
        }, []);
    }
    
    async analyzeWithAI(data) {
        const { content, question } = data;
        
        try {
            // Use local Ollama
            const response = await fetch(`${this.ollamaAPI}/api/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: 'qwen2.5:7b',
                    prompt: `Analyze this webpage content and ${question}:\n\n${content}`,
                    stream: false
                })
            });
            
            const result = await response.json();
            return { success: true, analysis: result.response };
            
        } catch (error) {
            // Fallback to curllm server
            return await fetch(`${this.curllmAPI}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, question })
            }).then(r => r.json());
        }
    }
    
    setupContextMenu() {
        chrome.contextMenus.create({
            id: 'curllm-extract',
            title: 'Extract with curllm AI',
            contexts: ['selection', 'link', 'image', 'page']
        });
        
        chrome.contextMenus.create({
            id: 'curllm-automate',
            title: 'Automate this action',
            contexts: ['all']
        });
        
        chrome.contextMenus.create({
            id: 'curllm-analyze',
            title: 'Analyze with AI',
            contexts: ['selection', 'page']
        });
    }
    
    async handleContextMenu(info, tab) {
        switch (info.menuItemId) {
            case 'curllm-extract':
                await this.extractFromContext(info, tab);
                break;
            case 'curllm-automate':
                await this.automateFromContext(info, tab);
                break;
            case 'curllm-analyze':
                await this.analyzeFromContext(info, tab);
                break;
        }
    }
    
    async setupSidePanel() {
        if (chrome.sidePanel) {
            await chrome.sidePanel.setOptions({
                enabled: true,
                path: 'sidepanel.html'
            });
            
            await chrome.sidePanel.setPanelBehavior({
                openPanelOnActionClick: true
            });
        }
    }
    
    setIcon(state) {
        const paths = {
            active: 'icons/icon-active.png',
            inactive: 'icons/icon-inactive.png',
            recording: 'icons/icon-recording.png'
        };
        
        chrome.action.setIcon({ path: paths[state] || paths.inactive });
    }
    
    showNotification(title, message) {
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon-128.png',
            title,
            message
        });
    }
}

// Initialize extension
const curllmExtension = new CurllmExtension();

// ============================================================================
// content.js - Content Script
// ============================================================================

class CurllmContentScript {
    constructor() {
        this.recording = false;
        this.picker = null;
        this.overlay = null;
        this.init();
    }
    
    init() {
        // Listen for messages from background
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            this.handleMessage(request, sendResponse);
            return true;
        });
        
        // Inject helper functions
        this.injectHelpers();
    }
    
    handleMessage(request, sendResponse) {
        switch (request.action) {
            case 'getStorage':
                sendResponse({
                    localStorage: this.getLocalStorage(),
                    sessionStorage: this.getSessionStorage()
                });
                break;
                
            case 'executeAction':
                this.executeAction(request.data);
                sendResponse({ success: true });
                break;
                
            case 'startRecording':
                this.startRecording();
                sendResponse({ success: true });
                break;
                
            case 'stopRecording':
                this.stopRecording();
                sendResponse({ success: true });
                break;
                
            case 'enablePicker':
                this.enableElementPicker();
                sendResponse({ success: true });
                break;
                
            case 'getContext':
                sendResponse(this.getPageContext());
                break;
                
            default:
                sendResponse({ error: 'Unknown action' });
        }
    }
    
    getLocalStorage() {
        const storage = {};
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            storage[key] = localStorage.getItem(key);
        }
        return storage;
    }
    
    getSessionStorage() {
        const storage = {};
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            storage[key] = sessionStorage.getItem(key);
        }
        return storage;
    }
    
    getPageContext() {
        return {
            url: window.location.href,
            title: document.title,
            html: document.documentElement.outerHTML.substring(0, 10000),
            text: document.body.innerText.substring(0, 5000),
            forms: this.getForms(),
            links: this.getLinks(),
            images: this.getImages(),
            tables: this.getTables(),
            metadata: this.getMetadata()
        };
    }
    
    getForms() {
        return Array.from(document.forms).map(form => ({
            id: form.id,
            name: form.name,
            action: form.action,
            method: form.method,
            fields: Array.from(form.elements).map(el => ({
                name: el.name,
                type: el.type,
                id: el.id,
                required: el.required,
                placeholder: el.placeholder
            }))
        }));
    }
    
    getLinks() {
        return Array.from(document.links).slice(0, 100).map(link => ({
            href: link.href,
            text: link.innerText,
            title: link.title
        }));
    }
    
    getImages() {
        return Array.from(document.images).slice(0, 50).map(img => ({
            src: img.src,
            alt: img.alt,
            title: img.title
        }));
    }
    
    getTables() {
        return Array.from(document.querySelectorAll('table')).map(table => {
            const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText);
            const rows = Array.from(table.querySelectorAll('tr')).slice(1).map(tr => 
                Array.from(tr.querySelectorAll('td')).map(td => td.innerText)
            );
            return { headers, rows };
        });
    }
    
    getMetadata() {
        const meta = {};
        document.querySelectorAll('meta').forEach(tag => {
            const name = tag.name || tag.getAttribute('property');
            if (name) meta[name] = tag.content;
        });
        return meta;
    }
    
    executeAction(action) {
        switch (action.type) {
            case 'click':
                this.click(action.selector);
                break;
            case 'input':
                this.input(action.selector, action.value);
                break;
            case 'select':
                this.select(action.selector, action.value);
                break;
            case 'scroll':
                this.scroll(action.position);
                break;
            case 'wait':
                setTimeout(() => {}, action.duration);
                break;
            case 'extract':
                return this.extract(action.selector);
        }
    }
    
    click(selector) {
        const element = document.querySelector(selector);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            element.click();
            this.highlightElement(element, 'success');
        }
    }
    
    input(selector, value) {
        const element = document.querySelector(selector);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            element.value = value;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            this.highlightElement(element, 'success');
        }
    }
    
    select(selector, value) {
        const element = document.querySelector(selector);
        if (element) {
            element.value = value;
            element.dispatchEvent(new Event('change', { bubbles: true }));
            this.highlightElement(element, 'success');
        }
    }
    
    scroll(position) {
        if (typeof position === 'number') {
            window.scrollTo({ top: position, behavior: 'smooth' });
        } else {
            window.scrollTo({ 
                top: position.y || 0, 
                left: position.x || 0, 
                behavior: 'smooth' 
            });
        }
    }
    
    extract(selector) {
        const elements = document.querySelectorAll(selector);
        return Array.from(elements).map(el => ({
            text: el.innerText,
            html: el.innerHTML,
            attributes: Array.from(el.attributes).reduce((attrs, attr) => {
                attrs[attr.name] = attr.value;
                return attrs;
            }, {})
        }));
    }
    
    startRecording() {
        this.recording = true;
        this.attachRecordingListeners();
        this.showRecordingOverlay();
    }
    
    stopRecording() {
        this.recording = false;
        this.removeRecordingListeners();
        this.hideRecordingOverlay();
    }
    
    attachRecordingListeners() {
        this.recordClick = (e) => {
            if (this.recording) {
                chrome.runtime.sendMessage({
                    action: 'recordAction',
                    data: {
                        type: 'click',
                        selector: this.getSelector(e.target),
                        position: { x: e.clientX, y: e.clientY }
                    }
                });
            }
        };
        
        this.recordInput = (e) => {
            if (this.recording) {
                chrome.runtime.sendMessage({
                    action: 'recordAction',
                    data: {
                        type: 'input',
                        selector: this.getSelector(e.target),
                        value: e.target.value
                    }
                });
            }
        };
        
        this.recordScroll = (e) => {
            if (this.recording) {
                chrome.runtime.sendMessage({
                    action: 'recordAction',
                    data: {
                        type: 'scroll',
                        position: { x: window.scrollX, y: window.scrollY }
                    }
                });
            }
        };
        
        document.addEventListener('click', this.recordClick, true);
        document.addEventListener('input', this.recordInput, true);
        document.addEventListener('scroll', this.recordScroll, true);
    }
    
    removeRecordingListeners() {
        document.removeEventListener('click', this.recordClick, true);
        document.removeEventListener('input', this.recordInput, true);
        document.removeEventListener('scroll', this.recordScroll, true);
    }
    
    getSelector(element) {
        if (element.id) return `#${element.id}`;
        
        if (element.className) {
            const classes = element.className.split(' ')
                .filter(c => c && !c.includes('curllm'))
                .join('.');
            if (classes) return `${element.tagName.toLowerCase()}.${classes}`;
        }
        
        // Generate nth-child selector
        let path = [];
        while (element.parentElement) {
            let siblings = Array.from(element.parentElement.children);
            let index = siblings.indexOf(element) + 1;
            path.unshift(`${element.tagName.toLowerCase()}:nth-child(${index})`);
            element = element.parentElement;
            if (element.id) {
                path.unshift(`#${element.id}`);
                break;
            }
        }
        return path.join(' > ');
    }
    
    enableElementPicker() {
        if (this.picker) return;
        
        this.picker = document.createElement('div');
        this.picker.className = 'curllm-picker';
        this.picker.style.cssText = `
            position: fixed;
            border: 2px solid #4CAF50;
            background: rgba(76, 175, 80, 0.1);
            pointer-events: none;
            z-index: 999999;
            transition: all 0.2s;
        `;
        document.body.appendChild(this.picker);
        
        this.handleHover = (e) => {
            const rect = e.target.getBoundingClientRect();
            this.picker.style.left = rect.left + 'px';
            this.picker.style.top = rect.top + 'px';
            this.picker.style.width = rect.width + 'px';
            this.picker.style.height = rect.height + 'px';
        };
        
        this.handleClick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const selector = this.getSelector(e.target);
            chrome.runtime.sendMessage({
                action: 'elementSelected',
                data: { selector, element: e.target.outerHTML }
            });
            
            this.disableElementPicker();
        };
        
        document.addEventListener('mouseover', this.handleHover);
        document.addEventListener('click', this.handleClick, true);
    }
    
    disableElementPicker() {
        if (this.picker) {
            this.picker.remove();
            this.picker = null;
        }
        document.removeEventListener('mouseover', this.handleHover);
        document.removeEventListener('click', this.handleClick, true);
    }
    
    highlightElement(element, type = 'info') {
        const colors = {
            info: '#2196F3',
            success: '#4CAF50',
            warning: '#FF9800',
            error: '#F44336'
        };
        
        const originalBorder = element.style.border;
        const originalBackground = element.style.background;
        
        element.style.border = `2px solid ${colors[type]}`;
        element.style.background = `${colors[type]}22`;
        
        setTimeout(() => {
            element.style.border = originalBorder;
            element.style.background = originalBackground;
        }, 2000);
    }
    
    showRecordingOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'curllm-recording-overlay';
        this.overlay.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: #F44336;
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                z-index: 999999;
                display: flex;
                align-items: center;
                gap: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            ">
                <span style="
                    width: 10px;
                    height: 10px;
                    background: white;
                    border-radius: 50%;
                    animation: pulse 1s infinite;
                "></span>
                Recording...
            </div>
            <style>
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.5; }
                    100% { opacity: 1; }
                }
            </style>
        `;
        document.body.appendChild(this.overlay);
    }
    
    hideRecordingOverlay() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
    }
    
    injectHelpers() {
        // Inject helper functions for automation
        const script = document.createElement('script');
        script.textContent = `
            window.curllmHelpers = {
                fillForm: function(data) {
                    Object.entries(data).forEach(([key, value]) => {
                        const input = document.querySelector(\`[name="\${key}"]\`) ||
                                     document.querySelector(\`#\${key}\`);
                        if (input) {
                            input.value = value;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    });
                },
                
                waitForElement: function(selector, timeout = 5000) {
                    return new Promise((resolve, reject) => {
                        const element = document.querySelector(selector);
                        if (element) return resolve(element);
                        
                        const observer = new MutationObserver((mutations, obs) => {
                            const element = document.querySelector(selector);
                            if (element) {
                                obs.disconnect();
                                resolve(element);
                            }
                        });
                        
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true
                        });
                        
                        setTimeout(() => {
                            observer.disconnect();
                            reject(new Error('Element not found: ' + selector));
                        }, timeout);
                    });
                },
                
                extractTable: function(selector) {
                    const table = document.querySelector(selector);
                    if (!table) return null;
                    
                    const headers = Array.from(table.querySelectorAll('th'))
                        .map(th => th.innerText);
                    const rows = Array.from(table.querySelectorAll('tr'))
                        .slice(1)
                        .map(tr => Array.from(tr.querySelectorAll('td'))
                            .map(td => td.innerText));
                    
                    return { headers, rows };
                }
            };
        `;
        document.head.appendChild(script);
    }
}

// Initialize content script
const curllmContent = new CurllmContentScript();

// Export for testing
if (typeof module !== 'undefined') {
    module.exports = { CurllmContentScript };
}