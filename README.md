<<<<<<< HEAD
# MultiAgent
=======
# Vernal Contentum - Production Setup Guide

## Overview
This project is a content management and generation platform with campaign management, author personality features, and scheduled posting capabilities.

## Database Setup Required for Live Deployment

### Campaign Management Integration

The application now includes full campaign management with database integration. The following setup is required for production:

#### 1. Campaign Database Table/Collection

Create the following table in your database:

```sql
-- MySQL/PostgreSQL
CREATE TABLE campaigns (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    query TEXT, -- Additional context field
    type ENUM('keyword', 'url', 'trending') NOT NULL,
    keywords JSON, -- Array of strings
    urls JSON, -- Array of strings
    trending_topics JSON, -- Array of strings
    topics JSON, -- Array of strings
    status ENUM('INCOMPLETE', 'PROCESSING', 'READY_TO_ACTIVATE', 'ACTIVE') DEFAULT 'INCOMPLETE',
    extraction_settings JSON,
    preprocessing_settings JSON,
    entity_settings JSON,
    modeling_settings JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    user_id VARCHAR(255), -- Optional: for user-specific campaigns
    INDEX idx_user_id (user_id),
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- MongoDB (if using NoSQL)
{
  "_id": ObjectId,
  "name": String,
  "description": String,
  "query": String, // Additional context field
  "type": String, // "keyword", "url", or "trending"
  "keywords": [String],
  "urls": [String],
  "trendingTopics": [String],
  "topics": [String],
    "status": String, // "INCOMPLETE", "PROCESSING", "READY_TO_ACTIVATE", or "ACTIVE"
  "extractionSettings": Object,
  "preprocessingSettings": Object,
  "entitySettings": Object,
  "modelingSettings": Object,
  "createdAt": Date,
  "updatedAt": Date,
  "userId": String // Optional: for user-specific campaigns
}
```

#### 2. Campaign API Endpoints

Implement the following API endpoints in your backend:

```
GET    /campaigns              - Fetch all campaigns
POST   /campaigns              - Create new campaign
GET    /campaigns/{id}         - Get specific campaign
PUT    /campaigns/{id}         - Update campaign
DELETE /campaigns/{id}         - Delete campaign
```

#### 3. Progress Tracking System

The application includes real-time progress tracking for campaign analysis. The following setup is required:

**Database Fields for Progress Tracking:**
```sql
-- Add these fields to the campaigns table
ALTER TABLE campaigns ADD COLUMN progress INT DEFAULT 0; -- 0-100
ALTER TABLE campaigns ADD COLUMN current_step VARCHAR(255); -- Current processing step
ALTER TABLE campaigns ADD COLUMN progress_message TEXT; -- Progress description
ALTER TABLE campaigns ADD COLUMN task_id VARCHAR(255); -- Background task ID
```

**Progress Tracking API Endpoints:**
```
POST   /analyze                - Start analysis (returns task_id)
GET    /analyze/status/{task_id} - Get real-time progress
```

**Progress Tracking Implementation:**
- **Real-time polling**: Frontend polls every 2 seconds for progress updates
- **Meaningful increments**: Progress jumps in steps (5%, 15%, 25%, 50%, 70%, 85%, 90%, 100%)
- **Fallback system**: If API unavailable, uses time-based progress estimation
- **Persistent state**: Progress persists across page refreshes and login sessions

**Progress Steps:**
- 5% - Validating input parameters
- 15% - Setting up web scraping
- 25% - Web scraping in progress
- 50% - Scraping completed
- 60% - Processing scraped content
- 70% - Analyzing topics and extracting entities
- 80% - Extracting entities and processing text
- 90% - Storing results in database
- 100% - Analysis completed successfully

**Progress Tracking API Response Format:**

```typescript
// POST /analyze
Request Body:
{
  "campaign_name": "Test Campaign",
  "campaign_id": "campaign-123",
  "urls": ["https://example.com"],
  "query": "test query",
  "keywords": ["keyword1", "keyword2"]
}

Response:
{
  "status": "started",
  "task_id": "task-uuid-123",
  "message": "Analysis started, use task_id to check progress"
}

// GET /analyze/status/{task_id}
Response:
{
  "task_id": "task-uuid-123",
  "status": "processing", // "processing", "completed", "failed"
  "progress": 50, // 0-100
  "current_step": "scraping",
  "message": "Scraping 3 URLs...",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "result": null, // Final results when completed
  "error": null   // Error message if failed
}
```

**Expected Request/Response Format:**

