(function() {
  'use strict';

  // Configuration
  var API_URL = window.AUTHORITY_CHAT_API || '';
  var BRAND_COLOR = '#0ea5e9';
  var BRAND_DARK = '#0284c7';
  var GREETING = 'Hi! I\'m the AI assistant for Authority AI Systems. I help businesses get recommended by ChatGPT, Google AI, and other AI platforms. How can I help you today?';

  // State
  var isOpen = false;
  var sessionId = 'chat-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now();
  var messages = [];
  var isTyping = false;

  // Detect API URL from script src
  var scripts = document.getElementsByTagName('script');
  for (var i = 0; i < scripts.length; i++) {
    if (scripts[i].src && scripts[i].src.indexOf('chatbot-widget.js') !== -1) {
      var src = scripts[i].src;
      API_URL = src.replace('/api/chat/widget.js', '').replace('/static/chatbot-widget.js', '');
      break;
    }
  }
  if (window.AUTHORITY_CHAT_API) {
    API_URL = window.AUTHORITY_CHAT_API;
  }

  // Styles
  var css = '\n' +
    '#aai-chat-widget { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; position: fixed; bottom: 20px; right: 20px; z-index: 999999; }\n' +
    '#aai-chat-toggle { width: 60px; height: 60px; border-radius: 50%; background: ' + BRAND_COLOR + '; border: none; cursor: pointer; box-shadow: 0 4px 20px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; transition: transform 0.2s, background 0.2s; }\n' +
    '#aai-chat-toggle:hover { transform: scale(1.08); background: ' + BRAND_DARK + '; }\n' +
    '#aai-chat-toggle svg { width: 28px; height: 28px; fill: white; }\n' +
    '#aai-chat-window { display: none; position: fixed; bottom: 90px; right: 20px; width: 380px; max-width: calc(100vw - 40px); height: 520px; max-height: calc(100vh - 120px); background: #fff; border-radius: 16px; box-shadow: 0 8px 40px rgba(0,0,0,0.2); overflow: hidden; flex-direction: column; animation: aai-slide-up 0.3s ease; }\n' +
    '#aai-chat-window.aai-open { display: flex; }\n' +
    '@keyframes aai-slide-up { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }\n' +
    '#aai-chat-header { background: linear-gradient(135deg, ' + BRAND_COLOR + ', ' + BRAND_DARK + '); color: white; padding: 16px 20px; display: flex; align-items: center; gap: 12px; }\n' +
    '#aai-chat-header-avatar { width: 40px; height: 40px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }\n' +
    '#aai-chat-header-avatar svg { width: 22px; height: 22px; fill: white; }\n' +
    '#aai-chat-header-info h3 { margin: 0; font-size: 15px; font-weight: 600; }\n' +
    '#aai-chat-header-info p { margin: 2px 0 0; font-size: 12px; opacity: 0.85; }\n' +
    '#aai-chat-close { margin-left: auto; background: none; border: none; color: white; cursor: pointer; font-size: 20px; padding: 4px; opacity: 0.8; }\n' +
    '#aai-chat-close:hover { opacity: 1; }\n' +
    '#aai-chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; background: #f8fafc; }\n' +
    '.aai-msg { max-width: 85%; padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.5; word-wrap: break-word; }\n' +
    '.aai-msg-user { align-self: flex-end; background: ' + BRAND_COLOR + '; color: white; border-bottom-right-radius: 4px; }\n' +
    '.aai-msg-bot { align-self: flex-start; background: white; color: #1e293b; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }\n' +
    '.aai-typing { align-self: flex-start; background: white; padding: 12px 18px; border-radius: 16px; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); display: flex; gap: 4px; }\n' +
    '.aai-typing-dot { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; animation: aai-bounce 1.4s infinite ease-in-out; }\n' +
    '.aai-typing-dot:nth-child(2) { animation-delay: 0.2s; }\n' +
    '.aai-typing-dot:nth-child(3) { animation-delay: 0.4s; }\n' +
    '@keyframes aai-bounce { 0%, 80%, 100% { transform: scale(0.6); } 40% { transform: scale(1); } }\n' +
    '#aai-chat-input-area { padding: 12px 16px; border-top: 1px solid #e2e8f0; background: white; display: flex; gap: 8px; align-items: center; }\n' +
    '#aai-chat-input { flex: 1; border: 1px solid #e2e8f0; border-radius: 24px; padding: 10px 16px; font-size: 14px; outline: none; resize: none; font-family: inherit; max-height: 80px; }\n' +
    '#aai-chat-input:focus { border-color: ' + BRAND_COLOR + '; box-shadow: 0 0 0 2px rgba(14,165,233,0.15); }\n' +
    '#aai-chat-send { width: 38px; height: 38px; border-radius: 50%; background: ' + BRAND_COLOR + '; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: background 0.2s; }\n' +
    '#aai-chat-send:hover { background: ' + BRAND_DARK + '; }\n' +
    '#aai-chat-send:disabled { background: #cbd5e1; cursor: not-allowed; }\n' +
    '#aai-chat-send svg { width: 18px; height: 18px; fill: white; }\n' +
    '#aai-chat-powered { text-align: center; padding: 6px; font-size: 11px; color: #94a3b8; background: white; }\n' +
    '#aai-chat-pulse { position: absolute; top: -2px; right: -2px; width: 16px; height: 16px; background: #22c55e; border-radius: 50%; border: 2px solid white; animation: aai-pulse 2s infinite; }\n' +
    '@keyframes aai-pulse { 0% { box-shadow: 0 0 0 0 rgba(34,197,94,0.5); } 70% { box-shadow: 0 0 0 8px rgba(34,197,94,0); } 100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); } }\n' +
    '@media (max-width: 480px) { #aai-chat-window { width: calc(100vw - 20px); right: 10px; bottom: 80px; height: calc(100vh - 100px); } #aai-chat-widget { bottom: 10px; right: 10px; } }\n';

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  // Build DOM
  var widget = document.createElement('div');
  widget.id = 'aai-chat-widget';
  widget.innerHTML = 
    '<div id="aai-chat-window">' +
      '<div id="aai-chat-header">' +
        '<div id="aai-chat-header-avatar"><svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg></div>' +
        '<div id="aai-chat-header-info"><h3>Authority AI Assistant</h3><p>Online — Usually replies instantly</p></div>' +
        '<button id="aai-chat-close">&times;</button>' +
      '</div>' +
      '<div id="aai-chat-messages"></div>' +
      '<div id="aai-chat-input-area">' +
        '<input id="aai-chat-input" type="text" placeholder="Type your message..." autocomplete="off" />' +
        '<button id="aai-chat-send"><svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>' +
      '</div>' +
      '<div id="aai-chat-powered">Powered by Authority AI Systems</div>' +
    '</div>' +
    '<button id="aai-chat-toggle">' +
      '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>' +
      '<div id="aai-chat-pulse"></div>' +
    '</button>';
  document.body.appendChild(widget);

  var chatWindow = document.getElementById('aai-chat-window');
  var chatMessages = document.getElementById('aai-chat-messages');
  var chatInput = document.getElementById('aai-chat-input');
  var chatSend = document.getElementById('aai-chat-send');
  var chatToggle = document.getElementById('aai-chat-toggle');
  var chatClose = document.getElementById('aai-chat-close');

  function toggleChat() {
    isOpen = !isOpen;
    if (isOpen) {
      chatWindow.classList.add('aai-open');
      chatInput.focus();
      if (messages.length === 0) {
        addMessage('bot', GREETING);
      }
      var pulse = document.getElementById('aai-chat-pulse');
      if (pulse) pulse.style.display = 'none';
    } else {
      chatWindow.classList.remove('aai-open');
    }
  }

  function addMessage(role, text) {
    messages.push({ role: role, content: text });
    var div = document.createElement('div');
    div.className = 'aai-msg aai-msg-' + (role === 'user' ? 'user' : 'bot');
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function showTyping() {
    isTyping = true;
    var div = document.createElement('div');
    div.className = 'aai-typing';
    div.id = 'aai-typing-indicator';
    div.innerHTML = '<div class="aai-typing-dot"></div><div class="aai-typing-dot"></div><div class="aai-typing-dot"></div>';
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function hideTyping() {
    isTyping = false;
    var typing = document.getElementById('aai-typing-indicator');
    if (typing) typing.remove();
  }

  function sendMessage() {
    var text = chatInput.value.trim();
    if (!text || isTyping) return;

    addMessage('user', text);
    chatInput.value = '';
    chatSend.disabled = true;
    showTyping();

    var xhr = new XMLHttpRequest();
    xhr.open('POST', API_URL + '/api/chat', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function() {
      if (xhr.readyState === 4) {
        hideTyping();
        chatSend.disabled = false;
        if (xhr.status === 200) {
          try {
            var data = JSON.parse(xhr.responseText);
            addMessage('bot', data.response);
            if (data.lead_saved) {
              setTimeout(function() {
                addMessage('bot', 'Great news! I\'ve noted your information. Our team will be in touch shortly. In the meantime, would you like to try our free AI Visibility Score scanner?');
              }, 1000);
            }
          } catch (e) {
            addMessage('bot', 'Thanks for your message! Our team will get back to you soon. You can also try our free AI Visibility Score scanner while you wait.');
          }
        } else {
          addMessage('bot', 'I apologize, I\'m having a brief technical issue. Please try again in a moment, or use our free AI Visibility Score scanner to check your business.');
        }
        chatInput.focus();
      }
    };
    xhr.send(JSON.stringify({
      session_id: sessionId,
      message: text
    }));
  }

  // Event listeners
  chatToggle.addEventListener('click', toggleChat);
  chatClose.addEventListener('click', toggleChat);
  chatSend.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-open after 30 seconds if not interacted
  setTimeout(function() {
    if (!isOpen && messages.length === 0) {
      var pulse = document.getElementById('aai-chat-pulse');
      if (pulse) pulse.style.animation = 'aai-pulse 1s infinite';
    }
  }, 30000);

})();
