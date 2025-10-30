import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://themachine.vernalcontentum.com';

// GET /api/campaigns - Fetch all campaigns from backend
export async function GET(request: NextRequest) {
  try {
    // Get auth token from request headers
    const authHeader = request.headers.get('authorization');
    
    // Call backend API to get campaigns
    const response = await fetch(`${BACKEND_API_URL}/campaigns`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { 'Authorization': authHeader } : {}),
      },
    });

    if (!response.ok) {
      throw new Error(`Backend API returned ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching campaigns from backend:', error);
    // Fallback to local database if backend is unavailable
    try {
      const campaigns = await db.getAllCampaigns();
      return NextResponse.json({
        status: 'success',
        campaigns: campaigns
      });
    } catch (fallbackError) {
      console.error('Error fetching campaigns from local DB:', fallbackError);
      return NextResponse.json(
        { status: 'error', message: 'Failed to fetch campaigns' },
        { status: 500 }
      );
    }
  }
}

// POST /api/campaigns - Create a new campaign in backend
export async function POST(request: NextRequest) {
  try {
    const campaignData = await request.json();
    
    // Validate required fields
    if (!campaignData.name || !campaignData.type) {
      return NextResponse.json(
        { status: 'error', message: 'Name and type are required' },
        { status: 400 }
      );
    }

    // Get auth token from request headers
    const authHeader = request.headers.get('authorization');
    
    // Prepare payload for backend (matching CampaignCreate model)
    const backendPayload = {
      name: campaignData.name,
      description: campaignData.description || '',
      type: campaignData.type,
      keywords: campaignData.keywords || [],
      urls: campaignData.urls || [],
      trendingTopics: campaignData.trendingTopics || [],
      topics: campaignData.topics || [],
    };

    console.log('📤 Creating campaign in backend:', backendPayload);
    
    // Call backend API to create campaign
    const response = await fetch(`${BACKEND_API_URL}/campaigns`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { 'Authorization': authHeader } : {}),
      },
      body: JSON.stringify(backendPayload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ Backend API returned ${response.status}:`, errorText);
      throw new Error(`Backend API returned ${response.status}: ${errorText}`);
    }

    const data = await response.json();
    console.log('✅ Campaign created in backend:', data);
    
    // Also save locally for offline access (optional)
    try {
      await db.createCampaign(campaignData);
    } catch (localError) {
      console.warn('⚠️ Failed to save campaign locally:', localError);
      // Non-fatal, continue
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error creating campaign:', error);
    return NextResponse.json(
      { status: 'error', message: error instanceof Error ? error.message : 'Failed to create campaign' },
      { status: 500 }
    );
  }
}
