import { MaximizeIcon, RefreshCcwIcon } from "lucide-react";
import { useMemo } from "react";
import { useReactFlow, ReactFlowProvider } from "@xyflow/react";
import type { Edge as FlowEdge, Node as FlowNode } from "@xyflow/react";
import { Canvas } from "@/components/ai-elements/canvas";
import { Connection } from "@/components/ai-elements/connection";
import { Controls } from "@/components/ai-elements/controls";
import { Edge } from "@/components/ai-elements/edge";
import {
  Node,
  NodeContent,
  NodeDescription,
  NodeFooter,
  NodeHeader,
  NodeTitle,
} from "@/components/ai-elements/node";
import { Panel } from "@/components/ai-elements/panel";
import { Toolbar } from "@/components/ai-elements/toolbar";
import { Button } from "@/components/ui/button";
import type { LiveAgent } from "@/hooks/use-live-agent";
import type { LiveToolPart } from "@/lib/live-types";

/**
 * Live session graph: user → agent → one node per tool invocation.
 * Built entirely from real session events (messages/tool parts/usage).
 */

type WorkflowNodeData = {
  title: string;
  description: string;
  content?: string;
  footer?: string;
};

const WorkflowNode = ({ data }: { data: WorkflowNodeData }) => (
  <Node handles={{ source: true, target: true }}>
    <NodeHeader>
      <NodeTitle>{data.title}</NodeTitle>
      <NodeDescription>{data.description}</NodeDescription>
    </NodeHeader>
    {data.content && (
      <NodeContent>
        <p className="line-clamp-3 font-mono text-xs">{data.content}</p>
      </NodeContent>
    )}
    {data.footer && (
      <NodeFooter>
        <p className="text-muted-foreground text-xs">{data.footer}</p>
      </NodeFooter>
    )}
  </Node>
);

const nodeTypes = { workflow: WorkflowNode };
const edgeTypes = { animated: Edge.Animated, temporary: Edge.Temporary };

const FitButton = () => {
  const { fitView } = useReactFlow();
  return (
    <Button onClick={() => fitView({ duration: 300 })} size="sm" variant="ghost">
      <MaximizeIcon className="size-4" />
      Fit
    </Button>
  );
};

const WorkflowGraph = ({ agent }: { agent: LiveAgent }) => {
  const { nodes, edges } = useMemo(() => {
    const toolParts = agent.messages.flatMap((message) =>
      message.parts.filter((part): part is LiveToolPart =>
        part.type.startsWith("tool-")
      )
    );
    const userTurns = agent.messages.filter((m) => m.role === "user").length;

    const nodes: FlowNode[] = [
      {
        id: "user",
        type: "workflow",
        position: { x: 0, y: 120 },
        data: {
          title: "You",
          description: "Live audio + text input",
          footer: `${userTurns} turn${userTurns === 1 ? "" : "s"}`,
        },
      },
      {
        id: "agent",
        type: "workflow",
        position: { x: 420, y: 120 },
        data: {
          title: agent.agentCard?.name ?? "RandD Live",
          description: agent.agentCard?.model ?? "Gemini Live",
          footer: agent.usage
            ? `tokens: ${agent.usage.inputTokens} in / ${agent.usage.outputTokens} out`
            : "no usage yet",
        },
      },
      ...toolParts.map((part, index) => ({
        id: part.toolCallId,
        type: "workflow",
        position: { x: 840, y: index * 190 },
        data: {
          title: part.toolName,
          description:
            part.state === "output-available"
              ? "completed"
              : part.state === "output-error"
                ? "error"
                : "running…",
          content: JSON.stringify(part.input),
        },
      })),
    ];

    const edges: FlowEdge[] = [
      {
        id: "user-agent",
        source: "user",
        target: "agent",
        type: agent.chatStatus === "streaming" ? "animated" : "temporary",
      },
      ...toolParts.map((part) => ({
        id: `agent-${part.toolCallId}`,
        source: "agent",
        target: part.toolCallId,
        type:
          part.state === "output-available" || part.state === "output-error"
            ? ("temporary" as const)
            : ("animated" as const),
      })),
    ];

    return { nodes, edges };
  }, [agent.messages, agent.agentCard, agent.usage, agent.chatStatus]);

  return (
    <Canvas
      connectionLineComponent={Connection}
      edges={edges}
      edgeTypes={edgeTypes}
      nodes={nodes}
      nodeTypes={nodeTypes}
    >
      <Controls />
      <Panel position="top-left">
        <div className="rounded-md border bg-card px-3 py-2 text-xs">
          <p className="font-medium">Live session workflow</p>
          <p className="text-muted-foreground">
            {agent.status === "connected" ? "streaming events" : "disconnected"}
            {agent.usage && ` · ${agent.usage.totalTokens} tokens total`}
          </p>
        </div>
      </Panel>
      <Toolbar>
        <FitButton />
        <Button onClick={() => agent.refreshWorkspace()} size="sm" variant="ghost">
          <RefreshCcwIcon className="size-4" />
          Refresh
        </Button>
      </Toolbar>
    </Canvas>
  );
};

export const WorkflowView = ({ agent }: { agent: LiveAgent }) => (
  <div className="h-72 shrink-0 border-b">
    <ReactFlowProvider>
      <WorkflowGraph agent={agent} />
    </ReactFlowProvider>
  </div>
);
