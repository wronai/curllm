/**
 * Safety Utilities for DOM Processing (JavaScript)
 * 
 * Provides error handling, sanitization, and fallback mechanisms.
 */

/**
 * Safely call a function, returning default on error
 * @param {Function} fn - Function to call
 * @param {*} defaultValue - Default value on error
 * @param {...*} args - Arguments for function
 * @returns {*} Function result or default
 */
function safeCall(fn, defaultValue = null, ...args) {
    try {
        return fn(...args);
    } catch (e) {
        console.debug(`safeCall error: ${e.message}`);
        return defaultValue;
    }
}

/**
 * Safely get element property
 * @param {Element} element - DOM element
 * @param {string} property - Property path (e.g., 'textContent', 'dataset.id')
 * @param {*} defaultValue - Default if not found
 * @returns {*} Property value or default
 */
function safeGet(element, property, defaultValue = null) {
    try {
        if (!element) return defaultValue;
        
        const parts = property.split('.');
        let value = element;
        
        for (const part of parts) {
            if (value === null || value === undefined) {
                return defaultValue;
            }
            value = value[part];
        }
        
        return value ?? defaultValue;
    } catch (e) {
        return defaultValue;
    }
}

/**
 * Safely get text content from element
 * @param {Element} element - DOM element
 * @param {string} defaultValue - Default if not found
 * @returns {string} Text content
 */
function safeText(element, defaultValue = '') {
    try {
        if (!element) return defaultValue;
        const text = element.textContent || element.innerText || '';
        return text.trim() || defaultValue;
    } catch (e) {
        return defaultValue;
    }
}

/**
 * Safely query selector
 * @param {Element|Document} root - Root element
 * @param {string} selector - CSS selector
 * @returns {Element|null} Found element or null
 */
function safeQuery(root, selector) {
    try {
        if (!root || !selector) return null;
        return root.querySelector(selector);
    } catch (e) {
        console.debug(`safeQuery error for "${selector}": ${e.message}`);
        return null;
    }
}

/**
 * Safely query all elements
 * @param {Element|Document} root - Root element
 * @param {string} selector - CSS selector
 * @returns {Element[]} Found elements (never null)
 */
function safeQueryAll(root, selector) {
    try {
        if (!root || !selector) return [];
        return Array.from(root.querySelectorAll(selector));
    } catch (e) {
        console.debug(`safeQueryAll error for "${selector}": ${e.message}`);
        return [];
    }
}

/**
 * Sanitize text - remove control chars, normalize whitespace
 * @param {*} text - Input text
 * @param {number} maxLength - Maximum length
 * @returns {string} Sanitized text
 */
function sanitizeText(text, maxLength = 10000) {
    if (text === null || text === undefined) return '';
    
    let str = String(text);
    
    // Remove control characters
    str = str.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '');
    
    // Normalize unicode whitespace
    str = str.replace(/[\u00a0\u200b\u200c\u200d\ufeff]/g, ' ');
    
    // Normalize whitespace
    str = str.replace(/\s+/g, ' ').trim();
    
    // Truncate
    if (str.length > maxLength) {
        str = str.substring(0, maxLength);
    }
    
    return str;
}

/**
 * Strip HTML tags from text
 * @param {string} html - HTML string
 * @returns {string} Text without tags
 */
function stripHtml(html) {
    if (!html) return '';
    
    try {
        // Create temporary element
        const div = document.createElement('div');
        div.innerHTML = html;
        return div.textContent || div.innerText || '';
    } catch (e) {
        // Fallback to regex
        return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    }
}

/**
 * Execute functions with fallback
 * @param {Function[]} functions - Array of functions to try
 * @param {...*} args - Arguments for functions
 * @returns {{success: boolean, value: *, usedIndex: number}} Result
 */
function withFallback(functions, ...args) {
    for (let i = 0; i < functions.length; i++) {
        try {
            const result = functions[i](...args);
            if (result !== null && result !== undefined) {
                return { success: true, value: result, usedIndex: i };
            }
        } catch (e) {
            console.debug(`Fallback ${i} failed: ${e.message}`);
        }
    }
    return { success: false, value: null, usedIndex: -1 };
}

