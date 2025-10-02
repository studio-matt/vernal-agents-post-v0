# Vernal Contentum - Next.js Application

## Overview
This is a Next.js application called "Vernal Contentum" that appears to be a content management and generation platform. The application includes user authentication, campaign management, content generation workflows, and various tools for content analysis and planning.

## Recent Changes (September 25, 2025)
- Successfully imported from GitHub repository
- Installed all dependencies via npm
- Fixed TypeScript type errors in Service.tsx
- Configured Next.js for Replit environment with proper host settings
- Set up frontend workflow to run on port 5000 with 0.0.0.0 binding
- Configured deployment settings for autoscale deployment target
- Application is running successfully with authentication working

## Project Architecture
- **Framework**: Next.js 14.2.16 with TypeScript
- **Styling**: Tailwind CSS with custom components
- **UI Components**: Radix UI components with custom styling
- **API**: External API integration to https://themachine.vernalcontentum.com
- **Authentication**: JWT-based authentication with login/signup/OTP verification
- **Build System**: Next.js with npm package management

## Key Features
- User authentication (login, signup, password reset, email verification)
- Dashboard with multiple content management tools
- Campaign management and settings
- Content generation and planning workflows
- Author personality configuration
- Podcast tools and management
- Content analysis and trending topics

## Configuration
- **Port**: 5000 (required for Replit)
- **Host**: 0.0.0.0 (required for Replit proxy)
- **Deployment**: Configured for autoscale with build and start scripts
- **Environment**: Development server runs with hot reload

## API Integration
The application connects to an external API at `https://themachine.vernalcontentum.com` for:
- User authentication
- Content generation
- Campaign management
- Data analysis

## User Preferences
- No specific coding style preferences noted yet
- Standard Next.js/React development patterns followed
- TypeScript with strict mode enabled (build errors ignored for compatibility)