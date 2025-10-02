import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';

// POST /api/credentials/claude - Store Claude API key
export async function POST(request: NextRequest) {
  try {
    const { api_key } = await request.json();
    
    if (!api_key) {
      return NextResponse.json(
        { status: 'error', message: 'API key is required' },
        { status: 400 }
      );
    }

    const credentials = await db.storeUserCredentials({ claude_key: api_key });

    return NextResponse.json({
      status: 'success',
      message: 'Claude API key stored successfully',
      credentials: credentials
    });
  } catch (error) {
    console.error('Error storing Claude key:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to store Claude API key' },
      { status: 500 }
    );
  }
}
