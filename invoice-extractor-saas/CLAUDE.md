# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ComptaFlow est une plateforme SaaS intelligente d'extraction de données de factures PDF conçue spécifiquement pour les experts-comptables français. Elle utilise l'API Groq (Llama 3.1 8B) comme AI principal avec Claude 4 Opus en fallback pour l'OCR et l'extraction intelligente de données. Le projet se compose d'un frontend Next.js et d'un backend FastAPI avec PostgreSQL/Redis pour le stockage des données.

**CRITICAL**: The system is now GDPR-compliant with memory-only file processing - no files are stored permanently on disk.

## Key Architecture Points

### Invoice Processing Flow (GDPR-Compliant)
1. Frontend uploads PDF/image to backend via `/api/invoices/upload`
2. Backend processes files entirely in memory (no disk storage)
3. PDFs converted to images using `pypdfium2` (300 DPI) in memory
4. Images sent to Groq Llama 3.1 8B (primary) or Claude 4 Opus (fallback)
5. System validates extraction using French business rules (SIRET, TVA)
6. Data stored encrypted in database with GDPR audit logging
7. Files discarded immediately after processing (data minimization)

### Dual AI Processing System
- **Primary**: Groq Llama 3.1 8B (`backend/core/ai/groq_processor.py`) - Fast, cost-effective text processing
- **Fallback**: Claude 4 Opus vision (`backend/core/ai/claude_processor.py`) - Multimodal for complex invoices
- **Smart routing**: Text extraction first, vision processing only when needed

### French Compliance Architecture
- **SIRET/SIREN Validation**: Real-time INSEE API integration
- **TVA Rate Validation**: French tax rate compliance (20%, 10%, 5.5%, 2.1%)
- **Export Formats**: Sage PNM, EBP ASCII, Ciel XIMPORT, FEC (French accounting software)
- **Duplicate Detection**: Intelligent duplicate handling using supplier SIRET + invoice number
- **Data Localization**: French localization with proper terminology (uses "Importer" not "Téléverser")

### GDPR-Compliant Data Processing
- **Memory-Only Processing**: Files never stored unencrypted on disk
- **Audit Logging**: All operations logged for GDPR compliance
- **Data Subject Rights**: Full GDPR rights implementation (access, rectification, erasure, portability)
- **Encryption**: AES-256 encryption for sensitive data at rest
- **International Transfer Compliance**: Risk assessment for Claude API usage

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

### Docker Development (Recommended)
```bash
# Start all services (includes PostgreSQL, Redis)
docker-compose up -d

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f redis

# Stop all services
docker-compose down

# Rebuild after changes (if requirements.txt or package.json changed)
docker-compose build backend  # If backend dependencies changed
docker-compose build frontend # If frontend dependencies changed
docker-compose up -d --build

# Production deployment with monitoring
docker-compose -f docker-compose.prod.yml up -d
```

### Database Operations
```bash
cd backend
# Create migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Apply pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Reset database (CAUTION: destroys all data)
alembic downgrade base && alembic upgrade head
```

### Testing and Debugging
```bash
# Run manual tests (located in tests/ directory)
cd tests
python test_simple_post.py                    # Test basic invoice processing
python test_siret_validation_complete.py      # Test SIRET validation
python test_batch_debug.py                    # Test batch processing
python test_frontend_specific.py              # Test frontend integration

# Frontend type checking
cd frontend
npx tsc --noEmit

# Frontend linting
npm run lint

# Database debugging
cd backend
python -c "from core.database import engine; print('DB connection test passed')"
```

## Environment Configuration

### Backend Required Variables (.env)
```bash
# AI Processing (choose one or both)
ANTHROPIC_API_KEY=sk-ant-...              # For Claude 4 Opus fallback
GROQ_API_KEY=gsk_...                      # Primary AI processor (Llama 3.1 8B)

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/comptaflow
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ENCRYPTION_KEY=your-32-byte-encryption-key-for-gdpr-compliance

# French Compliance
INSEE_API_KEY=your-insee-api-key           # For SIRET validation
INSEE_API_SECRET=your-insee-api-secret

# Payment Processing (Production)
STRIPE_SECRET_KEY=sk_live_...              # Stripe secret key
STRIPE_PUBLISHABLE_KEY=pk_live_...         # Stripe publishable key
STRIPE_WEBHOOK_SECRET=whsec_...            # Stripe webhook secret

# Cloud Storage (Production)
AWS_ACCESS_KEY_ID=your-aws-access-key      # For S3 backups
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_BUCKET_NAME=comptaflow-backups
AWS_REGION=eu-west-3                       # Paris region

# Processing Configuration
AI_MODEL=llama-3.1-8b-instant             # Groq model
MAX_TOKENS=8192
PDF_DPI=300
MAX_PAGES=10
MAX_FILE_SIZE=10485760                     # 10MB limit

# GDPR Compliance
STORAGE_BACKEND=memory                     # CRITICAL: Never change to "file"
GDPR_MASTER_KEY=your-gdpr-encryption-key   # For GDPR data encryption
```

