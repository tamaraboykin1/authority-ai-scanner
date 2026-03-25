/**
 * Contact Name Field Injection Script
 * 
 * This script adds a "Contact Name" field to the scanner form
 * WITHOUT modifying the original React bundle. It:
 * 1. Waits for the form to render
 * 2. Injects a Contact Name input after Business Name
 * 3. Intercepts form submission to include contact_name in the API payload
 */
(function() {
  'use strict';

  var contactNameValue = '';
  var injected = false;

  // Intercept fetch to add contact_name to /api/scan POST requests
  var originalFetch = window.fetch;
  window.fetch = function(url, options) {
    if (url && typeof url === 'string' && url.includes('/api/scan') && options && options.method === 'POST') {
      try {
        var body = JSON.parse(options.body);
        body.contact_name = contactNameValue;
        options = Object.assign({}, options, { body: JSON.stringify(body) });
      } catch(e) {}
    }
    return originalFetch.apply(this, arguments);
  };

  function injectContactNameField() {
    if (injected) return;

    // Find the Business Name input by its placeholder
    var inputs = document.querySelectorAll('input[placeholder="e.g. Joe\'s Plumbing"]');
    if (inputs.length === 0) return;

    var businessNameInput = inputs[0];
    var businessNameDiv = businessNameInput.closest('div');
    if (!businessNameDiv || !businessNameDiv.parentElement) return;

    // Create the Contact Name field container
    var contactDiv = document.createElement('div');

    // Create label
    var label = document.createElement('label');
    label.className = 'block text-sm font-medium text-gray-300 mb-1';
    label.textContent = 'Contact Name *';
    contactDiv.appendChild(label);

    // Create input
    var input = document.createElement('input');
    input.type = 'text';
    input.required = true;
    input.className = businessNameInput.className;
    input.placeholder = 'e.g. John Smith';
    input.addEventListener('input', function(e) {
      contactNameValue = e.target.value;
    });
    contactDiv.appendChild(input);

    // Insert after Business Name div
    businessNameDiv.parentElement.insertBefore(contactDiv, businessNameDiv.nextSibling);

    injected = true;
  }

  // Use MutationObserver to detect when the form renders
  var observer = new MutationObserver(function() {
    injectContactNameField();
  });

  observer.observe(document.body || document.documentElement, {
    childList: true,
    subtree: true
  });

  // Also try immediately and on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', function() {
    setTimeout(injectContactNameField, 500);
    setTimeout(injectContactNameField, 1500);
    setTimeout(injectContactNameField, 3000);
  });

  // If body already loaded
  if (document.readyState !== 'loading') {
    setTimeout(injectContactNameField, 500);
    setTimeout(injectContactNameField, 1500);
    setTimeout(injectContactNameField, 3000);
  }
})();
