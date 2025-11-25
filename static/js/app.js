// curllm Web Client - JavaScript Application

let prompts = [];
let currentLogFile = null;
let lastResult = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadPrompts();
    checkHealth();
    setInterval(checkHealth, 30000); // Check health every 30s
    // Attach listeners for CLI preview updates
    const ids = [
        'url-input','prompt-select','prompt-text',
        'visual-mode','stealth-mode','captcha-solver',
        'bql-mode','verbose-mode','headful-mode',
        'session-id','proxy-input'
    ];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            const evt = (el.tagName === 'SELECT' || el.type === 'checkbox') ? 'change' : 'input';
            el.addEventListener(evt, updateCurllmPreview);
        }
    });
    // Initial render
    updateCurllmPreview();
    // Forms listeners
    const formIds = [
        'forms-url-input',
        'visual-mode-forms','stealth-mode-forms','captcha-solver-forms',
        'bql-mode-forms','verbose-mode-forms','headful-mode-forms',
        'session-id-forms','proxy-input-forms'
    ];
    formIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            const evt = (el.tagName === 'SELECT' || el.type === 'checkbox') ? 'change' : 'input';
            el.addEventListener(evt, updateCurllmFormsPreview);
        }
    });
    // Inputs inside form fields container
    document.getElementById('form-fields-container')?.addEventListener('input', updateCurllmFormsPreview);
    updateCurllmFormsPreview();

    // Init tab from URL and handle back/forward
    try {
        const initialTab = getTabFromUrl();
        switchTab(initialTab, false);
        window.addEventListener('popstate', (e) => {
            const tab = (e.state && e.state.tab) ? e.state.tab : getTabFromUrl();
            switchTab(tab, false);
        });
    } catch (e) { /* no-op */ }
});

// Tab switching
function getTabFromUrl() {
    try {
        const url = new URL(window.location);
        let tab = url.searchParams.get('tab');
        if (!tab) {
            const h = (url.hash || '').replace(/^#/, '');
            if (h.startsWith('tab=')) tab = h.split('=')[1];
            else if (h) tab = h;
        }
        const allowed = ['execute','logs','prompts','forms'];
        return allowed.includes(tab) ? tab : 'execute';
    } catch (e) { return 'execute'; }
}

function switchTab(tabName, pushUrl = true) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('[id^="tab-"]').forEach(el => {
        el.classList.remove('tab-active', 'text-blue-600', 'border-blue-500');
        el.classList.add('text-gray-500');
    });
    
    // Show selected tab
    document.getElementById(`content-${tabName}`).classList.remove('hidden');
    const tabBtn = document.getElementById(`tab-${tabName}`);
    tabBtn.classList.add('tab-active', 'text-blue-600', 'border-blue-500');
    tabBtn.classList.remove('text-gray-500');
    
    // Load data for specific tabs
    if (tabName === 'logs') {
        loadLogs();
    } else if (tabName === 'prompts') {
        loadPromptsManager();
    }

    // Update URL
    if (pushUrl) {
        try {
            const url = new URL(window.location);
            url.searchParams.set('tab', tabName);
            history.pushState({ tab: tabName }, '', url);
        } catch (e) {
            try { window.location.hash = 'tab=' + tabName; } catch (_) {}
        }
    }
}

// =========================
// CLI Preview (curllm)
// =========================
function bashQuoteSingle(s) {
    if (s == null) return "''";
    s = String(s);
    if (s === '') return "''";
    return "'" + s.replace(/'/g, "'\"'\"'") + "'";
}

