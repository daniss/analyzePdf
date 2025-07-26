# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InvoiceAI is an AI-powered PDF invoice data extractor SaaS that uses Claude 4 Opus vision API exclusively for both OCR and intelligent data extraction. The project consists of a Next.js frontend and FastAPI backend with PostgreSQL/Redis for data storage.

## Key Architecture Points

### Invoice Processing Flow
1. Frontend uploads PDF/image to backend via `/api/invoices/upload`
2. Backend converts PDFs to images using `pypdfium2` (300 DPI)
3. Images are base64 encoded and sent to Claude 4 Opus vision API
4. Claude extracts structured data (invoice number, dates, amounts, line items)
5. System validates extraction and stores in database
6. Data available for export as CSV/JSON

### Frontend-Backend Communication
- Frontend runs on port 3000, backend on port 8000
- API uses JWT authentication with OAuth2 password flow
- All invoice endpoints require authentication token
- File uploads limited to 10MB, supports PDF/PNG/JPG

### Claude 4 Integration
- Located in `backend/core/ai/claude_processor.py`
- Uses Claude 4 Opus multimodal capabilities for invoice processing
- GDPR-compliant with transfer risk assessment before API calls
- Comprehensive audit logging for all Claude API interactions
- Processes multiple pages per invoice with structured data extraction
- Automatic data subject creation from extracted invoice information
- Returns validated data with confidence scoring

## Development Commands

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Docker Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down
```

### Database Operations
```bash
cd backend
# Create migrations (when models change)
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Testing Commands
```bash
# Backend tests (not yet implemented)
cd backend
pytest
pytest --cov=. --cov-report=html

# Frontend tests (not yet implemented)
cd frontend
npm run test
npm run test:e2e

# Linting and formatting
cd frontend
npm run lint

# Type checking (frontend uses TypeScript)
cd frontend
npx tsc --noEmit
```

## Environment Configuration

### Backend Required Variables
```bash
# backend/.env
ANTHROPIC_API_KEY=sk-ant-...  # Required for Claude 4 Opus
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/invoiceai
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here  # Change in production
ENCRYPTION_KEY=your-32-byte-encryption-key  # For GDPR data encryption
AI_MODEL=claude-3-opus-20240229  # Claude model to use
MAX_TOKENS=4000  # Max tokens for Claude API calls
```

### Frontend Variables
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Current Implementation Status

### ✅ Completed
- Full project structure with Docker setup
- Claude 4 Opus vision integration for invoice processing
- PDF to image conversion pipeline with pypdfium2
- Complete database models with Alembic migrations
- GDPR-compliant data processing and storage
- Comprehensive audit logging system
- Data subject management and rights handling
- Transfer risk assessment for Claude API
- Frontend UI with landing page and dashboard
- File upload component with drag-and-drop
- Encrypted data storage and transit security

### ❌ Not Implemented (TODOs in code)
- JWT authentication implementation (auth endpoints exist but not integrated)
- Stripe payment integration
- Email notifications
- S3/R2 file storage (using local storage)
- Rate limiting middleware
- Frontend test suite
- Backend test suite

## Important Code Locations

### Backend Core
- `backend/main.py` - FastAPI app configuration and routers
- `backend/core/config.py` - Application settings and environment variables
- `backend/core/database.py` - Database connection and session management

### API Endpoints
- `backend/api/invoices.py` - Invoice upload and processing endpoints
- `backend/api/auth.py` - Authentication endpoints (registration, login)
- `backend/api/exports.py` - Data export functionality (CSV, JSON)
- `backend/api/gdpr_rights.py` - GDPR subject rights endpoints

### AI Processing
- `backend/core/ai/claude_processor.py` - Claude 4 Opus vision integration with GDPR compliance
- `backend/core/pdf_processor.py` - PDF to image conversion using pypdfium2

### Data Models and Storage
- `backend/models/gdpr_models.py` - Database models for GDPR compliance
- `backend/models/user.py` - User authentication models
- `backend/crud/` - Database operations (invoice, user, audit, data_subject)
- `backend/schemas/` - Pydantic schemas for API validation

### GDPR Compliance
- `backend/core/gdpr_audit.py` - Audit logging for GDPR compliance
- `backend/core/gdpr_encryption.py` - Data encryption for sensitive information
- `backend/core/gdpr_transfer_compliance.py` - International transfer compliance
- `backend/core/gdpr_helpers.py` - GDPR utility functions

### Frontend
- `frontend/app/page.tsx` - Landing page
- `frontend/app/dashboard/page.tsx` - Main dashboard
- `frontend/components/invoice/file-upload.tsx` - File upload component
- `frontend/app/auth/` - Authentication pages (signin/signup)
- `frontend/lib/api.ts` - API client for backend communication

## GDPR Compliance Features

### Data Subject Rights
- Right to access personal data
- Right to rectification (data correction)
- Right to erasure (data deletion)
- Right to data portability
- All rights accessible via `/api/gdpr-rights/` endpoints

### Audit Logging
- All data processing operations are logged
- Audit logs include user, operation type, data categories, and risk level
- GDPR-compliant retention and deletion of audit logs

### Data Encryption
- Sensitive data encrypted at rest using AES-256
- Encryption keys managed securely
- Transit encryption for Claude API communication

### Transfer Compliance
- Risk assessment before international data transfers
- Approval workflow for high-risk transfers
- Compliance with GDPR Chapter V requirements

## Cost Considerations
- Claude 4 Opus uses ~1000 tokens per invoice page
- Typical invoice (1-2 pages) costs $0.015-0.03 to process
- Monitor usage to stay within Anthropic rate limits

## Debugging Tips
- Check `docker-compose logs backend` for processing errors
- Invoice processing happens in background task - check console logs
- Claude API errors usually relate to invalid API key or rate limits
- PDF conversion errors often due to corrupted files or missing dependencies