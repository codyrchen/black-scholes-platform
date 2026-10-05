export const API_URL = (process.env.REACT_APP_API_URL || 'http://localhost:5001').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status, code, details } = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function describeValidation(details) {
  if (!Array.isArray(details) || details.length === 0) return '';
  return details
    .map((d) => `${(d.loc || []).join('.')}: ${d.msg}`)
    .join('; ');
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch (e) {
    throw new ApiError(
      `Can't reach the API at ${API_URL}. Start it with "python3 app.py" (port 5001), ` +
        'or set REACT_APP_API_URL if it runs elsewhere.',
      { code: 'NETWORK' },
    );
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const err = body && body.error;
    const message = err
      ? [err.message, describeValidation(err.details)].filter(Boolean).join(' ')
      : `Request failed (${response.status} ${response.statusText})`;
    throw new ApiError(message, { status: response.status, code: err && err.code, details: err && err.details });
  }
  return body;
}

export const apiGet = (path) => request(path);
export const apiPost = (path, data) => request(path, { method: 'POST', body: JSON.stringify(data) });
