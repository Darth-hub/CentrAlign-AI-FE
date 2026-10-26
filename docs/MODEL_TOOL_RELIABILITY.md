# Model tool-call reliability

## Observed failure

The original sourcing attempt received many Groq 429 responses and then `Failed to parse tool call arguments as JSON`. An isolated sourcing retry with GPT-OSS also exhausted one bounded response retry. This was a provider/model generation failure, distinct from OIDC login and ERP authentication.

## Runtime behavior

- Groq responses are requested without token streaming and with parallel tool calls disabled.
- Tool argument strings must decode to JSON objects before any response events are released to Strands.
- A rejected `tool_use_failed` response or malformed tool-argument object gets one fresh model-response attempt. This does not rerun an agent, workflow, or previously executed tool.
- Authentication and unrelated API errors are not resampled by this handler. Existing provider rate-limit handling and the worker deadline still apply.
- Invalid provider generations are never interpreted as Python or repaired into executable actions.
- GPT-OSS uses its supported low reasoning-effort setting; other models do not receive this model-specific parameter.
- Tool result serialization omits null optional fields and unnecessary whitespace, while preserving zero and false values.

The adapter extends the locked Strands OpenAI provider. Review this integration when upgrading the SDK; regression tests cover partial-response buffering, bounded retries, unrelated errors, JSON object requirements and factory configuration.

## Prompt and tool alignment

Sourcing and invoice prompt examples now use valid JSON braces. Sourcing reuses aggregate/history reads instead of requesting the same empty history for each supplier. The workflow exposes the calculator its prompt describes. Every agent also receives the current ERP tool-call protocol, with identity bound by the server.

The backend's independent approvals, write claims and ERP read-back verification remain the authority for consequential work.

## Local model selection

The configured account's live `/models` endpoint offered `qwen/qwen3.8-27b`; it passed a live arithmetic probe with one verified tool invocation. The local environment now selects that model. Model availability and quotas vary by account; this is not a universal availability or reliability claim. Keep `LLM_MODEL` configurable and provider credentials private.

Groq's [reasoning parameters](https://console.groq.com/docs/reasoning) document the GPT-OSS effort setting. Use the authenticated model listing and account limits when selecting a model; cached public model lists can differ from the actual account response.

Full sourcing verification is recorded in [validation status](STATUS.md). A successful tool probe alone is not proof of a completed procurement workflow.
