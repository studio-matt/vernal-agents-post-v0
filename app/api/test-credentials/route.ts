import { NextResponse } from 'next/server';
import { db } from '@/lib/database';

// GET /api/test-credentials - Test credentials endpoint
export async function GET() {
  try {
    console.log("🧪 Test: Getting credentials...");
    const credentials = await db.getUserCredentials();
    console.log("🧪 Test: Retrieved credentials:", credentials);
    
    // Test storing a credential
    console.log("🧪 Test: Storing test credential...");
    const testCredentials = await db.storeUserCredentials({ openai_key: 'test-key-123' });
    console.log("🧪 Test: Stored test credentials:", testCredentials);
    
    // Test retrieving again
    const retrievedCredentials = await db.getUserCredentials();
    console.log("🧪 Test: Retrieved after storage:", retrievedCredentials);
    
    return NextResponse.json({
      status: 'success',
      message: 'Test endpoint working',
      credentials: credentials,
      testCredentials: testCredentials,
      retrievedCredentials: retrievedCredentials,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('❌ Test: Error:', error);
    return NextResponse.json(
      { 
        status: 'error', 
        message: 'Test endpoint failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
