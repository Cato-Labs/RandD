import {
  CopyIcon,
  DownloadIcon,
  ExternalLinkIcon,
  FileIcon,
  RefreshCcwIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Tool as AiTool } from "ai";
import {
  Agent,
  AgentContent,
  AgentHeader,
  AgentInstructions,
  AgentTool,
  AgentTools,
} from "@/components/ai-elements/agent";
import {
  Artifact,
  ArtifactAction,
  ArtifactActions,
  ArtifactClose,
  ArtifactContent,
  ArtifactDescription,
  ArtifactHeader,
  ArtifactTitle,
} from "@/components/ai-elements/artifact";
import { CodeBlock } from "@/components/ai-elements/code-block";
import {
  WebPreview,
  WebPreviewBody,
  WebPreviewConsole,
  WebPreviewNavigation,
  WebPreviewNavigationButton,
  WebPreviewUrl,
} from "@/components/ai-elements/web-preview";
import { Button } from "@/components/ui/button";
import type { LiveAgent } from "@/hooks/use-live-agent";

const PREVIEWABLE = /\.(html?|svg|pdf|png|jpe?g|gif|webp)$/i;

const languageFor = (file: string): string => {
  const ext = file.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    py: "python",
    ts: "typescript",
    tsx: "tsx",
    js: "javascript",
    jsx: "jsx",
    json: "json",
    md: "markdown",
    html: "html",
    css: "css",
    sh: "bash",
    yml: "yaml",
    yaml: "yaml",
  };
  return map[ext] ?? "text";
};

/** Workspace artifact viewer: real files the agent created via the editor tool. */
const WorkspaceArtifact = ({
  file,
  onClose,
}: {
  file: string;
  onClose: () => void;
}) => {
  const [content, setContent] = useState("");
  const url = `/workspace/${file}`;

  useEffect(() => {
    let active = true;
    fetch(url)
      .then((res) => (res.ok ? res.text() : "(unable to load file)"))
      .then((text) => active && setContent(text))
      .catch(() => active && setContent("(unable to load file)"));
    return () => {
      active = false;
    };
  }, [url]);

  return (
    <Artifact className="mt-2">
      <ArtifactHeader>
        <div>
          <ArtifactTitle>{file}</ArtifactTitle>
          <ArtifactDescription>
            Created by the agent in its workspace
          </ArtifactDescription>
        </div>
        <ArtifactActions>
          <ArtifactAction
            icon={CopyIcon}
            label="Copy"
            onClick={() => navigator.clipboard?.writeText(content)}
            tooltip="Copy contents"
          />
          <ArtifactAction
            icon={DownloadIcon}
            label="Download"
            onClick={() => {
              const link = document.createElement("a");
              link.href = url;
              link.download = file;
              link.click();
            }}
            tooltip="Download file"
          />
          <ArtifactAction
            icon={ExternalLinkIcon}
            label="Open"
            onClick={() => window.open(url, "_blank")}
            tooltip="Open in new tab"
          />
          <ArtifactClose onClick={onClose} />
        </ArtifactActions>
      </ArtifactHeader>
      <ArtifactContent className="p-0">
        <CodeBlock code={content} language={languageFor(file) as never} />
      </ArtifactContent>
    </Artifact>
  );
};

export const AgentPanel = ({ agent }: { agent: LiveAgent }) => {
  const [openFile, setOpenFile] = useState<string | null>(null);
  const previewLogs: {
    level: "log" | "warn" | "error";
    message: string;
    timestamp: Date;
  }[] = [];

  const previewFile = useMemo(
    () => agent.workspaceFiles.find((file) => PREVIEWABLE.test(file)),
    [agent.workspaceFiles]
  );

  return (
    <aside className="flex w-96 shrink-0 flex-col gap-4 overflow-y-auto border-l bg-sidebar p-4">
      {agent.agentCard && (
        <Agent className="w-full">
          <AgentHeader
            model={agent.agentCard.model}
            name={agent.agentCard.name}
          />
          <AgentContent>
            <AgentInstructions>
              {agent.agentCard.instructions}
            </AgentInstructions>
            <AgentTools collapsible type="single">
              {agent.agentCard.tools.map((tool) => (
                <AgentTool
                  key={tool.name}
                  tool={{ description: `${tool.name} — ${tool.description}` } as AiTool}
                  value={tool.name}
                />
              ))}
            </AgentTools>
          </AgentContent>
        </Agent>
      )}

      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
            Agent workspace
          </p>
          <Button
            onClick={() => agent.refreshWorkspace()}
            size="icon-sm"
            variant="ghost"
          >
            <RefreshCcwIcon className="size-3.5" />
          </Button>
        </div>
        {agent.workspaceFiles.length === 0 ? (
          <p className="text-muted-foreground text-xs">
            Files the agent creates with its editor tool appear here.
          </p>
        ) : (
          <ul className="space-y-1">
            {agent.workspaceFiles.map((file) => (
              <li key={file}>
                <Button
                  className="h-7 w-full justify-start gap-2 px-2 font-mono text-xs"
                  onClick={() =>
                    setOpenFile((current) => (current === file ? null : file))
                  }
                  variant={openFile === file ? "secondary" : "ghost"}
                >
                  <FileIcon className="size-3.5" />
                  {file}
                </Button>
              </li>
            ))}
          </ul>
        )}
        {openFile && (
          <WorkspaceArtifact file={openFile} onClose={() => setOpenFile(null)} />
        )}
      </div>

      {previewFile && (
        <div>
          <p className="mb-2 font-medium text-muted-foreground text-xs uppercase tracking-wide">
            Document preview
          </p>
          <WebPreview className="h-96" defaultUrl={`/workspace/${previewFile}`}>
            <WebPreviewNavigation>
              <WebPreviewNavigationButton
                onClick={() => agent.refreshWorkspace()}
                tooltip="Refresh workspace"
              >
                <RefreshCcwIcon className="size-4" />
              </WebPreviewNavigationButton>
              <WebPreviewUrl />
            </WebPreviewNavigation>
            <WebPreviewBody />
            <WebPreviewConsole logs={previewLogs} />
          </WebPreview>
        </div>
      )}
    </aside>
  );
};