function buildCurllmCommand() {
    const url = document.getElementById('url-input')?.value.trim() || '';
    const instr = document.getElementById('prompt-text')?.value.trim() || '';
    const visual = document.getElementById('visual-mode')?.checked;
    const stealth = document.getElementById('stealth-mode')?.checked;
    const captcha = document.getElementById('captcha-solver')?.checked;
    const bql = document.getElementById('bql-mode')?.checked;
    const verbose = document.getElementById('verbose-mode')?.checked;
    const headful = document.getElementById('headful-mode')?.checked;
    const session = document.getElementById('session-id')?.value.trim();
    const proxy = document.getElementById('proxy-input')?.value.trim();

    const parts = [];
    if (headful) parts.push('CURLLM_HEADLESS=false');
    parts.push('curllm');
    if (verbose) parts.push('-v');
    if (visual) parts.push('--visual');
    if (stealth) parts.push('--stealth');
    if (captcha) parts.push('--captcha');
    if (bql) parts.push('--bql');
    if (proxy) { parts.push('--proxy'); parts.push(bashQuoteSingle(proxy)); }
    if (session) { parts.push('--session'); parts.push(bashQuoteSingle(session)); }
    if (instr) { parts.push('-d'); parts.push(bashQuoteSingle(instr)); }
    if (url) { parts.push(bashQuoteSingle(url)); }
    return parts.join(' ');
}

function updateCurllmPreview() {
    const pre = document.getElementById('curllm-preview');
    if (!pre) return;
    pre.textContent = buildCurllmCommand();
}

function copyCurllmPreview() {
    const pre = document.getElementById('curllm-preview');
    if (!pre) return;
    const txt = pre.textContent || '';
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(() => {
            showNotification('Komenda skopiowana', 'success');
        }).catch(() => { fallbackCopyText(txt); });
    } else {
        fallbackCopyText(txt);
    }
}

// Health check
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        const indicator = document.getElementById('status-indicator');
        if (data.status === 'ok') {
            indicator.innerHTML = `
                <span class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
                <span class="text-sm text-gray-600">Ready</span>
            `;
        }
    } catch (error) {
        const indicator = document.getElementById('status-indicator');
        indicator.innerHTML = `
            <span class="w-3 h-3 bg-red-500 rounded-full"></span>
            <span class="text-sm text-red-600">Offline</span>
        `;
    }
}

// Load prompts
async function loadPrompts() {
    try {
        const response = await fetch('/api/prompts');
        const data = await response.json();
        prompts = data.prompts;
        
        const select = document.getElementById('prompt-select');
        select.innerHTML = prompts.map(p => 
            `<option value="${p.id}">${p.name}</option>`
        ).join('');
        
        // Set first prompt
        if (prompts.length > 0) {
            updatePromptText();
        }
    } catch (error) {
        console.error('Error loading prompts:', error);
        showNotification('Błąd ładowania promptów', 'error');
    }
}

// Update prompt text when selection changes
function updatePromptText() {
    const select = document.getElementById('prompt-select');
    const textarea = document.getElementById('prompt-text');
    const selectedId = select.value;
    
    const prompt = prompts.find(p => p.id === selectedId);
    if (prompt) {
        textarea.value = prompt.prompt;
        // Enable editing for custom prompts
        textarea.disabled = false;
    }
    updateCurllmPreview();
}