```typescript
// POST /campaigns
Request Body:
{
  "name": "Campaign Name",
  "description": "Campaign description",
  "type": "keyword",
  "keywords": ["keyword1", "keyword2"],
  "urls": ["https://example.com"],
  "trendingTopics": ["topic1", "topic2"],
  "topics": ["topic1", "topic2"],
  "extractionSettings": { /* settings object */ },
  "preprocessingSettings": { /* settings object */ },
  "entitySettings": { /* settings object */ },
  "modelingSettings": { /* settings object */ }
}

Response:
{
  "status": "success",
  "message": {
    "id": "generated-campaign-id",
    "name": "Campaign Name",
    "description": "Campaign description",
    "type": "keyword",
    "keywords": ["keyword1", "keyword2"],
    "createdAt": "2025-01-01T00:00:00Z",
    "updatedAt": "2025-01-01T00:00:00Z"
  }
}

// GET /campaigns
Response:
{
  "status": "success",
  "campaigns": [
    {
      "id": "campaign-1",
      "name": "Campaign Name",
      "description": "Campaign description",
      "type": "keyword",
      "keywords": ["keyword1", "keyword2"],
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z"
    }
  ]
}
```

#### 3. Campaign Merge Functionality

The campaign merge feature requires:
- Ability to create new campaigns via POST endpoint
- Proper handling of merged campaign data
- Real-time updates to campaign lists
- Persistent storage across page refreshes

### Author Personalities Integration

The application now includes database integration for author personalities. The following setup is required for production:

#### 1. Database Table/Collection

Create the following table in your database:

```sql
-- MySQL/PostgreSQL
CREATE TABLE author_personalities (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    user_id VARCHAR(255), -- Optional: for user-specific personalities
    INDEX idx_user_id (user_id)
);

-- MongoDB (if using NoSQL)
{
  "_id": ObjectId,
  "name": String,
  "description": String,
  "created_at": Date,
  "updated_at": Date,
  "user_id": String // Optional: for user-specific personalities
}
```

#### 2. Backend API Endpoints

Implement the following API endpoints in your backend:

```
GET    /api/author_personalities     - Fetch all author personalities
POST   /api/author_personalities     - Create new author personality
PUT    /api/author_personalities/:id - Update existing author personality
DELETE /api/author_personalities/:id - Delete author personality
```

**Expected Request/Response Format:**

```typescript
// POST /api/author_personalities
Request Body:
{
  "name": "Ernest Hemingway",
  "description": "Concise, direct prose with short sentences"
}

Response:
{
  "status": "success",
  "message": {
    "id": "generated-id",
    "name": "Ernest Hemingway",
    "description": "Concise, direct prose with short sentences",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}

// GET /api/author_personalities
Response:
{
  "status": "success",
  "message": {
    "personalities": [
      {
        "id": "1",
        "name": "Ernest Hemingway",
        "description": "Concise, direct prose with short sentences",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### 3. Authentication Integration

Ensure the API endpoints:
- Require valid authentication tokens
- Associate personalities with the authenticated user
- Return user-specific data only

#### 4. Error Handling

The backend should return consistent error responses:

```typescript
// Error Response Format
{
  "status": "error",
  "message": "Error description here"
}
```

## Frontend Features Implemented

### Author Personalities Management
- ✅ Database integration with API calls
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Loading states and error handling
- ✅ Fallback to sample data if API fails
- ✅ Real-time UI updates
- ✅ Toast notifications for user feedback

### Scheduled Posts Management
- ✅ List and Grid view toggle
- ✅ Bulk selection and deletion
- ✅ Advanced filtering (date range, platform)
- ✅ Case-insensitive platform filtering
- ✅ Real-time filtering

### Campaign Management
- ✅ Database integration with full CRUD operations
- ✅ Campaign merge functionality
- ✅ Real-time updates and persistence
- ✅ Next.js API routes for development
- ✅ Backend API specification provided

## Current Development Setup

### Next.js API Routes (Development)

The application currently uses Next.js API routes for campaign management during development:

- **Location**: `/app/api/campaigns/`
- **Database**: In-memory storage (resets on server restart)
- **Purpose**: Development and testing of campaign functionality
- **Migration**: Will be replaced with external API when backend is ready

### Files Created for Campaign Management

```
/app/api/campaigns/
├── route.ts              # GET, POST /api/campaigns
└── [id]/route.ts         # GET, PUT, DELETE /api/campaigns/{id}

/lib/database.ts          # In-memory database service
/components/Service.tsx   # Updated to use local API
/BACKEND_API_SPECIFICATION.md  # Complete API spec for backend team
```

### Migration to Production

When the backend API is ready:

1. **Update Service.tsx**: Change API URLs from `/api/campaigns` to external API
2. **Remove Next.js API routes**: Delete `/app/api/campaigns/` directory
3. **Remove database.ts**: Delete `/lib/database.ts` file
4. **Test integration**: Verify all campaign operations work with external API

## Environment Variables Required

Ensure these environment variables are set in production:

```env
# API Configuration
NEXT_PUBLIC_API_BASE_URL=your_api_base_url
NEXT_PUBLIC_API_VERSION=v1

# Database Configuration (if applicable)
DATABASE_URL=your_database_connection_string

