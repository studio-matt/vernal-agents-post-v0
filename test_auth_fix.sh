#!/bin/bash
# Test the auth endpoint fix

echo "Testing auth endpoints after frontend fix..."

echo "1. Test auth health:"
curl -s http://localhost:8000/auth/health

echo -e "\n2. Test signup endpoint:"
curl -s -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "testpass123", "contact": "555-1234"}'

echo -e "\n3. Test login endpoint:"
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

echo -e "\n4. Test public URL auth health:"
curl -s https://themachine.vernalcontentum.com/auth/health

echo -e "\n5. Test public URL signup:"
curl -s -X POST https://themachine.vernalcontentum.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username": "publictest", "email": "public@example.com", "password": "testpass123", "contact": "555-5678"}'
