# Phase 1 & 2 Testing Guide

## ✅ Phase 1 & 2 Complete!

### What Was Created:
1. **Docker Infrastructure**: PostgreSQL 17 + Adminer
2. **Database Models**: Guest, ScanBatch, ScanImage, SeedDetection
3. **Alembic Migrations**: Code-first migration system ready
4. **Dependencies**: psycopg3, SQLAlchemy 2.x, Alembic

---

## 🧪 Testing Phase 1 & 2

### Step 1: Start Docker Services

```bash
cd /mnt/shared_data/FCAI/GP/project/seed-bank
docker-compose up -d postgres adminer
```

**Expected Output:**
- PostgreSQL container starts and becomes healthy
- Adminer container starts
- Both services accessible

**Verify:**
```bash
docker-compose ps
# Should show postgres and adminer as "Up" and "healthy"
```

---

### Step 2: Create .env File

```bash
cp env.example .env
# Edit .env if needed (defaults should work)
```

---

### Step 3: Install Dependencies (if not in Docker)

```bash
pip install -r requirements.txt
```

**Verify:**
```bash
python -c "import psycopg; import sqlalchemy; import alembic; print('All imports OK')"
```

---

### Step 4: Run Database Migrations

```bash
# Set DATABASE_URL if not using .env
export DATABASE_URL="postgresql://seedbank:seedbank_dev_password@localhost:5432/seedbank_db"

# Run migrations
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema, Initial migration
```

---

### Step 5: Verify Database Schema in Adminer

1. **Open Adminer**: http://localhost:8081
2. **Login**:
   - System: PostgreSQL
   - Server: postgres
   - Username: seedbank
   - Password: seedbank_dev_password
   - Database: seedbank_db
3. **Verify Tables Exist**:
   - Click "seedbank_db" database
   - Should see 4 tables:
     - `guests`
     - `scan_batches`
     - `scan_images`
     - `seed_detections`
4. **Check Schema**:
   - Click on each table to verify columns match the models
   - Check indexes are created
   - Verify foreign keys

---

### Step 6: Test Database Connection from Python

```bash
python -c "
from app.database import engine, SessionLocal
from app.models import Guest, ScanBatch
from sqlalchemy import text

# Test connection
with engine.connect() as conn:
    result = conn.execute(text('SELECT version()'))
    print('PostgreSQL Version:', result.fetchone()[0])

# Test session
db = SessionLocal()
try:
    count = db.query(Guest).count()
    print(f'Guests table exists! Current count: {count}')
finally:
    db.close()
print('✅ Database connection successful!')
"
```

**Expected Output:**
```
PostgreSQL Version: PostgreSQL 17.x ...
Guests table exists! Current count: 0
✅ Database connection successful!
```

---

## ✅ Success Criteria

- [ ] Docker containers start successfully
- [ ] Adminer accessible at http://localhost:8081
- [ ] Can login to Adminer with credentials
- [ ] All 4 tables exist in database
- [ ] Tables have correct columns and indexes
- [ ] Python can connect to database
- [ ] Can query tables from Python

---

## 🐛 Troubleshooting

### Issue: Docker containers won't start
- Check if ports 5432 or 8081 are already in use
- Try: `docker-compose down` then `docker-compose up -d`

### Issue: Migration fails
- Check DATABASE_URL is correct
- Verify PostgreSQL is running: `docker-compose ps`
- Check logs: `docker-compose logs postgres`

### Issue: Can't connect from Python
- Verify DATABASE_URL matches docker-compose.yml
- Check if using `localhost` (for local) or `postgres` (for Docker)
- Test connection: `psql -h localhost -U seedbank -d seedbank_db`

---

## 📝 Next Steps

Once Phase 1 & 2 testing passes, we'll proceed to **Phase 3: Integration** where we'll:
- Add persistence to existing API endpoints
- Implement image storage
- Test end-to-end flow

**Ready to test? Let me know the results!**