/**
 * Validate input value
 */
class InputValidator {
    constructor(value) {
        this._value = value;
        this._valid = true;
        this._errors = [];
    }
    
    notNull(msg = 'Value cannot be null') {
        if (this._value === null || this._value === undefined) {
            this._valid = false;
            this._errors.push(msg);
        }
        return this;
    }
    
    isString(msg = 'Value must be a string') {
        if (this._value !== null && typeof this._value !== 'string') {
            this._valid = false;
            this._errors.push(msg);
        }
        return this;
    }
    
    notEmpty(msg = 'Value cannot be empty') {
        if (typeof this._value === 'string' && !this._value.trim()) {
            this._valid = false;
            this._errors.push(msg);
        }
        return this;
    }
    
    minLength(len, msg = null) {
        if (typeof this._value === 'string' && this._value.length < len) {
            this._valid = false;
            this._errors.push(msg || `Value must be at least ${len} characters`);
        }
        return this;
    }
    
    maxLength(len) {
        if (typeof this._value === 'string' && this._value.length > len) {
            this._value = this._value.substring(0, len);
        }
        return this;
    }
    
    matches(pattern, msg = 'Value does not match pattern') {
        if (typeof this._value === 'string' && !pattern.test(this._value)) {
            this._valid = false;
            this._errors.push(msg);
        }
        return this;
    }
    
    transform(fn) {
        try {
            this._value = fn(this._value);
        } catch (e) {
            console.debug(`Transform error: ${e.message}`);
        }
        return this;
    }
    
    default(defaultValue) {
        if (!this._valid || this._value === null || this._value === undefined) {
            this._value = defaultValue;
            this._valid = true;
            this._errors = [];
        }
        return this;
    }
    
    result() {
        return {
            valid: this._valid,
            value: this._value,
            errors: this._errors
        };
    }
    
    get isValid() { return this._valid; }
    get value() { return this._value; }
}

/**
 * Validate input value
 * @param {*} value - Value to validate
 * @returns {InputValidator} Validator chain
 */
function validate(value) {
    return new InputValidator(value);
}

/**
 * Circuit breaker for repeated failures
 */
class CircuitBreaker {
    constructor(maxFailures = 5, resetTimeoutMs = 60000) {
        this.maxFailures = maxFailures;
        this.resetTimeout = resetTimeoutMs;
        this._failures = 0;
        this._lastFailure = null;
        this._state = 'closed';
    }
    
    get isOpen() {
        if (this._state === 'open') {
            if (this._lastFailure && Date.now() - this._lastFailure >= this.resetTimeout) {
                this._state = 'half-open';
                return false;
            }
            return true;
        }
        return false;
    }
    
    recordSuccess() {
        this._failures = 0;
        this._state = 'closed';
    }
    
    recordFailure() {
        this._failures++;
        this._lastFailure = Date.now();
        if (this._failures >= this.maxFailures) {
            this._state = 'open';
            console.warn(`Circuit breaker opened after ${this._failures} failures`);
        }
    }
    
    reset() {
        this._failures = 0;
        this._state = 'closed';
        this._lastFailure = null;
    }
}

// Export for browser
if (typeof window !== 'undefined') {
    window.safeCall = safeCall;
    window.safeGet = safeGet;
    window.safeText = safeText;
    window.safeQuery = safeQuery;
    window.safeQueryAll = safeQueryAll;
    window.sanitizeText = sanitizeText;
    window.stripHtml = stripHtml;
    window.withFallback = withFallback;
    window.validate = validate;
    window.InputValidator = InputValidator;
    window.CircuitBreaker = CircuitBreaker;
}

// Export for Node.js
if (typeof module !== 'undefined') {
    module.exports = {
        safeCall,
        safeGet,
        safeText,
        safeQuery,
        safeQueryAll,
        sanitizeText,
        stripHtml,
        withFallback,
        validate,
        InputValidator,
        CircuitBreaker,
    };
}
