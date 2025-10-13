#!/bin/bash
# Test authentication endpoints

echo "Testing authentication endpoints..."

echo "1. Auth health check:"
curl -s http://localhost:8000/auth/health

echo -e "\n2. Test signup:"
curl -s -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "testpass123", "contact": "555-1234"}'

echo -e "\n3. Test login:"
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

echo -e "\n4. Test public URL auth health:"
curl -s https://themachine.vernalcontentum.com/auth/health
