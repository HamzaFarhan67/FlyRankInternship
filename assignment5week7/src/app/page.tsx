"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  addEdge,
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";

type NodeData = { label: string; prompt: string; active?: boolean; onDelete: (id: string) => void };
type Log = { nodeId: string; result: "YES" | "NO" };

const initialNodes: Node<NodeData>[] = [
  { id: "question", type: "decision", position: { x: 110, y: 170 }, data: { label: "Support request?", prompt: "Is this a support request?", onDelete: () => {} } },
  { id: "support", type: "decision", position: { x: 460, y: 70 }, data: { label: "Support team", prompt: "Should this go to the support team?", onDelete: () => {} } },
  { id: "sales", type: "decision", position: { x: 460, y: 270 }, data: { label: "Sales request", prompt: "Is this a sales opportunity?", onDelete: () => {} } },
];

const initialEdges: Edge[] = [
  { id: "question-support", source: "question", target: "support", sourceHandle: "yes", label: "YES", type: "smoothstep", className: "yes-edge" },
  { id: "question-sales", source: "question", target: "sales", sourceHandle: "no", label: "NO", type: "smoothstep", className: "no-edge" },
];

function DecisionNode({ id, data, selected }: NodeProps<Node<NodeData>>) {
  return (
    <div className={`flow-node ${selected || data.active ? "active" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <div className="node-head"><span className="node-label">AI DECISION</span><button className="delete-node" onClick={() => data.onDelete(id)}>×</button></div>
      <div className="node-body"><strong>{data.label}</strong><p>{data.prompt}</p><div className="node-footer"><span>Returns YES / NO</span><span>OpenAI</span></div></div>
      <Handle id="yes" type="source" position={Position.Right} style={{ top: "38%" }} />
      <Handle id="no" type="source" position={Position.Right} style={{ top: "72%" }} />
    </div>
  );
}

const nodeTypes = { decision: DecisionNode };

export default function Home() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedId, setSelectedId] = useState("question");
  const [logs, setLogs] = useState<Log[]>([]);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Ready to run");

  const activeNodes = useMemo(() => new Set(logs.map((log) => log.nodeId)), [logs]);
  const selectedNode = nodes.find((node) => node.id === selectedId);

  useEffect(() => {
    const saved = localStorage.getItem("flowpilot-workflow");
    if (!saved) return;
    try {
      const value = JSON.parse(saved) as { nodes: Node<NodeData>[]; edges: Edge[] };
      setNodes(value.nodes.map((node) => ({ ...node, data: { ...node.data, onDelete: () => {} } })));
      setEdges(value.edges);
    } catch {
      localStorage.removeItem("flowpilot-workflow");
    }
  }, [setEdges, setNodes]);

  useEffect(() => {
    localStorage.setItem("flowpilot-workflow", JSON.stringify({ nodes, edges }));
  }, [nodes, edges]);

  useEffect(() => {
    setNodes((items) => items.map((node) => ({ ...node, data: { ...node.data, active: activeNodes.has(node.id) } })));
  }, [activeNodes, setNodes]);

  const connect = useCallback((connection: Connection) => {
    const sourceHandle = connection.sourceHandle === "no" ? "NO" : "YES";
    setEdges((items) => addEdge({ ...connection, id: `${connection.source}-${connection.target}`, label: sourceHandle, type: "smoothstep" }, items));
  }, [setEdges]);

  const deleteNode = useCallback((id: string) => {
    setNodes((items) => items.filter((node) => node.id !== id));
    setEdges((items) => items.filter((edge) => edge.source !== id && edge.target !== id));
    setSelectedId("");
  }, [setEdges, setNodes]);

  useEffect(() => {
    setNodes((items) => items.map((node) => ({ ...node, data: { ...node.data, onDelete: deleteNode } })));
  }, [deleteNode, setNodes]);

  function addNode() {
    const id = `node-${Date.now()}`;
    setNodes((items) => [...items, { id, type: "decision", position: { x: 180, y: 430 }, data: { label: "New decision", prompt: "Does this condition pass?", onDelete: deleteNode } }]);
    setSelectedId(id);
  }

  async function runWorkflow() {
    setRunning(true);
    setLogs([]);
    setStatus("Running with Inngest steps...");
    try {
      const response = await fetch("/api/execute", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nodes: nodes.map(({ id, data }) => ({ id, prompt: data.prompt, label: data.label })), edges: edges.map(({ source, target, label, sourceHandle }) => ({ source, target, condition: (label ?? (sourceHandle === "no" ? "NO" : "YES")) as "YES" | "NO" })) }) });
      const result = await response.json() as { logs?: Log[]; error?: string };
      if (!response.ok) throw new Error(result.error);
      setLogs(result.logs ?? []);
      setStatus(`Completed ${result.logs?.length ?? 0} decision steps`);
    } catch {
      setStatus("Execution failed");
    } finally {
      setRunning(false);
    }
  }

  function exportWorkflow() {
    const blob = new Blob([JSON.stringify({ nodes, edges }, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "flowpilot-workflow.json";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function updateSelected(field: "label" | "prompt", value: string) {
    setNodes((items) => items.map((node) => node.id === selectedId ? { ...node, data: { ...node.data, [field]: value } } : node));
  }

  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand"><span className="brand-mark">✦</span> FlowPilot</div><div className="top-actions"><span className="status">{status}</span><button className="ghost-button" onClick={exportWorkflow}>Export JSON</button><button className="primary-button" onClick={runWorkflow} disabled={running}>{running ? "Running..." : "Run workflow"}</button></div></header>
      <div className="workspace">
        <aside className="sidebar"><div className="eyebrow">Workspace</div><h1 className="side-title">AI Workflows</h1><button className="side-button">◈  Customer routing</button><button className="side-button" onClick={() => { setNodes(initialNodes); setEdges(initialEdges); }}>＋  New workflow</button><div className="eyebrow" style={{ marginTop: 40 }}>Build</div><button className="side-button" onClick={addNode}>＋  Add decision node</button><p className="panel-copy" style={{ marginTop: 28 }}>Connect the YES and NO handles to create your branching logic.</p></aside>
        <section className="main-panel"><div className="toolbar"><div className="toolbar-left"><span className="workflow-name">Customer routing</span><span className="status">Saved locally</span></div><div className="toolbar"><span className="status">{nodes.length} nodes · {edges.length} connections</span></div></div><div className="canvas"><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={connect} onNodeClick={(_, node) => setSelectedId(node.id)} fitView><Background color="#e2e5ef" gap={22} /><Controls /><MiniMap /></ReactFlow></div></section>
        <aside className="inspector"><div className="panel-heading"><h2>Node settings</h2><span className="eyebrow">Inspector</span></div>{selectedNode ? <><label className="field-label">Node name</label><input className="field" value={selectedNode.data.label} onChange={(event) => updateSelected("label", event.target.value)} /><label className="field-label">Decision prompt</label><textarea className="prompt" value={selectedNode.data.prompt} onChange={(event) => updateSelected("prompt", event.target.value)} /><p className="panel-copy">The AI will answer this prompt with exactly YES or NO, then follow the matching connection.</p></> : <p className="panel-copy">Select a decision node to edit it.</p>}<div className="panel-heading" style={{ marginTop: 30, marginBottom: 0 }}><h2>Execution log</h2></div><div className="log-list">{logs.length ? logs.map((log, index) => <div className="log-item" key={`${log.nodeId}-${index}`}><strong>{log.result}</strong>{nodes.find((node) => node.id === log.nodeId)?.data.label}</div>) : <span className="empty-log">Run the workflow to see each decision step.</span>}</div></aside>
      </div>
    </main>
  );
}
