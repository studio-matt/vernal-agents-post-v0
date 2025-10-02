import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';

// GET /api/credentials - Get user credentials
export async function GET() {
  try {
    console.log("🔍 API: Getting user credentials...");
    const credentials = await db.getUserCredentials();
    console.log("🔍 API: Retrieved credentials:", credentials);
    return NextResponse.json({
      status: 'success',
      credentials: credentials
    });
  } catch (error) {
    console.error('❌ API: Error fetching credentials:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to fetch credentials' },
      { status: 500 }
    );
  }
}

// POST /api/credentials - Store user credentials
export async function POST(request: NextRequest) {
  try {
    const { openai_key, claude_key } = await request.json();
    
    const credentials = await db.storeUserCredentials({ openai_key, claude_key });

    return NextResponse.json({
      status: 'success',
      message: 'Credentials stored successfully',
      credentials: credentials
    });
  } catch (error) {
    console.error('Error storing credentials:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to store credentials' },
      { status: 500 }
    );
  }
}
