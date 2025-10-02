# Backend API Specification for Campaign Management

## Overview
This document specifies the required API endpoints for campaign management functionality. The current external API at `https://themachine.vernalcontentum.com` is missing several critical endpoints that are needed for full campaign CRUD operations.

## Current Status
- ✅ `GET /campaigns` - Fetch all campaigns (working)
- ✅ `DELETE /campaigns/{id}` - Delete campaign (working)
- ✅ `GET /campaigns/{id}/raw_data` - Get campaign details (working)
- ❌ `POST /campaigns` - Create new campaign (MISSING)
- ❌ `PUT /campaigns/{id}` - Update campaign (MISSING)

## Required Endpoints

### 1. Create Campaign
**Endpoint:** `POST /campaigns`

**Request Body:**
```json
{
  "name": "Campaign Name",
  "description": "Campaign description",
  "type": "keyword" | "url" | "trending",
  "keywords": ["keyword1", "keyword2"], // Optional, required if type is "keyword"
  "urls": ["https://example.com"], // Optional, required if type is "url"
  "trendingTopics": ["topic1", "topic2"], // Optional, required if type is "trending"
  "topics": ["topic1", "topic2"], // Optional
  "extractionSettings": { // Optional
    "webScrapingDepth": 2,
    "includeImages": true,
    "includeLinks": true,
    "maxPages": 20,
    "batchSize": 10
  },
  "preprocessingSettings": { // Optional
    "removeStopwords": true,
    "stemming": true,
    "lemmatization": true,
    "caseSensitive": false
  },
  "entitySettings": { // Optional
    "extractPersons": true,
    "extractOrganizations": true,
    "extractLocations": true,
    "extractDates": true,
    "confidenceThreshold": 0.7
  },
  "modelingSettings": { // Optional
    "algorithm": "lda",
    "numTopics": 5,
    "iterations": 100,
    "passThreshold": 0.5
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": {
    "id": "generated-campaign-id",
    "name": "Campaign Name",
    "description": "Campaign description",
    "type": "keyword",
    "keywords": ["keyword1", "keyword2"],
    "createdAt": "2025-01-01T00:00:00Z",
    "updatedAt": "2025-01-01T00:00:00Z",
    // ... other fields
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Error description"
}
```

### 2. Update Campaign
**Endpoint:** `PUT /campaigns/{id}`

**Request Body:** Same as POST, but all fields are optional (partial update)

**Response:**
```json
{
  "status": "success",
  "message": {
    "id": "campaign-id",
    "name": "Updated Campaign Name",
    "description": "Updated description",
    "type": "keyword",
    "keywords": ["updated", "keywords"],
    "createdAt": "2025-01-01T00:00:00Z",
    "updatedAt": "2025-01-01T00:00:00Z",
    // ... other fields
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Campaign not found" // or other error message
}
```

## Database Schema

### Campaigns Table
```sql
CREATE TABLE campaigns (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type ENUM('keyword', 'url', 'trending') NOT NULL,
    keywords JSON, -- Array of strings
    urls JSON, -- Array of strings
    trending_topics JSON, -- Array of strings
    topics JSON, -- Array of strings
    extraction_settings JSON,
    preprocessing_settings JSON,
    entity_settings JSON,
    modeling_settings JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    user_id VARCHAR(255), -- Optional: for user-specific campaigns
    INDEX idx_user_id (user_id),
    INDEX idx_type (type),
    INDEX idx_created_at (created_at)
);
```

## Implementation Notes

1. **Authentication:** All endpoints should require valid JWT authentication
2. **User Isolation:** Campaigns should be associated with the authenticated user
3. **Validation:** 
   - `name` and `type` are required
   - `keywords` required if `type` is "keyword"
   - `urls` required if `type` is "url"
   - `trendingTopics` required if `type` is "trending"
4. **ID Generation:** Use UUID or timestamp-based IDs
5. **Timestamps:** Use ISO 8601 format for dates
6. **Error Handling:** Return consistent error format with appropriate HTTP status codes

## Testing

### Test Create Campaign
```bash
curl -X POST https://themachine.vernalcontentum.com/campaigns \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Test Campaign",
    "description": "Test description",
    "type": "keyword",
    "keywords": ["test", "campaign"]
  }'
```

### Test Update Campaign
```bash
curl -X PUT https://themachine.vernalcontentum.com/campaigns/CAMPAIGN_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Updated Campaign Name",
    "description": "Updated description"
  }'
```

## Current Workaround

Until these endpoints are implemented, the application uses:
1. **Next.js API Routes** (`/api/campaigns/*`) as a temporary solution
2. **In-memory database** for development/testing
3. **Automatic fallback** to external API for existing campaigns

Once the backend endpoints are ready, simply update the `Service.tsx` file to use the external API URLs instead of the local API routes.
