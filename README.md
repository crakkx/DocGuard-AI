# DocGuard AI

DocGuard AI is a multimodal procurement compliance and audit-review system.

The application processes invoices and purchase orders, extracts structured
fields, validates them against company policies and deterministic rules,
calculates risk, supports human review, and records a complete audit trail.

## Initial MVP

- Invoice and purchase-order upload
- OCR-based document extraction
- Pydantic structured outputs
- Invoice-to-PO matching
- Policy RAG with citations
- Deterministic compliance rules
- Risk scoring
- Human correction and approval
- Audit logging
- Evaluation scripts
- Docker Compose
- GitHub Actions

## Repository structure

- `backend/`: FastAPI application and tests
- `frontend/`: React reviewer interface
- `evals/`: extraction and compliance evaluation
- `sample_data/`: safe synthetic documents and ground truth
- `docs/`: architecture, decisions, and API contracts
- `scripts/`: development and data-management scripts
