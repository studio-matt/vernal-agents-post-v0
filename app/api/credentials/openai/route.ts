import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';

// POST /api/credentials/openai - Store OpenAI API key
export async function POST(request: NextRequest) {
  try {
    console.log("🔍 OpenAI API: Received request");
    const { api_key } = await request.json();
    console.log("🔍 OpenAI API: API key received:", api_key ? "***" + api_key.slice(-4) : "empty");
    
    if (!api_key) {
      return NextResponse.json(
        { status: 'error', message: 'API key is required' },
        { status: 400 }
      );
    }

    console.log("🔍 OpenAI API: Storing credentials...");
    const credentials = await db.storeUserCredentials({ openai_key: api_key });
    console.log("🔍 OpenAI API: Stored credentials:", credentials);

    return NextResponse.json({
      status: 'success',
      message: 'OpenAI API key stored successfully',
      credentials: credentials
    });
  } catch (error) {
    console.error('❌ OpenAI API: Error storing key:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to store OpenAI API key' },
      { status: 500 }
    );
  }
}