### Frontend Variables (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...    # Stripe publishable key for payments
```

## Critical Architecture Understanding

### Memory-Only File Processing
**NEVER** introduce file storage. The system is designed for GDPR compliance:
- Files processed in `process_invoice_task_memory()` 
- Content passed as `bytes` through the processing pipeline
- Immediately discarded after database storage

### Duplicate Detection System
Located in `backend/core/duplicate_detector.py`:
- **File-level**: SHA-256 hash comparison
- **Invoice-level**: Supplier SIRET + invoice number uniqueness
- **French business logic**: Handles legitimate reprocessing scenarios
- **Batch processing**: User choice handling for bulk uploads

### Export System Architecture
Multiple French accounting software formats:
- **CSV**: Simplified 15-column format for French accountants
- **Sage PNM**: Plan Comptable Général integration
- **EBP ASCII**: EBP Comptabilité format
- **Ciel XIMPORT**: Ciel Comptabilité format  
- **FEC**: Administration Fiscale compliance format

### French Validation Pipeline
1. **SIRET/SIREN**: INSEE API real-time validation
2. **TVA Rates**: French tax compliance checking
3. **Sequential Numbering**: French invoice numbering rules
4. **Address Format**: French postal code validation
5. **Business Identifiers**: RCS, NAF/APE code validation

## Important Code Locations

### Backend Core
- `backend/main.py` - FastAPI app with ComptaFlowException handling
- `backend/core/config.py` - Settings with GDPR-compliant storage config
- `backend/core/database.py` - Async database sessions
- `backend/core/exceptions.py` - ComptaFlowException system (renamed from InvoiceAI)

### Production Features (NEW)
- `backend/core/auth/jwt_auth.py` - JWT authentication with subscription integration
- `backend/core/quota_manager.py` - Invoice quota tracking and enforcement
- `backend/core/rate_limiter.py` - Redis-based rate limiting by subscription tier
- `backend/core/stripe_manager.py` - Complete Stripe payment integration
- `backend/core/monitoring.py` - Production monitoring and health checks
- `backend/models/subscription.py` - Subscription and pricing tier models

### AI Processing (Dual System)
- `backend/core/ai/groq_processor.py` - Primary AI (Llama 3.1 8B, fast/cheap)
- `backend/core/ai/claude_processor.py` - Fallback AI (Claude 4 Opus, vision)
- `backend/core/pdf_processor.py` - Memory-based PDF to image conversion

### API Endpoints
- `backend/api/invoices.py` - GDPR-compliant upload/processing (uses memory-only)
- `backend/api/payments.py` - Stripe payment endpoints and webhooks
- `backend/api/subscription.py` - Subscription management endpoints
- `backend/api/auth.py` - Authentication endpoints with JWT
- `backend/api/batch_processing.py` - Bulk upload with duplicate detection
- `backend/api/export_routes.py` - Multi-format export system
- `backend/api/exports/` - Individual format exporters (Sage, EBP, Ciel, FEC)

### French Compliance
- `backend/core/validation/french_validator.py` - French business rule validation
- `backend/core/validation/siret_validation_service.py` - INSEE API integration
- `backend/core/french_compliance/insee_client.py` - Professional INSEE API client
- `backend/core/duplicate_detector.py` - Smart duplicate detection
- `backend/models/siret_validation.py` - SIRET validation tracking

### GDPR Compliance
- `backend/core/gdpr_*` - GDPR audit, encryption, transfer compliance
- `backend/api/gdpr_rights.py` - Data subject rights endpoints
- `backend/models/gdpr_models.py` - GDPR-compliant database models
- `backend/crud/audit_log.py` - Audit logging for compliance

### Frontend (Production-Ready)
- `frontend/lib/french-localization.ts` - Complete French translations
- `frontend/lib/api.ts` - API client with authentication
- `frontend/components/subscription/` - Subscription management UI components
- `frontend/components/invoice/batch-upload.tsx` - Bulk processing UI
- `frontend/app/dashboard/page.tsx` - Main invoice management interface
- `frontend/app/subscription/page.tsx` - Subscription and billing management
- `frontend/app/support/page.tsx` - Customer support portal
- `frontend/app/legal/` - GDPR-compliant legal pages (privacy, terms)

## Current Implementation Status

### ✅ Completed Features
- **GDPR-Compliant Processing**: Memory-only file processing, no disk storage
- **Dual AI System**: Groq primary + Claude fallback processing
- **French Compliance**: SIRET validation, TVA rates, export formats
- **Duplicate Detection**: Smart file and invoice-level duplicate handling
- **Multi-Format Export**: CSV, Sage PNM, EBP, Ciel, FEC formats
- **Batch Processing**: Bulk upload with duplicate resolution
- **Comprehensive Validation**: French business rules and error handling
- **Audit Logging**: Full GDPR audit trail
- **French Localization**: Complete French UI with proper terminology

### 🎯 Production System Status
**✅ All production features are now fully implemented and operational:**
- **Authentication System**: JWT-based authentication with subscription integration
- **Subscription Management**: 4-tier pricing (Free, Pro, Business, Enterprise) with Stripe
- **Rate Limiting**: Redis-based rate limiting by subscription tier
- **Payment Processing**: Complete Stripe integration with webhooks
- **Monitoring & Health**: Production monitoring with backup systems
- **GDPR Compliance**: Legal pages and data protection measures
- **Customer Support**: Support portal and FAQ system

### 🚀 Production-Ready Architecture
- **Subscription Tiers**: Free (10/month), Pro (€29/500), Business (€59/2000), Enterprise (€99/unlimited)
- **Quota Enforcement**: Real-time invoice processing limits by subscription tier
- **Payment Integration**: Stripe checkout sessions, webhooks, and subscription management
- **Production Deployment**: Nginx reverse proxy, SSL, Docker containerization
- **Backup Strategy**: Automated S3 backups and disaster recovery
- **Monitoring**: System health checks and metrics collection

## French Market Specifics

### Accounting Software Integration
- **Sage 100**: PNM format export with Plan Comptable Général
- **EBP Comptabilité**: ASCII format with account mapping
- **Ciel Comptabilité**: XIMPORT format
- **Administration Fiscale**: FEC format for tax compliance

### Business Validation Rules
- **SIRET**: 14-digit identifier validation via INSEE API
- **SIREN**: 9-digit company identifier validation
- **TVA Intracommunautaire**: Format FR + 11 digits
- **Sequential Numbering**: French invoice numbering requirements
- **TVA Rates**: 20% (normal), 10% (reduced), 5.5% (special), 2.1% (super-reduced)

## Debugging and Troubleshooting

### Common Issues
- **Memory errors**: Check file size limits (10MB max)
- **AI processing failures**: Verify GROQ_API_KEY and ANTHROPIC_API_KEY
- **SIRET validation errors**: Check INSEE_API_KEY credentials
- **Database connection**: Ensure PostgreSQL is running via Docker
- **File processing errors**: Verify PDF is not corrupted, use tests/test_simple_post.py
- **Authentication errors**: Check JWT token expiration and subscription status
- **Payment failures**: Verify Stripe keys and webhook endpoint configuration
- **Quota exceeded**: Check subscription limits and usage in dashboard
- **Container startup fails**: Verify all required dependencies in requirements.txt

### Debugging Commands
```bash
# Check API health and subscription system
curl http://localhost:8000/health
curl http://localhost:8000/api/auth/health

