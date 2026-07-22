# AI Valuation Automation System (AVAS)

## Project Overview

AI Valuation Automation System (AVAS) is a desktop application that automates the preparation of professional property valuation reports for banks and financial institutions.

The application allows valuers to upload property-related documents, a bank valuation template, and optional supporting images. It then extracts relevant information, performs automated research where required, and generates a completed valuation report using Anthropic Claude while preserving the formatting of the uploaded bank template.

---

# Objectives

- Reduce manual effort in preparing valuation reports.
- Minimize human errors.
- Preserve bank-specific report formatting.
- Generate reports significantly faster than manual workflows.
- Ensure every generated report is factually grounded and professionally formatted.

---

# Target Users

- Property Valuers
- Civil Engineers
- Bank Approved Valuers
- Financial Institutions

---

# Core Features

### Document Upload

- Upload property documents (PDF, DOCX, Images)
- Upload bank valuation template (.docx)
- Upload optional supporting images

### Document Processing

- Extract text from PDFs
- Extract information from Word documents
- OCR for scanned documents (when required)

### AI Processing

- Analyze uploaded documents
- Combine extracted information
- Generate valuation report
- Preserve uploaded template formatting

### Browser Automation

- Retrieve official guideline values from Maharashtra eASR using Playwright.
- Use verified information only.
- Handle failures gracefully.

### Report Generation

- Populate uploaded bank template
- Preserve layout and formatting
- Generate editable DOCX

### Report Preview

- Preview report before export
- Allow regeneration if necessary

### AI Usage Dashboard

- Token usage
- Estimated API cost
- Monthly usage
- Budget monitoring

---

# Technology Stack

## Desktop

Electron

## Frontend

Next.js

React

TypeScript

## Backend

FastAPI

Python

## AI

Anthropic Claude API

## Browser Automation

Playwright

## Document Processing

PyMuPDF

python-docx

OCR (EasyOCR/Tesseract if required)

---

# Business Rules

- Never hallucinate information.
- Never invent missing values.
- Never modify facts found in uploaded documents.
- Preserve original document formatting whenever possible.
- Every output must remain suitable for professional bank submission.

If information cannot be verified:

Output:

"Information Not Available"

---

# Application Workflow

1. Upload required property documents.
2. Upload bank valuation template.
3. Upload supporting images (optional).
4. Validate uploaded files.
5. Extract document contents.
6. Retrieve official data using Playwright (where applicable).
7. Build AI prompt.
8. Generate valuation report.
9. Populate uploaded template.
10. Preview report.
11. Download DOCX.

---

# Non-Functional Requirements

- Modular architecture
- Maintainable codebase
- Production-ready
- Responsive desktop UI
- Proper error handling
- Logging
- Secure API key handling
- Fast report generation

---

# Project Goals

The goal is to build a reliable, production-quality desktop application that assists professional valuers in generating accurate valuation reports efficiently while maintaining compliance with industry standards.

This is intended to be commercial-grade software rather than a demonstration or portfolio project.