# Deployment Guide

## Option 1: Render.com (Recommended - Free, No Credit Card)

### Step 1: Create Database on Neon (Free PostgreSQL)
1. Go to [neon.tech](https://neon.tech) and sign up (free, no credit card)
2. Create a new project → choose region closest to your users
3. Get your **pooled connection string**:
   ```
   postgresql://user:password@ep-xxx-pooler.region.aws.neon.tech/dbname?sslmode=require
   ```
4. Save this — you'll need it for Render

### Step 2: Deploy to Render
1. Push this repo to GitHub
2. Go to [render.com](https://render.com) and sign up with GitHub
3. Click **New +** → **Web Service**
4. Connect your GitHub repo
5. Configure:
   - **Name**: `codevector-api`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variable:
   - `DATABASE_URL` = your Neon pooled connection string
7. Click **Create Web Service**

### Step 3: Seed the Database
Once deployed, run the seed script:
```bash
# Install dependencies locally
pip install -r requirements.txt

# Set your Neon connection string
export DATABASE_URL="postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/dbname?sslmode=require"

# Run seed
python scripts/seed.py --count 200000
```

Your app will be live at `https://codevector-api.onrender.com`

---

## Option 2: Docker + Docker Compose (Local Development)

```bash
# Start everything
docker-compose up --build

# Seed the database (in another terminal)
docker-compose exec app python scripts/seed.py --count 200000

# App runs at http://localhost:8000
```

---

## Option 3: Railway (Alternative)

1. Push to GitHub
2. Go to [railway.app](https://railway.app)
3. New Project → Deploy from GitHub repo
4. Add PostgreSQL plugin
5. Set `DATABASE_URL` environment variable
6. Deploy

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SEED_COUNT` | No | Number of products to generate (default: 200000) |

## Connection String Format

```
# Neon (recommended for serverless)
postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/dbname?sslmode=require

# Local PostgreSQL
postgresql://user:pass@localhost:5432/codevector

# Render managed PostgreSQL
postgresql://user:pass@host.render.com:5432/dbname
```
