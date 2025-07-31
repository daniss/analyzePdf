# ComptaFlow MVP Setup Guide 🚀

Quick setup guide to get ComptaFlow running for the French market MVP.

## Prerequisites

- Docker & Docker Compose installed
- Groq API key (required)
- INSEE API credentials (optional but recommended)

## 1. Configure Environment (2 minutes)

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys:
# - GROQ_API_KEY (REQUIRED) - Get from https://console.groq.com/
# - INSEE_API_KEY (optional) - For SIRET validation
```

**Minimum required change in .env:**
```
GROQ_API_KEY=gsk_your-actual-groq-api-key-here
```

## 2. Start Services (5 minutes)

```bash
# Start all services with Docker Compose
docker-compose up -d

# Wait for services to be healthy (about 30 seconds)
docker-compose ps
```

## 3. Initialize Database (2 minutes)

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Initialize French TVA reference data
docker-compose exec backend python scripts/init_tva_data.py

# Create a demo user (optional)
docker-compose exec backend python scripts/create_demo_user.py
```

## 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432 (user: postgres)

## 5. Test the MVP

1. **Register an account** at http://localhost:3000/auth/signup
2. **Upload a PDF invoice** (French invoices work best)
3. **Review extracted data** with SIRET validation
4. **Export to Sage/EBP** format

## Quick Troubleshooting

### "Groq API key not configured" error
- Make sure you added your actual Groq API key in .env
- Restart backend: `docker-compose restart backend`

### Database connection errors
- Check if PostgreSQL is running: `docker-compose ps postgres`
- Check logs: `docker-compose logs postgres`

### Cannot access frontend
- Check if port 3000 is free: `lsof -i :3000`
- Check frontend logs: `docker-compose logs frontend`

## Production Deployment

For production on a French VPS:

1. **Get a VPS** (OVH, Scaleway, etc.) with 4GB RAM minimum
2. **Install Docker** on the VPS
3. **Clone the repository** to the VPS
4. **Configure production .env** with strong passwords
5. **Add SSL** with nginx-proxy or Traefik
6. **Point your domain** to the VPS IP

```bash
# Production start command
docker-compose -f docker-compose.yml up -d
```

## Support

- Check logs: `docker-compose logs -f [service]`
- Reset everything: `docker-compose down -v && docker-compose up -d`
- Database backup: `docker-compose exec postgres pg_dump -U postgres comptaflow > backup.sql`

---

**Ready to process French invoices in 10 minutes! 🇫🇷**