# Authentication
JWT_SECRET=your_jwt_secret

# Campaign Management (when backend is ready)
NEXT_PUBLIC_CAMPAIGNS_API_URL=https://themachine.vernalcontentum.com/campaigns
```

## Testing the Integration

### 1. Test Author Personalities API
```bash
# Test creating a personality
curl -X POST your_api_url/api/author_personalities \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"name": "Test Author", "description": "Test description"}'

# Test fetching personalities
curl -X GET your_api_url/api/author_personalities \
  -H "Authorization: Bearer your_token"
```

### 2. Test Campaign Management API
```bash
# Test creating a campaign
curl -X POST your_api_url/campaigns \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "name": "Test Campaign",
    "description": "Test description",
    "type": "keyword",
    "keywords": ["test", "campaign"]
  }'

# Test fetching campaigns
curl -X GET your_api_url/campaigns \
  -H "Authorization: Bearer your_token"

# Test updating a campaign
curl -X PUT your_api_url/campaigns/CAMPAIGN_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"name": "Updated Campaign Name"}'

# Test deleting a campaign
curl -X DELETE your_api_url/campaigns/CAMPAIGN_ID \
  -H "Authorization: Bearer your_token"
```

### 3. Verify Frontend Integration
1. Navigate to Dashboard → Content Planner → Campaigns tab
2. Check that campaigns load from the database
3. Test creating a new campaign
4. Test merging campaigns (select multiple, click merge)
5. Test editing a campaign (click Edit button)
6. Test deleting a campaign
7. Verify loading states and error handling
8. Test campaign persistence across page refreshes

## Fallback Behavior

If the API endpoints are not implemented yet:
- The application will fall back to sample data
- Users can still interact with the UI
- Error messages will be displayed
- No functionality will be broken

## Migration from Sample Data

Once the API is implemented:
1. The application will automatically use the database
2. Sample data will be ignored
3. All CRUD operations will persist to the database
4. Users will see their actual saved personalities

## Installation Requirements for Live Deployment

### Prerequisites
- Node.js 18+ and npm
- Database (PostgreSQL, MySQL, or MongoDB)
- Backend API server with campaign endpoints
- Authentication system (JWT tokens)

### Required Backend Implementation

Before deploying to production, ensure the backend team implements:

1. **Campaign API Endpoints** (see `BACKEND_API_SPECIFICATION.md`)
2. **Database Schema** (campaigns table with proper indexes)
3. **Authentication Integration** (JWT token validation)
4. **CORS Configuration** (allow frontend domain)
5. **Error Handling** (consistent error response format)

### Development vs Production

**Current Development Setup:**
- Uses Next.js API routes (`/app/api/campaigns/`)
- In-memory database (resets on restart)
- Local development only

**Production Requirements:**
- External API endpoints (`https://themachine.vernalcontentum.com/campaigns`)
- Persistent database storage
- User authentication and authorization
- Proper error handling and logging

### Migration Checklist

When moving to production:

- [ ] Backend API endpoints implemented
- [ ] Database schema created (including progress tracking fields)
- [ ] Progress tracking API endpoints implemented (`/analyze`, `/analyze/status/{task_id}`)
- [ ] Authentication integrated
- [ ] CORS configured
- [ ] Update `Service.tsx` API URLs
- [ ] Remove Next.js API routes
- [ ] Remove `lib/database.ts`
- [ ] Test all campaign functionality
- [ ] Verify campaign merge works
- [ ] Test campaign persistence
- [ ] Test progress tracking (real-time updates)
- [ ] Test progress persistence across page refreshes

## Troubleshooting

### Common Issues:
1. **Campaign merge not working**: Check POST /campaigns endpoint implementation
2. **"Campaign Not Found" errors**: Verify GET /campaigns/{id} endpoint
3. **Campaigns disappearing**: Check database persistence and API responses
4. **Author personalities not loading**: Check API endpoint implementation
5. **CORS errors**: Ensure proper CORS configuration on backend
6. **Authentication errors**: Verify token handling in API calls
7. **Database connection issues**: Check database configuration and connectivity
8. **Progress not updating**: Check `/analyze/status/{task_id}` endpoint implementation
9. **Progress stuck at 0%**: Verify progress tracking fields in database
10. **Progress increments too small**: Check if using time-based fallback instead of API progress

### Debug Steps:
1. Check browser network tab for API call failures
2. Verify API endpoint responses match expected format
3. Check console for error messages
4. Test API endpoints directly with curl/Postman
5. Verify campaign data is being saved to database
6. Check authentication tokens are valid

## Support

For issues with the database integration or API setup, refer to:
- Backend API documentation
- Database schema documentation
- Authentication service documentation

---

**Note**: This integration maintains backward compatibility. The application will work with or without the database integration, ensuring a smooth deployment process.
>>>>>>> 1a12b611a15808ca8f5561b51000789a2d6a6505
