import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ 
    status: 'online', 
    message: 'Backend is up and running' 
  });
}