export default function Architecture() {
  const stages = [
    ["Netlify frontend", "React UI signs in with OIDC and polls job progress over HTTPS."],
    ["API and identity", "FastAPI verifies tokens from Keycloak and enforces application roles."],
    ["Persistent execution", "PostgreSQL stores jobs, progress, chat and decisions. A Python worker runs each agent job in a separate process."],
    ["Agent reasoning", "Strands agents use a configured model, typed ERP operations and a restricted arithmetic tool."],
    ["ERP execution", "Per-user ERPNext credentials preserve ERP permissions. Write checks gate POs and payments; uncertain writes require reconciliation."],
    ["Human review", "Approvals and invoice confirmation are explicit actions with recorded identities."],
  ];
  return <div className="space-y-6"><h1 className="text-2xl font-bold">Portable ARIA architecture</h1>
    <p className="text-muted-foreground">The frontend is hosted on Netlify. The backend requires a persistent host with Docker and storage.</p>
    <div className="grid gap-4 md:grid-cols-2">{stages.map(([title, text], i) => <section key={title} className="rounded-lg border bg-card p-5"><h2 className="font-semibold">{i + 1}. {title}</h2><p className="text-sm mt-2 text-muted-foreground">{text}</p></section>)}</div>
    <p className="text-sm text-muted-foreground">This migration replaces the managed AWS services with self-hosted components. Formal policy verification and arbitrary code execution are not included.</p>
  </div>;
}
