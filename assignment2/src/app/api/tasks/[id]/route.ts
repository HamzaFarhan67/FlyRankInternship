import { NextRequest, NextResponse } from "next/server";
import database, { toTask } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };
type TaskRow = { id: number; title: string; done: number };

function getId(value: string) {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
}

function findTask(id: number) {
  return database.prepare("SELECT id, title, done FROM tasks WHERE id = ?").get(id) as
    | TaskRow
    | undefined;
}

export async function GET(_request: NextRequest, { params }: Params) {
  const id = getId((await params).id);
  const row = id === null ? undefined : findTask(id);

  if (!row) {
    return NextResponse.json({ error: "Task not found" }, { status: 404 });
  }

  return NextResponse.json(toTask(row));
}

export async function PUT(request: NextRequest, { params }: Params) {
  const id = getId((await params).id);
  if (id === null || !findTask(id)) {
    return NextResponse.json({ error: "Task not found" }, { status: 404 });
  }

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
    !(body as { title: string }).title.trim() ||
    typeof (body as { done?: unknown }).done !== "boolean"
  ) {
    return NextResponse.json({ error: "Title and done are required" }, { status: 400 });
  }

  const input = body as { title: string; done: boolean };
  database
    .prepare("UPDATE tasks SET title = ?, done = ? WHERE id = ?")
    .run(input.title.trim(), input.done ? 1 : 0, id);

  return NextResponse.json(toTask(findTask(id) as TaskRow));
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const id = getId((await params).id);
  if (id === null || !findTask(id)) {
    return NextResponse.json({ error: "Task not found" }, { status: 404 });
  }

  database.prepare("DELETE FROM tasks WHERE id = ?").run(id);
  return new NextResponse(null, { status: 204 });
}
