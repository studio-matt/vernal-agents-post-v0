import { NextRequest, NextResponse } from 'next/server';

// Mock scheduled posts data for now
const MOCK_SCHEDULED_POSTS = [
  {
    id: 1,
    topic: "AI Technology",
    title: "The Future of AI in Content Creation",
    content: "Artificial Intelligence is revolutionizing how we create content...",
    day: "Monday",
    platform: "LinkedIn",
    schedule_time: "2025-01-02T09:00:00Z",
    image_url: "https://via.placeholder.com/400x300"
  },
  {
    id: 2,
    topic: "Marketing Trends",
    title: "Social Media Marketing in 2025",
    content: "Social media marketing continues to evolve with new platforms...",
    day: "Tuesday",
    platform: "Instagram",
    schedule_time: "2025-01-03T14:00:00Z",
    image_url: "https://via.placeholder.com/400x300"
  },
  {
    id: 3,
    topic: "Business Strategy",
    title: "Building a Strong Brand Identity",
    content: "A strong brand identity is crucial for business success...",
    day: "Wednesday",
    platform: "Facebook",
    schedule_time: "2025-01-04T11:00:00Z",
    image_url: "https://via.placeholder.com/400x300"
  }
];

// GET /api/scheduled-posts - Fetch all scheduled posts
export async function GET() {
  try {
    console.log("🔍 API: Getting scheduled posts...");
    
    // For now, return mock data
    // In the future, this could be connected to a real database
    return NextResponse.json({
      status: 'success',
      message: {
        posts: MOCK_SCHEDULED_POSTS
      }
    });
  } catch (error) {
    console.error('Error fetching scheduled posts:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to fetch scheduled posts' },
      { status: 500 }
    );
  }
}
