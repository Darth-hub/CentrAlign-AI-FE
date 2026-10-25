/** Compatibility filename for the portable persistent-job client. No AWS SDK. */
import { getToken, invalidateSession } from './auth';
import { API_BASE } from './runtimeConfig';
export interface AgentEvent {
  type: 'progress' | 'result' | 'error'; step?: string; agent?: string; tool?: string;
  document_id?: string; result?: unknown; tools_used?: unknown[]; progress_steps?: string[];
  metrics?: Record<string, number>; error?: string; message?: string; status?: string;
}
const AGENTS = new Set(['requisition', 'sourcing', 'po_management', 'receiving', 'invoice_matching', 'payment', 'workflow']);
export function isAgentCoreAvailable(agent: string): boolean { return AGENTS.has(agent); }
async function call(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await getToken();
  if (!token) { await invalidateSession(); throw new Error('Session expired. Sign in again.'); }
  const response = await fetch(API_BASE + path, { ...init,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } });
  if (response.status === 401) { await invalidateSession(); throw new Error("Your session could not be verified. Sign in again."); }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Backend returned HTTP ${response.status}`);
  }
  return response;
}
function delay(signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const done = () => { signal?.removeEventListener('abort', abort); resolve(); };
    const timer = window.setTimeout(done, 1200);
    const abort = () => { clearTimeout(timer); signal?.removeEventListener('abort', abort); reject(new DOMException('Aborted', 'AbortError')); };
    if (signal?.aborted) abort(); else signal?.addEventListener('abort', abort, { once: true });
  });
}
export async function* invokeAgentCore(agent: string, documentId: string,
  extra: Record<string, string> = {}, signal?: AbortSignal): AsyncGenerator<AgentEvent> {
  const started = await call(`/agents/${encodeURIComponent(agent)}/runs`, { method: 'POST', signal,
    body: JSON.stringify({ document_id: documentId, order_id: extra.order_id || '', resume_from: extra.resume_from || '' }) });
  const { job_id } = await started.json();
  yield { type: 'progress', step: `Queued execution ${job_id}`, agent };
  let after = 0;
  while (!signal?.aborted) {
    const response = await call(`/agents/runs/${encodeURIComponent(job_id)}/events?after=${after}`, { signal });
    const body = await response.json() as { status: string; events: (AgentEvent & { sequence: number })[] };
    for (const event of body.events) {
      after = event.sequence;
      yield event;
      if (event.type === 'result' || event.type === 'error') return;
    }
    if (['completed', 'failed', 'interrupted', 'reconciled'].includes(body.status) && body.events.length < 100) {
      yield { type: 'error', error: `Execution ${body.status} without a result. Check execution history.` };
      return;
    }
    await delay(signal);
  }
}
