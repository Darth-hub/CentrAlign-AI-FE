// A frontend-only preview can build without backend credentials. Supplied URLs
// must be HTTPS so production users cannot accidentally call localhost/HTTP.
for (const name of ['VITE_API_URL', 'VITE_OIDC_AUTHORITY']) {
  const value = process.env[name];
  if (!value) { console.warn(`${name} is unset: the deployed frontend will require backend configuration.`); continue; }
  const url = new URL(value);
  if (url.protocol !== 'https:' || ['localhost', '127.0.0.1', '::1'].includes(url.hostname))
    throw new Error(`${name} must be a public HTTPS URL for Netlify deployment`);
}
for (const name of Object.keys(process.env)) {
  if (/^VITE_.*(SECRET|PASSWORD|API_KEY|TOKEN)$/.test(name))
    throw new Error(`Do not expose secrets through frontend build variable ${name}`);
}
