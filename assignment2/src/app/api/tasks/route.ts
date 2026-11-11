import { NextRequest, NextResponse } from "next/server";
import database, { toTask } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET() {
  const rows = database
    .prepare("SELECT id, title, done FROM tasks ORDER BY id")
    .all() as { id: number; title: string; done: number }[];

  return NextResponse.json(rows.map(toTask));
}

export async function POST(request: NextRequest) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  if (
    typeof body !== "object" ||
    body === null ||
    typeof (body as { title?: unknown }).title !== "string" ||
    !(body as { title: string }).title.trim()
  ) {
    return NextResponse.json({ error: "Title is required" }, { status: 400 });
  }

  const title = (body as { title: string }).title.trim();
  const result = database.prepare("INSERT INTO tasks (title, done) VALUES (?, 0)").run(title);
  const row = database
    .prepare("SELECT id, title, done FROM tasks WHERE id = ?")
    .get(result.lastInsertRowid) as { id: number; title: string; done: number };

  return NextResponse.json(toTask(row), { status: 201 });
}
