import {
  AudioLinesIcon,
  ClipboardCheckIcon,
  MessageSquareTextIcon,
  PanelRightIcon,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useLiveAgent } from "@/hooks/use-live-agent";
import { AgentPanel } from "@/views/AgentPanel";
import { ChatThread } from "@/views/ChatThread";
import { Composer } from "@/views/Composer";
import { InspectionView } from "@/views/InspectionView";
import { VoiceDock } from "@/views/VoiceDock";
import { WorkflowView } from "@/views/WorkflowView";

const App = () => {
  const agent = useLiveAgent();
  const [workflowOpen, setWorkflowOpen] = useState(false);
  const [agentPanelOpen, setAgentPanelOpen] = useState(false);
  const [inspectionOpen, setInspectionOpen] = useState(false);

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <span className="font-semibold">RandD Live</span>
          <span className="text-muted-foreground text-xs">
            {agent.models.find((entry) => entry.id === agent.model)?.name ??
              agent.agentCard?.model ??
              "Gemini Live"}{" "}
            ·{" "}
            <span
              className={
                agent.status === "connected"
                  ? "text-primary"
                  : "text-muted-foreground"
              }
            >
              {agent.status}
            </span>
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            onClick={() => agent.setMode("text")}
            size="sm"
            variant={agent.mode === "text" ? "secondary" : "ghost"}
          >
            <MessageSquareTextIcon className="size-4" />
            Text
          </Button>
          <Button
            onClick={() => agent.setMode("audio")}
            size="sm"
            variant={agent.mode === "audio" ? "secondary" : "ghost"}
          >
            <AudioLinesIcon className="size-4" />
            Voice
          </Button>
          <Button
            onClick={() => setInspectionOpen((open) => !open)}
            size="sm"
            variant={inspectionOpen ? "secondary" : "ghost"}
          >
            <ClipboardCheckIcon className="size-4" />
            Inspection
          </Button>
          <Button
            onClick={() => setAgentPanelOpen((open) => !open)}
            size="sm"
            variant={agentPanelOpen ? "secondary" : "ghost"}
          >
            <PanelRightIcon className="size-4" />
            Agent
          </Button>
        </div>
      </header>

      {agent.error && (
        <div className="border-destructive/50 border-b bg-destructive/10 px-4 py-2 text-destructive text-sm">
          {agent.error}
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <main className="flex min-w-0 flex-1 flex-col">
          {workflowOpen && <WorkflowView agent={agent} />}
          {/* Always mounted so checklist state persists and agent edits land
              in real time; it auto-surfaces whenever the agent updates it. */}
          <InspectionView
            agent={agent}
            onAgentEdit={() => setInspectionOpen(true)}
            open={inspectionOpen}
          />
          {!inspectionOpen && <ChatThread agent={agent} />}
          <Composer
            agent={agent}
            onToggleWorkflow={() => setWorkflowOpen((open) => !open)}
            workflowOpen={workflowOpen}
          />
        </main>
        <VoiceDock agent={agent} />
        {agentPanelOpen && <AgentPanel agent={agent} />}
      </div>
    </div>
  );
};

export default App;
