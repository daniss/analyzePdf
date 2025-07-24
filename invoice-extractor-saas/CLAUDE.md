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
- Uses multimodal Claude to process invoice images directly
- No traditional OCR needed - Claude handles both text extraction and understanding
- Processes up to 10 pages per invoice
- Returns structured data with validation

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
```

## Environment Configuration

### Backend Required Variables
```bash
# backend/.env
ANTHROPIC_API_KEY=sk-ant-...  # Required for Claude 4
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/invoiceai
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here  # Change in production
```

### Frontend Variables
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Current Implementation Status

### ✅ Completed
- Basic project structure and Docker setup
- Claude 4 vision integration for invoice processing
- PDF to image conversion pipeline
- Frontend UI with landing page and dashboard
- File upload component with drag-and-drop
- Mock authentication pages

### ❌ Not Implemented (TODOs in code)
- Database models and migrations
- Real JWT authentication (currently mock)
- Actual data persistence (invoices stored in memory)
- Stripe payment integration
- Email notifications
- S3/R2 file storage (using local storage)
- Rate limiting and security hardening
- Testing infrastructure

## Important Code Locations

### Backend
- `backend/main.py` - FastAPI app configuration and routers
- `backend/api/invoices.py` - Invoice upload and processing endpoints
- `backend/core/ai/claude_processor.py` - Claude 4 vision integration
- `backend/core/pdf_processor.py` - PDF to image conversion
- `backend/core/config.py` - Application settings

### Frontend
- `frontend/app/page.tsx` - Landing page
- `frontend/app/dashboard/page.tsx` - Main dashboard
- `frontend/components/invoice/file-upload.tsx` - File upload component
- `frontend/app/auth/` - Authentication pages (signin/signup)

## Common Development Tasks

### Add a New API Endpoint
1. Create route function in appropriate file under `backend/api/`
2. Add Pydantic schema in `backend/schemas/`
3. Include router in `backend/main.py`
4. Update frontend API client to call new endpoint

### Modify Invoice Data Structure
1. Update `backend/schemas/invoice.py` with new fields
2. Modify `backend/core/ai/claude_processor.py` extraction prompt
3. Update frontend TypeScript interfaces
4. Adjust export formats in `backend/api/exports.py`

### Deploy to Production
1. Frontend: `cd frontend && vercel deploy`
2. Backend: Deploy to Railway/Render with environment variables
3. Database: Use managed PostgreSQL (Neon/Supabase)
4. Set production `ANTHROPIC_API_KEY` and `SECRET_KEY`

## Cost Considerations
- Claude 4 Opus uses ~1000 tokens per invoice page
- Typical invoice (1-2 pages) costs $0.015-0.03 to process
- Monitor usage to stay within Anthropic rate limits

## Debugging Tips
- Check `docker-compose logs backend` for processing errors
- Invoice processing happens in background task - check console logs
- Claude API errors usually relate to invalid API key or rate limits
- PDF conversion errors often due to corrupted files or missing dependencies