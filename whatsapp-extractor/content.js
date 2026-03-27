whatsapp // WhatsApp Web Number Extractor - Content Script

let extractedNumbers = [];
let isExtracting = false;

function normalizePhone(phone) {
  let cleaned = phone.replace(/[\s\-\(\)]/g, '');
  if (cleaned.startsWith('+964')) {
    cleaned = '0' + cleaned.substring(4);
  } else if (cleaned.startsWith('964')) {
    cleaned = '0' + cleaned.substring(3);
  }
  return cleaned;
}

function isValidPhone(phone) {
  const normalized = normalizePhone(phone);
  return /^0[67]\d{9}$/.test(normalized);
}

function extractPhonesFromText(text) {
  const phones = [];
  const patterns = [
    /\+964[67]\d{9}/g,
    /07\d{9}/g,
    /01\d{9}/g,
    /964[67]\d{9}/g
  ];
  
  patterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const normalized = normalizePhone(match[0]);
      if (isValidPhone(match[0])) {
        phones.push(normalized);
      }
    }
  });
  
  return phones;
}

function addNumber(phone, name = '') {
  const normalized = normalizePhone(phone);
  if (!isValidPhone(phone)) return;
  
  const exists = extractedNumbers.find(n => n.phone === normalized);
  if (!exists) {
    extractedNumbers.push({ phone: normalized, name: name || '' });
  }
}

// Extract from chat list
async function extractFromChatList() {
  const chatSelectors = [
    'div[data-testid="chat-list"] span[class*="two-line-ellipsis"]',
    'div[data-testid="chat-list"] div[title]',
    'div[data-testid="conversation-panel-messagelist"] span[class*="ellipsis"]',
    'div[role="listitem"] span[class*="title"]'
  ];
  
  for (const selector of chatSelectors) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
      const text = el.textContent.trim();
      if (text) {
        // Check if text itself is a phone number
        const phones = extractPhonesFromText(text);
        phones.forEach(p => addNumber(p, ''));
        
        // Also check if it's a regular name
        if (!phones.length && text.length > 2 && !text.includes('@')) {
          // Could be a name - leave blank
        }
      }
    });
  }
  
  // Try to get names with phones
  const chatItems = document.querySelectorAll('div[data-testid="chat-list-item"]');
  chatItems.forEach(item => {
    const titleEl = item.querySelector('span[title]');
    const subtitleEl = item.querySelector('span[class*="subtitle"]');
    
    if (titleEl && subtitleEl) {
      const title = titleEl.textContent.trim();
      const subtitle = subtitleEl.textContent.trim();
      
      const phones = extractPhonesFromText(subtitle);
      phones.forEach(p => addNumber(p, title));
    }
  });
}

// Extract from contacts
async function extractFromContacts() {
  // Find contact items
  const contactSelectors = [
    'div[data-testid="contact-list-item"]',
    'div[role="listitem"]',
    'div[class*="contact"]'
  ];
  
  for (const selector of contactSelectors) {
    const items = document.querySelectorAll(selector);
    items.forEach(item => {
      const text = item.textContent;
      const phones = extractPhonesFromText(text);
      phones.forEach(p => addNumber(p, ''));
    });
  }
}

// Extract from messages in current chat
async function extractFromMessages() {
  const messages = document.querySelectorAll('div[class*="message"]');
  const panelHeader = document.querySelector('header span[title]');
  const chatName = panelHeader ? panelHeader.textContent.trim() : '';
  
  messages.forEach(msg => {
    const text = msg.textContent;
    const phones = extractPhonesFromText(text);
    phones.forEach(p => addNumber(p, chatName));
  });
}

// Scroll functions
async function scrollAndLoad(element, maxScrolls = 50) {
  for (let i = 0; i < maxScrolls; i++) {
    const prevScrollTop = element.scrollTop;
    element.scrollTop = element.scrollHeight;
    await new Promise(r => setTimeout(r, 500));
    
    if (element.scrollTop === prevScrollTop) break;
  }
}

// Main extraction function
async function startExtraction(options) {
  if (isExtracting) return;
  
  isExtracting = true;
  extractedNumbers = [];
  
  try {
    if (options.chatList) {
      // Find chat list sidebar
      const sidebars = document.querySelectorAll('div[data-testid="chat-list"], aside div');
      for (const sidebar of sidebars) {
        if (sidebar.offsetHeight > 200) {
          await scrollAndLoad(sidebar, 30);
        }
      }
      extractFromChatList();
    }
    
    if (options.contacts) {
      // Look for contacts section
      const contactLists = document.querySelectorAll('div[data-testid*="contact"]');
      for (const list of contactLists) {
        await scrollAndLoad(list, 20);
      }
      extractFromContacts();
    }
    
    if (options.messages) {
      // Get messages from main chat area
      const messageContainers = document.querySelectorAll('div[data-testid="conversation-panel-messages"]');
      for (const container of messageContainers) {
        await scrollAndLoad(container, 100);
      }
      extractFromMessages();
    }
    
  } catch (err) {
    console.error('Extraction error:', err);
  }
  
  isExtracting = false;
  return extractedNumbers;
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'startExtraction') {
    startExtraction(request.options || { chatList: true, contacts: true, messages: false })
      .then(numbers => {
        sendResponse({ success: true, numbers: numbers });
      })
      .catch(err => {
        sendResponse({ success: false, error: err.message });
      });
    return true; // Keep channel open for async response
  }
});
