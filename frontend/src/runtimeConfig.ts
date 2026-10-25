/** Public deployment configuration only. Never put provider keys here. */
export const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
export const OIDC_AUTHORITY = import.meta.env.VITE_OIDC_AUTHORITY || '';
export const OIDC_CLIENT_ID = import.meta.env.VITE_OIDC_CLIENT_ID || 'aria-web';
