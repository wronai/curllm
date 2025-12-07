/**
 * Atomic Extraction Functions (JavaScript/Browser)
 * 
 * These functions run in the browser context for DOM-based extraction.
 */

// Function registry for JS functions
const FunctionRegistry = {
    functions: {},
    
    register(name, fn, meta = {}) {
        this.functions[name] = { fn, ...meta };
    },
    
    get(name) {
        return this.functions[name]?.fn;
    },
    
    list() {
        return Object.keys(this.functions);
    }
};

/**
 * Extract price from element text
 * @param {Element|string} elementOrText - DOM element or text
 * @returns {number|null} Price as number or null
 */
function extractPrice(elementOrText) {
    const text = typeof elementOrText === 'string' 
        ? elementOrText 
        : elementOrText?.textContent || '';
    
    // Polish price pattern
    const patterns = [
        /(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN|złotych)/i,
        /(\d+[\d\s]*)\s*(?:zł|PLN)/i,
        /€\s*(\d+[\d\s]*[,\.]\d{2})/i,
        /\$\s*(\d+[\d,]*\.?\d*)/i,
    ];
    
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
            let priceStr = match[1];
            // Normalize
            priceStr = priceStr.replace(/\s/g, '').replace(',', '.');
            return parseFloat(priceStr);
        }
    }
    
    return null;
}

FunctionRegistry.register('extractPrice', extractPrice, {
    category: 'extractors',
    description: 'Extract price from element or text'
});

/**
 * Extract product name from element
 * @param {Element} element - DOM element
 * @param {number} maxLength - Maximum length
 * @returns {string|null} Product name or null
 */
function extractProductName(element, maxLength = 200) {
    if (!element) return null;
    
    // Try common selectors
    const selectors = [
        'h1', 'h2', 'h3', 'h4',
        '.product-name', '.product-title', '.item-name',
        '[class*="title"]', '[class*="name"]',
        'a[href]'
    ];
    
    let text = null;
    
    for (const sel of selectors) {
        const el = element.querySelector(sel);
        if (el) {
            text = el.textContent?.trim();
            if (text && text.length > 2) break;
        }
    }
    
    if (!text) {
        text = element.textContent?.trim();
    }
    
    if (!text) return null;
    
    // Clean up
    text = cleanProductName(text);
    
    // Truncate
    if (text.length > maxLength) {
        text = text.substring(0, maxLength).split(' ').slice(0, -1).join(' ');
    }
    
    return text || null;
}

FunctionRegistry.register('extractProductName', extractProductName, {
    category: 'extractors',
    description: 'Extract product name from DOM element'
});

/**
 * Clean product name - remove prices, normalize whitespace
 * @param {string} text - Raw text
 * @returns {string} Cleaned text
 */
function cleanProductName(text) {
    if (!text) return '';
    
    // Remove price patterns
    text = text.replace(/\d+[\d\s]*[,\.]\d{2}\s*(?:zł|PLN|€|EUR|\$|USD)/gi, '');
    text = text.replace(/\d+\s*(?:zł|PLN)/gi, '');
    
    // Remove quantity patterns
    text = text.replace(/\s*[-–]\s*\d+\s*szt\.?/gi, '');
    text = text.replace(/\s*x\s*\d+/gi, '');
    
    // Normalize whitespace
    text = text.replace(/\s+/g, ' ').trim();
    
    return text;
}

FunctionRegistry.register('cleanProductName', cleanProductName, {
    category: 'transformers',
    description: 'Clean product name from text'
});

/**
 * Extract URL from element
 * @param {Element} element - DOM element
 * @returns {string|null} URL or null
 */
function extractUrl(element) {
    if (!element) return null;
    
    // Direct link
    if (element.href) return element.href;
    
    // Find first link
    const link = element.querySelector('a[href]');
    if (link?.href) return link.href;
    
    // Check data attributes
    const dataUrl = element.dataset?.url || element.dataset?.href;
    if (dataUrl) return dataUrl;
    
    return null;
}

FunctionRegistry.register('extractUrl', extractUrl, {
    category: 'extractors',
    description: 'Extract URL from element'
});

/**
 * Extract image URL from element
 * @param {Element} element - DOM element
 * @returns {string|null} Image URL or null
 */
