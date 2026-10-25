export default function Architecture() {
  const stages = [
    ["01 / Understand", "Chat captures procurement intent and retrieves company records through the acting user's ERP permissions."],
    ["02 / Plan and reason", "Domain agents evaluate suppliers, analyze requisitions and choose permitted tool operations."],
    ["03 / Execute", "A persistent worker runs each queued job in an isolated process and records progress."],
    ["04 / Review exceptions", "Approval, invoice confirmation and payment actions keep consequential decisions visible to the responsible user."],
    ["05 / Verify", "PO completion requires an ERP record created through the tool boundary and checked on read-back."],
    ["06 / Recover", "Interrupted work retains a document lock. Uncertain ERP writes require reconciliation before a retry."],
  ];
  return (
    <div className="space-y-6 animate-fade-up">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-teal-600 dark:text-teal-400">CentrAlign AI / System architecture</p>
        <h1 className="text-3xl font-bold tracking-tight">From intent to a verified outcome</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">Identity, durable execution and ERP evidence connect the procurement workflow. The frontend targets Netlify; the backend runs as persistent Docker services.</p>
      </header>
      <figure className="overflow-hidden rounded-xl border bg-[#0c1725]">
        <a href="/architecture.svg" target="_blank" rel="noreferrer" aria-label="Open the full system architecture diagram">
          <img src="/architecture.svg" alt="CentrAlign AI system map showing the frontend, identity, API, agent worker, model providers, ERPNext and persistent storage" className="w-full" />
        </a>
        <figcaption className="border-t border-slate-700 px-5 py-3 text-xs text-slate-300">Select the diagram to inspect the full system map.</figcaption>
      </figure>
      <section aria-label="Execution stages" className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {stages.map(([title, text]) => (
          <article key={title} className="rounded-xl border bg-card p-5">
            <h2 className="font-semibold">{title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{text}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