// Execute task
async function executeTask() {
    const url = document.getElementById('url-input').value.trim();
    const instruction = document.getElementById('prompt-text').value.trim();
    
    if (!url) {
        showNotification('Proszę podać URL', 'error');
        return;
    }
    
    if (!instruction) {
        showNotification('Proszę podać instrukcję', 'error');
        return;
    }
    
    const options = {
        visual_mode: document.getElementById('visual-mode').checked,
        stealth_mode: document.getElementById('stealth-mode').checked,
        captcha_solver: document.getElementById('captcha-solver').checked,
        export_format: document.getElementById('export-format').value,
        use_bql: document.getElementById('bql-mode') ? document.getElementById('bql-mode').checked : false
    };
    
    const btn = document.getElementById('execute-btn');
    const resultsContainer = document.getElementById('results-container');
    
    // Show loading
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner mx-auto"></div>';
    resultsContainer.innerHTML = `
        <div class="text-center py-12">
            <div class="spinner mx-auto mb-4"></div>
            <p class="text-gray-600">Wykonywanie zadania...</p>
            <p class="text-sm text-gray-400 mt-2">To może potrwać kilka minut</p>
        </div>
    `;
    
    try {
        const response = await fetch('/api/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                instruction: instruction,
                options: options
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            resultsContainer.innerHTML = `
                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 class="text-red-800 font-medium mb-2">
                        <i class="fas fa-exclamation-circle mr-2"></i>Błąd
                    </h4>
                    <p class="text-red-700 mb-2">${escapeHtml(data.error)}</p>
                    ${data.help ? `
                        <div class="bg-yellow-50 border border-yellow-300 rounded p-3 mt-3">
                            <p class="text-yellow-800 text-sm">
                                <i class="fas fa-lightbulb mr-2"></i><strong>Pomoc:</strong> ${escapeHtml(data.help)}
                            </p>
                        </div>
                    ` : ''}
                    ${data.details ? `
                        <details class="mt-3">
                            <summary class="text-red-600 text-sm cursor-pointer hover:underline">Szczegóły techniczne</summary>
                            <pre class="mt-2 text-xs text-red-600 overflow-x-auto bg-red-100 p-2 rounded">${escapeHtml(data.details)}</pre>
                        </details>
                    ` : ''}
                </div>
            `;
        } else {
            displayResults(data);
            showNotification('Zadanie wykonane pomyślnie', 'success');
        }
    } catch (error) {
        console.error('Error executing task:', error);
        resultsContainer.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <h4 class="text-red-800 font-medium mb-2">
                    <i class="fas fa-exclamation-circle mr-2"></i>Błąd połączenia
                </h4>
                <p class="text-red-700">${escapeHtml(error.message)}</p>
            </div>
        `;
        showNotification('Błąd wykonania zadania', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play mr-2"></i>Wykonaj zadanie';
    }
}

// Display results
function displayResults(data, containerId = 'results-container') {
    const container = document.getElementById(containerId);
    
    let html = '<div class="space-y-4">';
    
    // Success message
    if (data.success) {
        html += `
            <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                <i class="fas fa-check-circle text-green-600 mr-2"></i>
                <span class="text-green-800 font-medium">Sukces</span>
                ${data.reason ? `<span class="text-green-700 ml-2">- ${escapeHtml(data.reason)}</span>` : ''}
            </div>
        `;
    } else if (data.success === false) {
        html += `
            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <i class="fas fa-exclamation-triangle text-yellow-600 mr-2"></i>
                <span class="text-yellow-800 font-medium">Ostrzeżenie</span>
                ${data.reason ? `<span class="text-yellow-700 ml-2">- ${escapeHtml(data.reason)}</span>` : ''}
            </div>
        `;
    }
    
    // Steps info
    if (data.steps_taken !== undefined) {
        html += `
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <i class="fas fa-list-ol text-blue-600 mr-2"></i>
                <span class="text-blue-800 text-sm">Wykonano ${data.steps_taken} ${data.steps_taken === 1 ? 'krok' : 'kroków'}</span>
            </div>
        `;
    }
    
    // Log file link
    if (data.run_log) {
        const logFilename = data.run_log.split('/').pop();
        html += `
            <div class="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <i class="fas fa-file-alt text-purple-600 mr-2"></i>
                <span class="text-purple-800">Szczegółowy log: </span>
                <button onclick="switchTab('logs'); setTimeout(() => viewLog('${logFilename}'), 100)" class="text-purple-600 underline hover:text-purple-800 font-medium">
                    Otwórz log z obrazami →
                </button>
            </div>
        `;
    }
    
    // Result data
    if (data.result !== undefined && data.result !== null) {
        lastResult = data.result;
        const resultStr = JSON.stringify(data.result, null, 2);
        const resultCount = Array.isArray(data.result) ? data.result.length : 
                           (typeof data.result === 'object' && data.result !== null) ? Object.keys(data.result).length : 1;
        
        html += `
            <div class="border border-gray-200 rounded-lg p-4">
                <h4 class="font-medium text-gray-900 mb-2">
                    <i class="fas fa-database mr-2"></i>Dane wynikowe
                    <span class="text-sm text-gray-500 ml-2">(${resultCount} ${Array.isArray(data.result) ? 'elementów' : 'pól'})</span>
                </h4>
                <pre class="bg-gray-50 p-4 rounded overflow-x-auto text-sm max-h-96">${escapeHtml(resultStr)}</pre>
            </div>
            <div class="border border-gray-200 rounded-lg p-4">
                <h4 class="font-medium text-gray-900 mb-2">
                    <i class="fas fa-file-export mr-2"></i>Eksport
                </h4>
                <div class="flex flex-wrap items-center gap-3 mb-3">
                    <label class="text-sm text-gray-600">Format</label>
                    <select id="export-format-runtime" class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent" onchange="updateExportPreview(this.value)">
                        <option value="json">JSON</option>
                        <option value="csv">CSV</option>
                        <option value="html" selected>HTML</option>
                        <option value="xml">XML</option>
                    </select>
                    <button onclick="downloadExport()" class="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                        <i class="fas fa-download mr-1"></i>Pobierz
                    </button>
                    <button onclick="copyExport()" class="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">
                        <i class="fas fa-copy mr-1"></i>Kopiuj
                    </button>
                </div>
                <div id="export-preview" class="bg-gray-50 p-4 rounded overflow-x-auto text-sm max-h-96"></div>
            </div>
        `;
    } else {
        html += `
            <div class="border border-yellow-200 bg-yellow-50 rounded-lg p-4">
                <h4 class="font-medium text-yellow-800 mb-2">
                    <i class="fas fa-info-circle mr-2"></i>Brak danych
                </h4>
                <p class="text-yellow-700 text-sm">Zadanie wykonane, ale nie zwróciło żadnych danych. Sprawdź log aby zobaczyć szczegóły.</p>
            </div>
        `;
    }
    
    // Screenshots
    if (data.screenshots && data.screenshots.length > 0) {
        html += `
            <div class="border border-gray-200 rounded-lg p-4">
                <h4 class="font-medium text-gray-900 mb-2">
                    <i class="fas fa-images mr-2"></i>Screenshoty (${data.screenshots.length})
                </h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        `;
        data.screenshots.forEach((screenshot, idx) => {
            html += `
                <div>
                    <p class="text-sm text-gray-600 mb-2">Krok ${idx + 1}</p>
                    <img src="/screenshots/${screenshot}" alt="Screenshot ${idx + 1}" class="rounded-lg shadow-md w-full">
                </div>
            `;
        });
        html += `
                </div>
            </div>
        `;
    }
    
    // Evaluation metadata
    if (data.evaluation) {
        html += `
            <details class="border border-gray-200 rounded-lg p-4">
                <summary class="font-medium text-gray-700 cursor-pointer hover:text-gray-900">
                    <i class="fas fa-chart-line mr-2"></i>Szczegóły ewaluacji
                </summary>
                <pre class="mt-2 bg-gray-50 p-3 rounded text-xs overflow-x-auto">${escapeHtml(JSON.stringify(data.evaluation, null, 2))}</pre>
            </details>
        `;
    }
    
    html += '</div>';
    container.innerHTML = html;
    if (containerId === 'results-container' && lastResult !== null) { updateExportPreview('html'); }
}

// Load logs
async function loadLogs() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        
        const logsList = document.getElementById('logs-list');
        
        if (data.logs.length === 0) {
            logsList.innerHTML = `
                <div class="text-center text-gray-400 py-8">
                    <i class="fas fa-inbox text-3xl mb-2"></i>
                    <p>Brak logów</p>
                </div>
            `;
            return;
        }
        
        logsList.innerHTML = data.logs.map(log => `
            <button onclick="viewLog('${log.filename}')" 
                    class="w-full text-left p-3 rounded-lg hover:bg-gray-50 border border-gray-200 transition-colors">
                <div class="font-medium text-sm text-gray-900 truncate">${log.filename}</div>
                <div class="text-xs text-gray-500 mt-1">${log.modified}</div>
                <div class="text-xs text-gray-400">${formatFileSize(log.size)}</div>
            </button>
        `).join('');
    } catch (error) {
        console.error('Error loading logs:', error);
        showNotification('Błąd ładowania logów', 'error');
    }
}

// View specific log
async function viewLog(filename) {
    currentLogFile = filename;
    
    const viewer = document.getElementById('log-viewer');
    viewer.innerHTML = `
        <div class="text-center py-8">
            <div class="spinner mx-auto mb-4"></div>
            <p class="text-gray-600">Ładowanie logu...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/logs/${filename}`);
        const data = await response.json();
        
        if (data.success) {
            // Convert markdown to HTML
            let html = marked.parse(data.content);
            
            // Fix image paths to use absolute URLs
            html = html.replace(/src="([^"]+\.png)"/g, (match, path) => {
                if (!path.startsWith('http') && !path.startsWith('/')) {
                    return `src="/screenshots/${path}"`;
                }
                return match;
            });
            
            viewer.innerHTML = html;
        } else {
            viewer.innerHTML = `
                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <i class="fas fa-exclamation-circle text-red-600 mr-2"></i>
                    <span class="text-red-800">Błąd ładowania logu</span>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error viewing log:', error);
        viewer.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <i class="fas fa-exclamation-circle text-red-600 mr-2"></i>
                <span class="text-red-800">Błąd: ${escapeHtml(error.message)}</span>
            </div>
        `;
    }
}

// Load prompts manager
async function loadPromptsManager() {
    try {
        const response = await fetch('/api/prompts');
        const data = await response.json();
        prompts = data.prompts;
        
        const list = document.getElementById('prompts-list');
        list.innerHTML = prompts.map(prompt => `
            <div class="border border-gray-200 rounded-lg p-4">
                <div class="flex justify-between items-start mb-2">
                    <input type="text" value="${escapeHtml(prompt.name)}" 
                           id="prompt-name-${prompt.id}"
                           class="font-medium text-gray-900 border-b border-transparent hover:border-gray-300 focus:border-blue-500 outline-none px-2 py-1">
                    <div class="flex space-x-2">
                        <button onclick="savePrompt('${prompt.id}')" 
                                class="text-blue-600 hover:text-blue-800">
                            <i class="fas fa-save"></i>
                        </button>
                        <button onclick="deletePrompt('${prompt.id}')" 
                                class="text-red-600 hover:text-red-800">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <textarea id="prompt-content-${prompt.id}" rows="3"
                          class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >${escapeHtml(prompt.prompt)}</textarea>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading prompts manager:', error);
        showNotification('Błąd ładowania promptów', 'error');
    }
}