function extractImageUrl(element) {
    if (!element) return null;
    
    // Direct img
    if (element.tagName === 'IMG') {
        return element.src || element.dataset?.src;
    }
    
    // Find img inside
    const img = element.querySelector('img[src], img[data-src]');
    if (img) {
        return img.src || img.dataset?.src;
    }
    
    // Background image
    const style = getComputedStyle(element);
    const bgImage = style.backgroundImage;
    if (bgImage && bgImage !== 'none') {
        const match = bgImage.match(/url\(["']?([^"')]+)["']?\)/);
        if (match) return match[1];
    }
    
    return null;
}

FunctionRegistry.register('extractImageUrl', extractImageUrl, {
    category: 'extractors',
    description: 'Extract image URL from element'
});

/**
 * Check if element looks like a product container
 * @param {Element} element - DOM element
 * @returns {boolean} True if looks like product
 */
function isProductContainer(element) {
    if (!element) return false;
    
    const text = element.textContent || '';
    const className = (element.className || '').toLowerCase();
    
    // Positive signals
    const hasPrice = /\d+[\d\s]*[,\.]\d{2}\s*(?:zł|PLN|€|\$)/i.test(text);
    const hasProductClass = /product|item|card|offer|listing/i.test(className);
    const hasLink = element.querySelector('a[href]') !== null;
    const hasImage = element.querySelector('img') !== null;
    
    // Negative signals
    const isNav = /nav|menu|header|footer|sidebar/i.test(className);
    const tooLong = text.length > 2000;
    const tooShort = text.length < 10;
    
    if (isNav || tooLong || tooShort) return false;
    
    // Score
    let score = 0;
    if (hasPrice) score += 30;
    if (hasProductClass) score += 25;
    if (hasLink) score += 20;
    if (hasImage) score += 15;
    
    return score >= 40;
}

FunctionRegistry.register('isProductContainer', isProductContainer, {
    category: 'validators',
    description: 'Check if element is a product container'
});

/**
 * Extract specifications from a table element
 * @param {Element} table - Table element
 * @returns {Object} Key-value specifications
 */
function extractSpecsFromTable(table) {
    const specs = {};
    if (!table) return specs;
    
    const rows = table.querySelectorAll('tr');
    for (const row of rows) {
        const cells = row.querySelectorAll('td, th');
        if (cells.length >= 2) {
            const key = cells[0].textContent?.trim();
            const value = cells[1].textContent?.trim();
            if (key && value && key.length < 100) {
                specs[key] = value;
            }
        }
    }
    
    return specs;
}

FunctionRegistry.register('extractSpecsFromTable', extractSpecsFromTable, {
    category: 'extractors',
    description: 'Extract specifications from table'
});

/**
 * Extract all product data from element
 * @param {Element} element - Product container element
 * @returns {Object} Product data
 */
function extractProductData(element) {
    if (!element) return null;
    
    const data = {};
    
    // Name
    const name = extractProductName(element);
    if (name) data.name = name;
    
    // Price
    const price = extractPrice(element);
    if (price !== null) data.price = price;
    
    // URL
    const url = extractUrl(element);
    if (url) data.url = url;
    
    // Image
    const image = extractImageUrl(element);
    if (image) data.image = image;
    
    return Object.keys(data).length > 0 ? data : null;
}

FunctionRegistry.register('extractProductData', extractProductData, {
    category: 'extractors',
    description: 'Extract complete product data from element'
});

// Export for use in browser context
if (typeof window !== 'undefined') {
    window.FunctionRegistry = FunctionRegistry;
    window.extractPrice = extractPrice;
    window.extractProductName = extractProductName;
    window.cleanProductName = cleanProductName;
    window.extractUrl = extractUrl;
    window.extractImageUrl = extractImageUrl;
    window.isProductContainer = isProductContainer;
    window.extractSpecsFromTable = extractSpecsFromTable;
    window.extractProductData = extractProductData;
}

// Export for Node.js/testing
if (typeof module !== 'undefined') {
    module.exports = {
        FunctionRegistry,
        extractPrice,
        extractProductName,
        cleanProductName,
        extractUrl,
        extractImageUrl,
        isProductContainer,
        extractSpecsFromTable,
        extractProductData,
    };
}
