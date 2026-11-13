import { Inngest } from "inngest";
import { executeWorkflow, type WorkflowInput } from "./workflow";

export const inngest = new Inngest({ id: "flowpilot" });

export const runWorkflow = inngest.createFunction(
  { id: "run-ai-workflow" },
  { event: "workflow/run" },
  async ({ event, step }) => {
    const workflow = event.data as WorkflowInput;
    const logs: Awaited<ReturnType<typeof executeWorkflow>>["logs"] = [];
    const nodes = workflow.nodes;
    const edges = workflow.edges;
    let current: WorkflowInput["nodes"][number] | undefined = nodes[0];
    const visited = new Set<string>();

    while (current && !visited.has(current.id)) {
      visited.add(current.id);
      const node: WorkflowInput["nodes"][number] = current;
      const result = await step.run(`decision-${node.id}`, () => executeWorkflow({
        nodes: [node],
        edges: [],
      }).then((value) => value.logs[0]?.result ?? "NO"));
      logs.push({ nodeId: node.id, result });
      const edge = edges.find(
        (item) => item.source === node.id && (!item.condition || item.condition === result),
      );
      current = edge ? nodes.find((item) => item.id === edge.target) : undefined;
    }

    return { logs };
  },
);
