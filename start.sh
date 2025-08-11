#!/bin/bash

echo "========================================="
echo "AI Workspace - Installing Dependencies"
echo "========================================="

# Install required packages
echo "Installing SQLAlchemy dependencies..."
pip install sqlalchemy aiosqlite asyncpg

echo ""
echo "========================================="
echo "Starting Application"
echo "========================================="
echo ""
echo "Login credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "========================================="

# Run the application
chainlit run app.py
