openlet extractedNumbers = [];
let isRunning = false;

const statusEl = document.getElementById('status');
const startBtn = document.getElementById('startBtn');
const downloadBtn = document.getElementById('downloadBtn');
const chatListCheck = document.getElementById('chatList');
const contactsCheck = document.getElementById('contacts');
const messagesCheck = document.getElementById('messages');

function updateStatus(text) {
  statusEl.textContent = text;
}

function normalizePhone(phone) {
  // Remove spaces, dashes, parentheses
  let cleaned = phone.replace(/[\s\-\(\)]/g, '');
  
  // Normalize: +964 -> 0
  if (cleaned.startsWith('+964')) {
    cleaned = '0' + cleaned.substring(4);
  } else if (cleaned.startsWith('964')) {
    cleaned = '0' + cleaned.substring(3);
  }
  
  return cleaned;
}

function isValidPhone(phone) {
  const normalized = normalizePhone(phone);
  // Iraqi formats: 07XXXXXXXXX or 01XXXXXXXX
  return /^0[67]\d{9}$/.test(normalized);
}

function extractPhoneNumbers(text) {
  const phones = [];
  // Match various phone patterns
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

async function startExtraction() {
  if (isRunning) return;
  
  isRunning = true;
  extractedNumbers = [];
  startBtn.disabled = true;
  downloadBtn.disabled = true;
  
  const options = {
    chatList: chatListCheck.checked,
    contacts: contactsCheck.checked,
    messages: messagesCheck.checked
  };
  
  updateStatus('Sending extraction request...');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'startExtraction',
      options: options
    });
    
    if (response && response.success) {
      extractedNumbers = response.numbers || [];
      updateStatus(`Found: ${extractedNumbers.length} numbers`);
      downloadBtn.disabled = extractedNumbers.length === 0;
    } else {
      updateStatus('Error: ' + (response?.error || 'Failed'));
    }
  } catch (err) {
    updateStatus('Error: Make sure WhatsApp Web is open');
  }
  
  isRunning = false;
  startBtn.disabled = false;
}

function downloadCSV() {
  if (extractedNumbers.length === 0) return;
  
  let csv = 'phone,name\n';
  
  extractedNumbers.forEach(item => {
    const name = item.name || '';
    csv += `"${item.phone}","${name}"\n`;
  });
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = 'whatsapp_numbers.csv';
  a.click();
  
  URL.revokeObjectURL(url);
  updateStatus(`Downloaded ${extractedNumbers.length} numbers`);
}

startBtn.addEventListener('click', startExtraction);
downloadBtn.addEventListener('click', downloadCSV);
