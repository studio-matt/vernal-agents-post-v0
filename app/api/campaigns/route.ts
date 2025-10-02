import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';

// GET /api/campaigns - Fetch all campaigns
export async function GET() {
  try {
    const campaigns = await db.getAllCampaigns();
    return NextResponse.json({
      status: 'success',
      campaigns: campaigns
    });
  } catch (error) {
    console.error('Error fetching campaigns:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to fetch campaigns' },
      { status: 500 }
    );
  }
}

// POST /api/campaigns - Create a new campaign
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

    const newCampaign = await db.createCampaign(campaignData);

    return NextResponse.json({
      status: 'success',
      message: newCampaign
    });
  } catch (error) {
    console.error('Error creating campaign:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to create campaign' },
      { status: 500 }
    );
  }
}