# Test database connection
cd backend && python -c "from core.database import async_session_maker; print('DB OK')"

# View processing logs
docker-compose logs -f backend | grep "invoice"
docker-compose logs -f backend | grep "subscription"
docker-compose logs -f backend | grep "stripe"

# Test specific components
cd tests && python test_siret_validation_complete.py
cd tests && python test_simple_post.py

# Debug frontend with detailed logging
cd frontend && npm run dev

# Test Stripe webhooks (in development)
stripe listen --forward-to localhost:8000/api/payments/webhook

# Monitor system resources and quota usage
curl http://localhost:8000/api/monitoring/health
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/subscription/usage
```

### Performance Monitoring
- **Groq Processing**: ~0.5-2 seconds per invoice, very low cost
- **Claude Fallback**: ~3-8 seconds per invoice, higher cost but better accuracy
- **SIRET Validation**: ~200-500ms per validation via INSEE API
- **Memory Usage**: Monitor for large batch processing operations

## Cost Optimization & Pricing Strategy
- **Groq Llama 3.1 8B**: Primary processor, extremely low cost (~$0.0001 per invoice)
- **Claude 4 Opus**: Fallback only, ~$0.015-0.03 per invoice page
- **INSEE API**: Free for reasonable usage, monitor rate limits
- **Memory processing**: No storage costs, faster processing
- **Subscription Revenue**: €29-99/month tiers provide healthy margins over processing costs
- **Stripe Fees**: 2.9% + €0.25 per transaction (factored into pricing)

## Production Infrastructure
- **Nginx**: Reverse proxy with SSL termination, rate limiting, and CORS handling
- **PostgreSQL**: Primary database with automated S3 backups
- **Redis**: Caching, rate limiting, and session storage
- **Docker**: Multi-container orchestration for development and production
- **Monitoring**: Prometheus metrics with Grafana dashboards (optional)
- **Security**: AES-256 encryption, GDPR audit trails, secure key management