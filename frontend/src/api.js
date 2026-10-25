export const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/+$/, '');

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// Kept independent of React so the real HTTP contract can be checked directly.
export function createApi(baseUrl = API_BASE_URL, getToken = () => null, onUnauthorized = () => {}) {
  return async function request(path, { method = 'GET', body, signal } = {}) {
    const token = getToken();
    let response;
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method, signal,
        headers: {
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new ApiError('Unable to reach the server. Check your connection and try again.', 0);
    }
    if (response.status === 204) return null;
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401 && token) onUnauthorized();
      const detail = data?.detail;
      const message = Array.isArray(detail)
        ? detail.map(item => `${item.loc?.slice(1).join(' · ') || 'Input'}: ${item.msg}`).join('; ')
        : typeof detail === 'string' ? detail : `Request failed (${response.status}). Please try again.`;
      throw new ApiError(message, response.status);
    }
    return data;
  };
}