// Add new prompt
async function addNewPrompt() {
    const name = prompt('Nazwa nowego promptu:');
    if (!name) return;
    
    try {
        const response = await fetch('/api/prompts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                prompt: ''
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Prompt dodany', 'success');
            loadPromptsManager();
            loadPrompts();
        }
    } catch (error) {
        console.error('Error adding prompt:', error);
        showNotification('Błąd dodawania promptu', 'error');
    }
}

// Save prompt
async function savePrompt(promptId) {
    const name = document.getElementById(`prompt-name-${promptId}`).value;
    const content = document.getElementById(`prompt-content-${promptId}`).value;
    
    try {
        const response = await fetch(`/api/prompts/${promptId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                prompt: content
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Prompt zapisany', 'success');
            loadPrompts();
        }
    } catch (error) {
        console.error('Error saving prompt:', error);
        showNotification('Błąd zapisywania promptu', 'error');
    }
}

// Delete prompt
async function deletePrompt(promptId) {
    if (!confirm('Czy na pewno chcesz usunąć ten prompt?')) return;
    
    try {
        const response = await fetch(`/api/prompts/${promptId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Prompt usunięty', 'success');
            loadPromptsManager();
            loadPrompts();
        }
    } catch (error) {
        console.error('Error deleting prompt:', error);
        showNotification('Błąd usuwania promptu', 'error');
    }
}

// Upload file
async function uploadFile() {
    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];
    
    if (!file) {
        showNotification('Proszę wybrać plik', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin text-blue-600"></i> Przesyłanie...';
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusDiv.innerHTML = `
                <i class="fas fa-check-circle text-green-600"></i>
                <span class="text-green-700">Plik przesłany: ${data.filename}</span>
            `;
            showNotification('Plik przesłany pomyślnie', 'success');
        } else {
            statusDiv.innerHTML = `
                <i class="fas fa-exclamation-circle text-red-600"></i>
                <span class="text-red-700">${data.error}</span>
            `;
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        statusDiv.innerHTML = `
            <i class="fas fa-exclamation-circle text-red-600"></i>
            <span class="text-red-700">Błąd przesyłania</span>
        `;
        showNotification('Błąd przesyłania pliku', 'error');
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showNotification(message, type = 'info') {
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500'
    };
    
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function getExportFormatSelection() {
    const el = document.getElementById('export-format-runtime');
    return el ? el.value : 'html';
}

function getExportData(format) {
    if (lastResult === null || lastResult === undefined) return '';
    if (format === 'json') return JSON.stringify(lastResult, null, 2);
    if (format === 'csv') return toCSV(lastResult);
    if (format === 'html') return toHTML(lastResult);
    if (format === 'xml') return toXML(lastResult);
    return JSON.stringify(lastResult, null, 2);
}

function updateExportPreview(format) {
    const preview = document.getElementById('export-preview');
    if (!preview) return;
    const content = getExportData(format);
    if (format === 'html') {
        preview.innerHTML = content;
    } else {
        preview.textContent = content;
    }
}

function downloadExport() {
    const format = getExportFormatSelection();
    let data = getExportData(format);
    let mime = 'text/plain';
    let filename = 'curllm_result.' + format;
    if (format === 'json') mime = 'application/json';
    if (format === 'csv') mime = 'text/csv';
    if (format === 'xml') mime = 'application/xml';
    if (format === 'html') { mime = 'text/html'; data = generateHTMLDocument(data); }
    const blob = new Blob([data], { type: mime + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 0);
    showNotification('Plik zapisany: ' + filename, 'success');
}

function copyExport() {
    const format = getExportFormatSelection();
    const data = getExportData(format);
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(data).then(() => {
            showNotification('Skopiowano do schowka', 'success');
        }).catch(() => { fallbackCopyText(data); });
    } else {
        fallbackCopyText(data);
    }
}

function fallbackCopyText(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); showNotification('Skopiowano do schowka', 'success'); }
    catch (e) { showNotification('Nie udało się skopiować', 'error'); }
    finally { document.body.removeChild(ta); }
}

function toCSV(value) {
    const rows = [];
    function esc(v) {
        if (v === null || v === undefined) return '';
        let s = typeof v === 'string' ? v : JSON.stringify(v);
        s = s.replace(/"/g, '""');
        return /[",\n]/.test(s) ? '"' + s + '"' : s;
    }
    if (Array.isArray(value)) {
        if (value.length === 0) return '';
        const first = value[0];
        if (typeof first === 'object' && first !== null) {
            const headersSet = new Set();
            value.forEach(item => { if (item && typeof item === 'object') { Object.keys(item).forEach(k => headersSet.add(k)); } });
            const headers = Array.from(headersSet);
            rows.push(headers.join(','));
            value.forEach(item => {
                const row = headers.map(k => esc(item ? item[k] : ''));
                rows.push(row.join(','));
            });
        } else {
            rows.push('value');
            value.forEach(v => rows.push(esc(v)));
        }
    } else if (typeof value === 'object' && value !== null) {
        rows.push('key,value');
        Object.keys(value).forEach(k => { rows.push(esc(k) + ',' + esc(value[k])); });
    } else {
        rows.push('value');
        rows.push(esc(value));
    }
    return rows.join('\n');
}

function formatCell(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
}

function toHTML(value) {
    if (Array.isArray(value)) {
        if (value.length === 0) return '<div class="text-gray-500">Brak danych</div>';
        const first = value[0];
        if (typeof first === 'object' && first !== null) {
            const headersSet = new Set();
            value.forEach(item => { if (item && typeof item === 'object') { Object.keys(item).forEach(k => headersSet.add(k)); } });
            const headers = Array.from(headersSet);
            let h = '<div class="overflow-x-auto"><table class="min-w-full text-sm"><thead><tr>';
            headers.forEach(k => { h += '<th class="px-3 py-2 text-left border-b">' + escapeHtml(String(k)) + '</th>'; });
            h += '</tr></thead><tbody>';
            value.forEach(item => {
                h += '<tr>';
                headers.forEach(k => { const cell = item ? item[k] : ''; h += '<td class="px-3 py-2 border-b align-top">' + escapeHtml(formatCell(cell)) + '</td>'; });
                h += '</tr>';
            });
            h += '</tbody></table></div>';
            return h;
        } else {
            let h = '<ul class="list-disc pl-6">';
            value.forEach(v => { h += '<li>' + escapeHtml(formatCell(v)) + '</li>'; });
            h += '</ul>';
            return h;
        }
    } else if (typeof value === 'object' && value !== null) {
        let h = '<div class="overflow-x-auto"><table class="min-w-full text-sm"><tbody>';
        Object.keys(value).forEach(k => { h += '<tr><th class="px-3 py-2 text-left border-b align-top">' + escapeHtml(String(k)) + '</th><td class="px-3 py-2 border-b align-top">' + escapeHtml(formatCell(value[k])) + '</td></tr>'; });
        h += '</tbody></table></div>';
        return h;
    } else {
        return '<pre class="bg-gray-50 p-3 rounded">' + escapeHtml(formatCell(value)) + '</pre>';
    }
}

function toXML(value) {
    function escTag(t) { return String(t).replace(/[^a-zA-Z0-9_-]/g, '_'); }
    function escText(t) { if (t === null || t === undefined) return ''; return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function build(val, name) {
        if (Array.isArray(val)) {
            let s = '<' + name + '>';
            val.forEach(item => { s += build(item, 'item'); });
            s += '</' + name + '>';
            return s;
        } else if (typeof val === 'object' && val !== null) {
            let s = '<' + name + '>';
            Object.keys(val).forEach(k => { s += build(val[k], escTag(k)); });
            s += '</' + name + '>';
            return s;
        } else {
            return '<' + name + '>' + escText(val) + '</' + name + '>';
        }
    }
    return '<?xml version="1.0" encoding="UTF-8"?>' + build(value, 'result');
}

function generateHTMLDocument(content) {
    return '<!DOCTYPE html><html><head><meta charset="utf-8"><title>curllm result</title><style>table{border-collapse:collapse}th,td{border:1px solid #ddd;padding:6px}th{background:#f7fafc;text-align:left}</style></head><body>' + content + '</body></html>';
}

// =========================
// Forms tab helpers
// =========================
function addFormFieldRow() {
    const cont = document.getElementById('form-fields-container');
    if (!cont) return;
    const row = document.createElement('div');
    row.className = 'grid grid-cols-1 md:grid-cols-2 gap-2';
    row.setAttribute('data-row','form-field');
    row.innerHTML = `
        <input type="text" class="px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="field">
        <input type="text" class="px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="value">
    `;
    cont.appendChild(row);
    updateCurllmFormsPreview();
}

function collectFormFields() {
    const out = [];
    document.querySelectorAll('#form-fields-container [data-row="form-field"]').forEach(row => {
        const inputs = row.querySelectorAll('input');
        if (inputs.length >= 2) {
            const k = (inputs[0].value || '').trim();
            const v = (inputs[1].value || '').trim();
            if (k) out.push({name: k, value: v});
        }
    });
    return out;
}

function buildFormInstruction(fields) {
    if (!fields || fields.length === 0) return 'Fill the form on this page and submit it.';
    const parts = fields.map(f => `${f.name}="${f.value.replace(/"/g,'\\"')}"`);
    return `Fill the form on this page with the following values: ${parts.join(', ')}. Then submit the form and report status.`;
}

function buildCurllmFormsCommand() {
    const url = document.getElementById('forms-url-input')?.value.trim() || '';
    const fields = collectFormFields();
    const instr = buildFormInstruction(fields);
    const visual = document.getElementById('visual-mode-forms')?.checked;
    const stealth = document.getElementById('stealth-mode-forms')?.checked;
    const captcha = document.getElementById('captcha-solver-forms')?.checked;
    const bql = document.getElementById('bql-mode-forms')?.checked;
    const verbose = document.getElementById('verbose-mode-forms')?.checked;
    const headful = document.getElementById('headful-mode-forms')?.checked;
    const session = document.getElementById('session-id-forms')?.value.trim();
    const proxy = document.getElementById('proxy-input-forms')?.value.trim();

    const parts = [];
    if (headful) parts.push('CURLLM_HEADLESS=false');
    parts.push('curllm');
    if (verbose) parts.push('-v');
    if (visual) parts.push('--visual');
    if (stealth) parts.push('--stealth');
    if (captcha) parts.push('--captcha');
    if (bql) parts.push('--bql');
    if (proxy) { parts.push('--proxy'); parts.push(bashQuoteSingle(proxy)); }
    if (session) { parts.push('--session'); parts.push(bashQuoteSingle(session)); }
    if (instr) { parts.push('-d'); parts.push(bashQuoteSingle(instr)); }
    if (url) { parts.push(bashQuoteSingle(url)); }
    return parts.join(' ');
}

function updateCurllmFormsPreview() {
    const pre = document.getElementById('curllm-preview-forms');
    if (!pre) return;
    pre.textContent = buildCurllmFormsCommand();
}

function copyCurllmFormsPreview() {
    const pre = document.getElementById('curllm-preview-forms');
    if (!pre) return;
    const txt = pre.textContent || '';
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(() => {
            showNotification('Komenda skopiowana', 'success');
        }).catch(() => { fallbackCopyText(txt); });
    } else {
        fallbackCopyText(txt);
    }
}

async function executeFormTask() {
    const url = document.getElementById('forms-url-input')?.value.trim();
    if (!url) { showNotification('Proszę podać URL', 'error'); return; }
    const fields = collectFormFields();
    const instruction = buildFormInstruction(fields);
    const options = {
        visual_mode: document.getElementById('visual-mode-forms')?.checked || false,
        stealth_mode: document.getElementById('stealth-mode-forms')?.checked || false,
        captcha_solver: document.getElementById('captcha-solver-forms')?.checked || false,
        export_format: 'json',
        use_bql: document.getElementById('bql-mode-forms')?.checked || false
    };
    const btn = document.getElementById('execute-form-btn');
    const container = document.getElementById('forms-results-container');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner mx-auto"></div>';
    container.innerHTML = `
        <div class="text-center py-12">
            <div class="spinner mx-auto mb-4"></div>
            <p class="text-gray-600">Wypełnianie formularza...</p>
        </div>`;
    try {
        const response = await fetch('/api/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, instruction, options })
        });
        const data = await response.json();
        if (data.error) {
            container.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-lg p-4"><h4 class="text-red-800 font-medium mb-2"><i class=\"fas fa-exclamation-circle mr-2\"></i>Błąd</h4><p class="text-red-700 mb-2">${escapeHtml(data.error)}</p></div>`;
        } else {
            displayResults(data, 'forms-results-container');
            showNotification('Formularz wypełniony', 'success');
        }
    } catch (e) {
        container.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-lg p-4"><h4 class="text-red-800 font-medium mb-2"><i class=\"fas fa-exclamation-circle mr-2\"></i>Błąd</h4><p class="text-red-700 mb-2">${escapeHtml(e.message)}</p></div>`;
        showNotification('Błąd wypełniania formularza', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play mr-2"></i>Wypełnij formularz';
    }
}
