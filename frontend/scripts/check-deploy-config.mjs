import { loadEnv } from 'vite';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Match Vite's production env loading, including .env.local and
// .env.production. Checking process.env alone misses values bundled by Vite.
export function validateDeploymentConfig(env) {
  const warnings = [];
  for (const name of Object.keys(env)) {
    if (/^VITE_.*(SECRET|PASSWORD|API_KEY|TOKEN)/i.test(name)) {
      throw new Error(`Do not expose secrets through frontend build variable ${name}`);
    }
  }
  for (const name of ['VITE_API_URL', 'VITE_OIDC_AUTHORITY']) {
    const value = env[name];
    if (!value) {
      warnings.push(`${name} is unset: only the public architecture preview will be available until the backend is configured.`);
      continue;
    }
    let url;
    try { url = new URL(value); } catch { throw new Error(`${name} must be a public HTTPS URL`); }
    const hostname = url.hostname.toLowerCase();
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash ||
        hostname === 'localhost' || hostname.endsWith('.localhost') || hostname === '[::1]' ||
        /^127\./.test(hostname) || hostname === '0.0.0.0') {
      throw new Error(`${name} must be an HTTPS URL without credentials, query or fragment; loopback addresses are not valid for Netlify`);
    }
  }
  if (Boolean(env.VITE_API_URL) !== Boolean(env.VITE_OIDC_AUTHORITY)) {
    throw new Error('Configure both VITE_API_URL and VITE_OIDC_AUTHORITY, or leave both unset for an architecture preview');
  }
  return warnings;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const warnings = validateDeploymentConfig(loadEnv('production', process.cwd(), 'VITE_'));
    warnings.forEach(message => console.warn(message));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
