# AVAS Architecture Decisions

Lightweight decision log. Each entry captures what was decided, and why — so decisions aren't relitigated later without new information.

---

## D1 — Single-user desktop application, no authentication (2026-07-22)
**Decision:** AVAS is a single-user local desktop tool. No login, accounts, or roles.
**Why:** Confirmed by the client; the valuer is the only operator of their own installation.
**Implication:** `usage_service.py` tracks usage globally per installation, not per-user.

## D2 — Maharashtra eASR is the only official-rates source for V1 (2026-07-22)
**Decision:** `easr_service.py` targets Maharashtra eASR exclusively in V1. Other states are out of scope until explicitly requested.

## D3 — Claude Sonnet is the AI model (2026-07-22)
**Decision:** `claude_service.py` uses Claude Sonnet for extraction, mapping, and report-content generation calls.

## D4 — Arbitrary bank templates, no predefined placeholders (2026-07-22)
**Decision:** The system must accept any bank's `.docx` template as uploaded, unmodified. No merge-field/placeholder tagging convention is required from the user.
**Why:** Banks supply their own templates as-is; requiring the valuer to pre-tag them defeats the purpose of automation.

## D5 — Three-stage template population pipeline (2026-07-22)
**Decision:** Report generation is split into three stages rather than asking Claude to generate a formatted document directly:
1. **Extraction** — Claude reads source documents + research data, returns structured data matching the canonical schema (see D9). No formatting involved.
2. **Mapping** — `report_service.py` parses the uploaded template with `python-docx`, extracts a structural skeleton (every paragraph/table/cell plus adjacent label text), and sends that skeleton to Claude (via `claude_service.py`) to map schema fields to skeleton locations.
3. **Injection** — code (not Claude) applies the mapping deterministically: existing `Run` objects have their `.text` replaced in place (inheriting existing formatting automatically); table rows are duplicated from an existing correctly-formatted row's XML rather than created fresh.
**Why:** LLMs are unreliable at reproducing exact visual formatting from a description, but reliable at semantic matching. Never generating new formatted elements — only cloning and mutating existing ones — guarantees fidelity (fonts, spacing, no shading, table margins) by construction instead of by hoping the model gets it right.
**Related:** D6 (mapping cache), D9 (schema).

## D6 — Template-mapping cache keyed by structural skeleton hash (2026-07-22)
**Decision:** The Stage-2 mapping result is cached, keyed by a hash of the *extracted skeleton* (not the raw file bytes). A manual "regenerate mapping" action is exposed in the UI, and cache entries (bank name, first-seen date) are visible to the valuer via the SQLite persistence layer.
**Why:** Valuers reuse the same handful of bank templates repeatedly — caching avoids re-running the mapping call (cost, latency, variance) for every report. Hashing raw file bytes was rejected because trivial re-saves (Word metadata changes) would cause unnecessary cache misses without any real layout change; hashing the skeleton instead means a genuinely-changed template (renamed label, moved section, new table column) always produces a new hash and triggers a fresh mapping, while a cosmetic re-save still hits the cache.

## D7 — No CAPTCHA on Maharashtra eASR — full Playwright automation in scope (2026-07-22)
**Decision:** Confirmed by the client that the Maharashtra eASR portal (igreval) does not present a CAPTCHA. `easr_service.py` can therefore perform fully unattended retrieval with retries, as originally scoped in `ARCHITECTURE.md`, without a human-in-the-loop step.

## D8 — Two-tier market/comparable research strategy (2026-07-22)
**Decision:**
- **Tier 1 (official/government data)** — Ready Reckoner/guideline value (via eASR), and potentially RERA/SRO if their public search pages prove similarly automatable — dedicated Playwright services, following the eASR pattern, returning structured data.
- **Tier 2 (comparable listings)** — 99acres, MagicBricks, Housing.com, and other heterogeneous public sources — handled via Anthropic's hosted web-search tool, attached to the Claude Messages API call in `claude_service.py`, rather than custom scrapers.
**Why:** Government portals are stable, structured, and safe to automate deterministically. Real-estate listing portals are numerous, change their DOM frequently, and scraping them carries ToS risk. Claude's own web-search tool already performs this kind of research (with citations, source URLs, and access dates) in the client's current manual workflow, so using it via the API preserves that behavior instead of rebuilding it as fragile scraper code.

## D9 — Canonical data schema derived from docs/PROMPTS.md (2026-07-22)
**Decision:** The Pydantic schema shared between services (extraction output, mapping input, injection input) will be based directly on the field list already present in the client's working prompt (`docs/PROMPTS.md`, Sections 4–11 and 24–26: property identification, ownership/title flow, area reconciliation, boundaries, site/building particulars, land use/statutory position, encumbrances, valuation calculation, concluded values), rather than designed from scratch.
**Why:** That prompt already encodes the client's real-world professional requirements (IVS/IBBI compliance) field-by-field; reinventing the schema risks missing something the client's current manual process already accounts for.

## D10 — SQLite as the local persistence layer (2026-07-22)
**Decision:** SQLite is added for usage tracking (tokens/cost/monthly stats), report generation history, and the template-mapping cache (D6).
**Why:** Desktop, single-user app; SQLite requires no separate server and is sufficient for this scale.

## D11 — Deterministic OCR fallback (2026-07-22)
**Decision:** OCR triggering will use an explicit rule (e.g., extracted text length below a threshold triggers OCR) rather than a vague "if required." Exact threshold to be set during Phase 3.

## D12 — Testing introduced progressively (2026-07-22)
**Decision:** Test coverage is added per phase as features are built, rather than deferred entirely to Phase 8. First instance: Phase 1 shipped with a passing pytest test against `/health`.
