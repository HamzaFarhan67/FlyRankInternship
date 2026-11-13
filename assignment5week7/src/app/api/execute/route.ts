import { NextResponse } from "next/server";
import { executeWorkflow, type WorkflowInput } from "@/lib/workflow";

export async function POST(request: Request) {
  try {
    const input = (await request.json()) as WorkflowInput;
    const result = await executeWorkflow(input);
    return NextResponse.json(result);
  } catch {
    return NextResponse.json({ error: "Workflow execution failed" }, { status: 500 });
  }
}
