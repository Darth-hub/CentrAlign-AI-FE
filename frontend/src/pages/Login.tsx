import { useState } from 'react';
import { useAuth } from '../AuthContext';
import { OIDC_AUTHORITY } from '../runtimeConfig';
import { Button } from '@/components/ui/button';
export default function Login() {
  const { login } = useAuth();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function signIn() {
    setLoading(true); setError('');
    try { await login('', ''); } catch (e) { setError(e instanceof Error ? e.message : 'Sign-in failed'); setLoading(false); }
  }
  return <div className="min-h-screen flex items-center justify-center bg-background p-6">
    <main className="max-w-md w-full rounded-xl border bg-card p-8 space-y-5 shadow-sm">
      <h1 className="text-3xl font-bold">CentrAlign AI</h1>
      <p className="text-muted-foreground">Procurement operations with accountable AI agents.</p>
      {!OIDC_AUTHORITY && <p role="alert" className="text-sm text-amber-600">Sign-in is not configured. Connect the backend and set the Netlify environment variables described in the deployment guide.</p>}
      {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
      <Button className="w-full" disabled={!OIDC_AUTHORITY || loading} onClick={signIn}>Sign in securely</Button>
      <p className="text-xs text-muted-foreground">Your organization controls your role and ERP permissions.</p>
    </main>
  </div>;
}
