# Security model

Retrieved excerpts and request topics are untrusted data. Agents receive an
explicit policy and JSON-encoded input, with no tools, no delegation, no memory,
and verbose output disabled. Search uses a fixed allowlisted Serper HTTPS endpoint;
source URLs are metadata and are never fetched. Only Python controls stages,
source IDs, persistence and citation acceptance. Prompt text cannot add tools,
read environment variables or skip a stage through a workflow API.

This constrains capabilities; it does not prove a model will never follow hostile
text in its generated prose. Injection fixtures preserve hostile text as provenance
while requiring citation validation and safe status assignment to run normally.
Exact-quote checking proves a quote exists, not that it is relevant or trustworthy.

URL checks reject non-HTTP(S), credential-bearing, local/private literal addresses,
local hostname suffixes and nonstandard ports. Arbitrary source domains are not
resolved or crawled. A future fetcher must add DNS/rebinding and redirect defenses.
Ollama is limited to loopback HTTP. Serper responses have a byte cap, timeouts and
three bounded attempts for transient failures, and redirects are not followed.

Provider keys entered in Streamlit remain in session widget/config memory and are
passed explicitly into LLM constructors. Serper keys are passed only in the API
header. `SecretStr` masks key representation and excludes keys from config dumps.
Configuration is never stored in Flow state. No application code logs keys or
exports raw exception bodies. Failure records use safe categories. CrewAI tracing
and OpenTelemetry are disabled before import; agents and crews are non-verbose.
Operational UI events do not inspect model thoughts or internal step callbacks.

Web mode sends topics/queries to the search service and evidence to the selected
model service. Do not place secrets in topics or retrieved content: these inputs
are intentionally persisted as research data and may appear in reports. This app
does not automatically detect/redact arbitrary sensitive content. SQLite and local
reports are not encrypted; use filesystem access controls and remove local data
when no longer needed. Multiple UI sessions use session keys but share run storage;
there is no account authentication, authorization or tenant isolation.

`.env`, local data, virtual environments and bootstrap/runtime downloads are
ignored. `.env.example` has empty keys only. Run
`uv run --locked python scripts/check_secrets.py` for tracked and nonignored new
file patterns, ignored/untracked dotenv assertions and placeholder verification.
The checker prints file names only and never matched values. It is a deterministic
pattern check, not an exhaustive credential detector or history audit.

The baseline tag remains recoverable and no existing history is rewritten. Default
CI requires no secrets. Production deployment needs authentication, storage isolation,
monitoring, stronger semantic evaluation and an operational security review.
