import OpenAI from "openai";

export type WorkflowNode = {
  id: string;
  prompt: string;
  label?: string;
};

export type WorkflowEdge = {
  source: string;
  target: string;
  condition?: "YES" | "NO";
};

export type WorkflowInput = {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

export async function decide(prompt: string): Promise<"YES" | "NO"> {
  if (!process.env.OPENAI_API_KEY) {
    return prompt.toLowerCase().includes("support") ? "YES" : "NO";
  }

  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const response = await client.responses.create({
    model: "gpt-4o-mini",
    input: `Answer the decision question with exactly YES or NO.\nQuestion: ${prompt}`,
  });
  const result = response.output_text.trim().toUpperCase();
  return result === "YES" ? "YES" : "NO";
}

export async function executeWorkflow({ nodes, edges }: WorkflowInput) {
  const logs: { nodeId: string; result: "YES" | "NO" }[] = [];
  const start = nodes[0];
  if (!start) return { logs, completed: true };

  let current: WorkflowNode | undefined = start;
  const visited = new Set<string>();
  while (current && !visited.has(current.id)) {
    visited.add(current.id);
    const result = await decide(current.prompt);
    logs.push({ nodeId: current.id, result });
    const edge = edges.find(
      (item) => item.source === current?.id && (!item.condition || item.condition === result),
    );
    current = edge ? nodes.find((node) => node.id === edge.target) : undefined;
  }
  return { logs, completed: true };
}
