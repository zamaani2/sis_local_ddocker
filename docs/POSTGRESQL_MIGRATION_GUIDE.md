# PostgreSQL Migration Guide

This guide will help you migrate your Django SchoolApp from MySQL to PostgreSQL.

## Overview

The following changes have been made to support PostgreSQL:

1. **Requirements**: Replaced `pymysql` with `psycopg2-binary`
2. **Django Settings**: Updated database configuration to use PostgreSQL
3. **Docker Configuration**: Updated docker-compose.yml and Dockerfile for PostgreSQL
4. **Environment Variables**: Updated env.example with PostgreSQL settings

## Prerequisites

- Docker and Docker Compose installed
- Backup of your existing MySQL database (if migrating existing data)
- PostgreSQL client tools (optional, for manual database operations)

## Migration Steps

### Step 1: Backup Existing Data (if applicable)

If you have existing data in MySQL that you want to preserve:

```bash
# Export data from MySQL
mysqldump -u root -p multi_sis_database > backup.sql

# Or if using Docker:
docker exec schoolapp_mysql mysqldump -u root -p multi_sis_database > backup.sql
```

### Step 2: Update Environment Configuration

1. Copy the updated environment file:

   ```bash
   cp env.example .env
   ```

2. Update your `.env` file with PostgreSQL settings:
   ```env
   # Database Configuration (PostgreSQL)
   DB_NAME=multi_sis_database
   DB_USER=postgres
   DB_PASSWORD=your-secure-postgres-password
   DB_HOST=db
   DB_PORT=5432
   ```

### Step 3: Stop Existing Services

```bash
# Stop and remove existing containers
docker-compose down

# Remove old MySQL volume (optional - this will delete all MySQL data)
docker volume rm pgredschoolapp_mysql_data
```

### Step 4: Install New Dependencies

```bash
# Install PostgreSQL dependencies
pip install psycopg2-binary

# Or if using Docker, rebuild the image
docker-compose build
```

### Step 5: Start PostgreSQL Services

```bash
# Start PostgreSQL database
docker-compose up -d db

# Wait for PostgreSQL to be ready
docker-compose logs -f db
```

### Step 6: Run Database Migrations

```bash
# Run Django migrations
python manage.py migrate

# Or if using Docker:
docker-compose exec django python manage.py migrate
```

### Step 7: Create Superuser (if needed)

```bash
# Create a superuser
python manage.py createsuperuser

# Or if using Docker:
docker-compose exec django python manage.py createsuperuser
```

### Step 8: Start All Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

## Data Migration (if migrating from MySQL)

If you need to migrate existing data from MySQL to PostgreSQL:

### Option 1: Using Django's dumpdata/loaddata

```bash
# Export data from MySQL (run with MySQL settings)
python manage.py dumpdata --natural-foreign --natural-primary > data.json

# Switch to PostgreSQL settings and load data
python manage.py loaddata data.json
```

### Option 2: Using pgloader (Advanced)

1. Install pgloader:

   ```bash
   # On Ubuntu/Debian
   sudo apt-get install pgloader

   # On macOS
   brew install pgloader
   ```

2. Create a migration script:

   ```sql
   LOAD DATABASE
       FROM mysql://root:password@localhost:3306/multi_sis_database
       INTO postgresql://postgres:password@localhost:5432/multi_sis_database

   WITH include drop, create tables, create indexes, reset sequences

   SET work_mem to '256MB', maintenance_work_mem to '512 MB';
   ```

3. Run the migration:
   ```bash
   pgloader migration.script
   ```

## Verification

### Check Database Connection

```bash
# Test database connection
python manage.py dbshell

# Or using Docker:
docker-compose exec django python manage.py dbshell
```

### Verify Data Integrity

```bash
# Check if migrations were applied
python manage.py showmigrations

# Run Django checks
python manage.py check
```

## Troubleshooting

### Common Issues

1. **Connection Refused**

   - Ensure PostgreSQL container is running: `docker-compose ps`
   - Check if port 5432 is available
   - Verify environment variables in `.env`

2. **Permission Denied**

   - Check PostgreSQL user permissions
   - Ensure database exists and user has access

3. **Migration Errors**

   - Run `python manage.py migrate --fake-initial` if needed
   - Check for conflicting migrations

4. **Data Type Issues**
   - PostgreSQL is stricter about data types than MySQL
   - Some MySQL-specific features may need adjustment

### Useful Commands

```bash
# View PostgreSQL logs
docker-compose logs db

# Access PostgreSQL shell
docker-compose exec db psql -U postgres -d multi_sis_database

# Reset database (WARNING: This deletes all data)
docker-compose exec django python manage.py flush

# Create fresh migrations
python manage.py makemigrations
python manage.py migrate
```

## Performance Considerations

PostgreSQL offers several advantages over MySQL:

1. **Better JSON Support**: Native JSON data types
2. **Advanced Indexing**: GIN, GiST, and other index types
3. **Better Concurrency**: MVCC (Multi-Version Concurrency Control)
4. **Extensibility**: Custom data types and functions

### Recommended PostgreSQL Settings

For production, consider these PostgreSQL configuration optimizations:

```sql
-- In postgresql.conf or via environment variables
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

## Rollback Plan

If you need to rollback to MySQL:

1. Stop PostgreSQL services: `docker-compose down`
2. Restore MySQL configuration in settings.py
3. Update requirements.txt to use pymysql
4. Update docker-compose.yml for MySQL
5. Restore from MySQL backup

## Support

For issues specific to PostgreSQL migration:

1. Check Django PostgreSQL documentation
2. Review PostgreSQL logs: `docker-compose logs db`
3. Verify Django settings: `python manage.py check --deploy`

## Next Steps

After successful migration:

1. Update any custom SQL queries for PostgreSQL syntax
2. Test all application functionality
3. Update documentation and deployment scripts
4. Consider PostgreSQL-specific optimizations
5. Set up regular backups using `pg_dump`

---

**Note**: This migration guide assumes you're using Docker. For non-Docker deployments, adjust the commands accordingly and ensure PostgreSQL is installed locally.

