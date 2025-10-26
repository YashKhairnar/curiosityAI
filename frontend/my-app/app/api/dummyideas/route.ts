import { NextResponse } from "next/server";
import dummyEnhancedIdeas from "@/dummydata/dummy_enhanced_idea.json";

// Next.js App Router API route: respond to GET /api/dummyideas
export function GET() {
    return NextResponse.json({ enhanced_ideas: dummyEnhancedIdeas });
}