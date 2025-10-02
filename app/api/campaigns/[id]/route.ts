import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';

// GET /api/campaigns/[id] - Get a specific campaign
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    
    const campaign = await db.getCampaignById(id);
    
    if (!campaign) {
      return NextResponse.json(
        { status: 'error', message: 'Campaign not found' },
        { status: 404 }
      );
    }

    // Convert campaign to the format expected by the frontend
    const formattedCampaign = {
      status: 'success',
      message: {
        raw_data: [{
          ...campaign,
          campaign_name: campaign.name,
          query: campaign.query || campaign.name,
          trending_content: campaign.trendingTopics?.map((topic: string) => ({ text: topic })) || [],
          topics: campaign.topics || campaign.trendingTopics || [],
          text: '',
          stemmed_text: '',
          lemmatized_text: '',
          stopwords_removed_text: ''
        }]
      }
    };

    return NextResponse.json(formattedCampaign);
  } catch (error) {
    console.error('Error fetching campaign:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to fetch campaign' },
      { status: 500 }
    );
  }
}

// PUT /api/campaigns/[id] - Update a specific campaign
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    const updateData = await request.json();
    
    const updatedCampaign = await db.updateCampaign(id, updateData);
    
    if (!updatedCampaign) {
      return NextResponse.json(
        { status: 'error', message: 'Campaign not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      status: 'success',
      message: updatedCampaign
    });
  } catch (error) {
    console.error('Error updating campaign:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to update campaign' },
      { status: 500 }
    );
  }
}

// DELETE /api/campaigns/[id] - Delete a specific campaign
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    
    const deleted = await db.deleteCampaign(id);
    
    if (!deleted) {
      return NextResponse.json(
        { status: 'error', message: 'Campaign not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      status: 'success',
      message: 'Campaign deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting campaign:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to delete campaign' },
      { status: 500 }
    );
  }
}
