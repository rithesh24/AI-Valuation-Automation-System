# AVAS Development Roadmap

## Phase 1 - Project Foundation
- [x] Initialize Git
- [x] Setup Electron (scaffolded and verified: tsc build succeeds)
- [x] Setup Next.js (scaffolded and verified: next build succeeds)
- [x] Setup FastAPI (scaffolded and verified: pytest passes)
- [x] Configure project structure

---

## Phase 2 - File Upload System
- [x] Upload PDFs
- [x] Upload DOCX
- [x] Upload Images
- [x] File validation
- [x] Temporary storage

---

## Phase 3 - Document Processing
- [ ] PDF text extraction
- [ ] DOCX extraction
- [ ] OCR integration

---

## Phase 4 - Browser Automation
- [ ] Playwright setup
- [ ] eASR automation (confirmed: no CAPTCHA, fully unattended)
- [ ] Retry mechanism
- [ ] Error handling
- [ ] Evaluate RERA/SRO automation feasibility (stretch, per-source)

---

## Phase 5 - AI Integration
- [ ] Canonical data schema (derived from docs/PROMPTS.md sections 4-11, 24-26)
- [ ] Prompt Builder
- [ ] Claude API
- [ ] Web-search tool integration for Tier 2 comparable research (99acres, MagicBricks, etc.)
- [ ] Token tracking

---

## Phase 6 - Report Generation
- [ ] Template skeleton extraction (python-docx)
- [ ] Claude-assisted field-to-template mapping
- [ ] Mapping cache (keyed by template skeleton hash) + manual regenerate override
- [ ] Clone-and-fill DOCX injection (preserve formatting)
- [ ] Automated final quality-check validation pass
- [ ] Preview report
- [ ] Download DOCX

---

## Phase 7 - Dashboard
- [ ] Token usage
- [ ] API cost

- [ ] Monthly statistics

---

## Phase 8 - Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] UI testing

---

## Phase 9 - Production
- [ ] Build Electron app
- [ ] Package installer
- [ ] Documentation