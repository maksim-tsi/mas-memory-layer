#!/bin/bash
# 
# Database Setup Script for mas-memory-layer
# Creates the dedicated 'mas_memory' PostgreSQL database
#
# Usage: ./scripts/setup_database.sh
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================"
echo "mas-memory-layer Database Setup"
echo "======================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create .env file with database credentials."
    echo "See .env.example for reference."
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Determine Host (support both legacy DEV_IP and new POSTGRES_HOST/DATA_NODE_IP)
HOST="${POSTGRES_HOST:-${DATA_NODE_IP:-$DEV_IP}}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Host: ${HOST}"
echo "  Port: ${POSTGRES_PORT}"
echo "  User: ${POSTGRES_USER}"
echo "  Database: mas_memory"
echo ""

# Construct base connection URL (to postgres database)
BASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${HOST}:${POSTGRES_PORT}/postgres"

# Check if database already exists
echo -e "${YELLOW}Checking if database 'mas_memory' exists...${NC}"
DB_EXISTS=$(psql "$BASE_URL" -tAc "SELECT 1 FROM pg_database WHERE datname='mas_memory'" || echo "0")

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${YELLOW}Database 'mas_memory' already exists.${NC}"
    read -p "Do you want to drop and recreate it? (yes/no): " -r
    echo
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${RED}Dropping database 'mas_memory'...${NC}"
        psql "$BASE_URL" -c "DROP DATABASE mas_memory;" || {
            echo -e "${RED}Failed to drop database. It may be in use.${NC}"
            echo "Try closing all connections and run this script again."
            exit 1
        }
        echo -e "${GREEN}Database dropped successfully.${NC}"
    else
        echo -e "${YELLOW}Skipping database creation.${NC}"
        exit 0
    fi
fi

# Create the database
echo -e "${YELLOW}Creating database 'mas_memory'...${NC}"
psql "$BASE_URL" -c "CREATE DATABASE mas_memory;" || {
    echo -e "${RED}Failed to create database!${NC}"
    exit 1
}

echo -e "${GREEN}✓ Database 'mas_memory' created successfully!${NC}"
echo ""

# Verify creation
echo -e "${YELLOW}Verifying database creation...${NC}"
psql "$BASE_URL" -c "\l mas_memory"

echo ""
echo -e "${GREEN}======================================"
echo "Database Setup Complete!"
echo "======================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Update your .env file if needed:"
echo "     POSTGRES_DB=mas_memory"
echo "     POSTGRES_URL=postgresql://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@\${DEV_IP}:\${POSTGRES_PORT}/mas_memory"
echo ""
echo "  2. Run database migrations:"
echo "     psql \"\$POSTGRES_URL\" -f migrations/001_active_context.sql"
echo ""
echo "  3. Test connection:"
echo "     psql \"\$POSTGRES_URL\" -c \"SELECT current_database();\""
echo ""
