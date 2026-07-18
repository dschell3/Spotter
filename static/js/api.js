// Shared fetch wrapper: attaches CSRF token + JSON handling for same-origin API calls.
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || '';

async function apiFetch(url, options = {}) {
  const opts = { credentials: 'same-origin', ...options };
  opts.headers = { ...(options.headers || {}) };
  const method = (opts.method || 'GET').toUpperCase();
  if (method !== 'GET') opts.headers['X-CSRFToken'] = CSRF_TOKEN;
  if (opts.body && typeof opts.body !== 'string') {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  return fetch(url, opts);
}

// Escape a user-controlled value for safe interpolation into innerHTML.
function esc(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}
