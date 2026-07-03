import {
  CheckCircleIcon,
  CopyIcon,
  FileCodeIcon,
  RefreshCcwIcon,
  TerminalIcon,
  WrenchIcon,
} from "lucide-react";
import { Fragment, useCallback } from "react";
import type { UIMessage } from "ai";
import {
  AudioPlayer,
  AudioPlayerControlBar,
  AudioPlayerDurationDisplay,
  AudioPlayerElement,
  AudioPlayerMuteButton,
  AudioPlayerPlayButton,
  AudioPlayerSeekBackwardButton,
  AudioPlayerSeekForwardButton,
  AudioPlayerTimeDisplay,
  AudioPlayerTimeRange,
  AudioPlayerVolumeRange,
} from "@/components/ai-elements/audio-player";
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtSearchResult,
  ChainOfThoughtSearchResults,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";
import { CodeBlock, CodeBlockCopyButton } from "@/components/ai-elements/code-block";
import {
  Conversation,
  ConversationContent,
  ConversationDownload,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Image } from "@/components/ai-elements/image";
import {
  JSXPreview,
  JSXPreviewContent,
  JSXPreviewError,
} from "@/components/ai-elements/jsx-preview";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  Plan,
  PlanContent,
  PlanDescription,
  PlanHeader,
  PlanTitle,
  PlanTrigger,
} from "@/components/ai-elements/plan";
import {
  Sandbox,
  SandboxContent,
  SandboxHeader,
  SandboxTabContent,
  SandboxTabs,
  SandboxTabsBar,
  SandboxTabsList,
  SandboxTabsTrigger,
} from "@/components/ai-elements/sandbox";
import {
  Task,
  TaskContent,
  TaskItem,
  TaskItemFile,
  TaskTrigger,
} from "@/components/ai-elements/task";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
import type { LiveAgent } from "@/hooks/use-live-agent";
import type { LiveMessage, LiveToolPart } from "@/lib/live-types";
import { segmentText } from "@/lib/parse-blocks";

const messageText = (message: LiveMessage): string =>
  message.parts
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("\n");

/** Filenames touched by editor/shell tool input (real tool args). */
const touchedFiles = (part: LiveToolPart): string[] => {
  const input = part.input as Record<string, unknown> | undefined;
  const path = input?.path ?? input?.file_path ?? input?.file_text_path;
  return typeof path === "string" ? [path] : [];
};

const ShellSandbox = ({ part }: { part: LiveToolPart }) => {
  const input = part.input as Record<string, unknown> | undefined;
  const command =
    typeof input?.command === "string"
      ? input.command
      : JSON.stringify(input ?? {}, null, 2);
  return (
    <Sandbox>
      <SandboxHeader state={part.state} title="shell" />
      <SandboxContent>
        <SandboxTabs defaultValue="command">
          <SandboxTabsBar>
            <SandboxTabsList>
              <SandboxTabsTrigger value="command">Command</SandboxTabsTrigger>
              <SandboxTabsTrigger value="output">Output</SandboxTabsTrigger>
            </SandboxTabsList>
          </SandboxTabsBar>
          <SandboxTabContent value="command">
            <CodeBlock code={command} language="bash">
              <CodeBlockCopyButton />
            </CodeBlock>
          </SandboxTabContent>
          <SandboxTabContent value="output">
            <CodeBlock
              code={String(part.output ?? part.errorText ?? "(running…)")}
              language="console"
            >
              <CodeBlockCopyButton />
            </CodeBlock>
          </SandboxTabContent>
        </SandboxTabs>
      </SandboxContent>
    </Sandbox>
  );
};

const ToolPartView = ({ part }: { part: LiveToolPart }) => {
  if (part.toolName === "shell") return <ShellSandbox part={part} />;
  return (
    <Tool>
      <ToolHeader
        state={part.state}
        toolName={part.toolName}
        type="dynamic-tool"
      />
      <ToolContent>
        <ToolInput input={part.input} />
        {(part.output !== undefined || part.errorText) && (
          <ToolOutput
            errorText={part.errorText}
            output={
              typeof part.output === "string" ? (
                <MessageResponse>{part.output}</MessageResponse>
              ) : (
                <CodeBlock
                  code={JSON.stringify(part.output, null, 2)}
                  language="json"
                />
              )
            }
          />
        )}
      </ToolContent>
    </Tool>
  );
};

const AssistantTextPart = ({
  text,
  streaming,
}: {
  text: string;
  streaming: boolean;
}) => (
  <>
    {segmentText(text, streaming).map((segment, index) => {
      if (segment.kind === "markdown") {
        return segment.content.trim() ? (
          <MessageResponse key={index}>{segment.content}</MessageResponse>
        ) : null;
      }
      if (segment.kind === "jsx") {
        return (
          <JSXPreview
            isStreaming={segment.streaming}
            jsx={segment.content}
            key={index}
          >
            <JSXPreviewContent className="rounded-lg border bg-card p-4" />
            <JSXPreviewError />
          </JSXPreview>
        );
      }
      return (
        <Plan defaultOpen isStreaming={segment.streaming} key={index}>
          <PlanHeader>
            <div>
              <PlanTitle>{segment.plan?.title ?? "Plan"}</PlanTitle>
              {segment.plan?.description && (
                <PlanDescription>{segment.plan.description}</PlanDescription>
              )}
            </div>
            <PlanTrigger />
          </PlanHeader>
          <PlanContent>
            {(segment.plan?.steps ?? []).map((step, stepIndex) => (
              <ChainOfThoughtStep
                key={stepIndex}
                label={step.title}
                status={step.status ?? "pending"}
              />
            ))}
            {!segment.plan && (
              <MessageResponse>{`\`\`\`json\n${segment.raw}\n\`\`\``}</MessageResponse>
            )}
          </PlanContent>
        </Plan>
      );
    })}
  </>
);

const AssistantChainOfThought = ({ message }: { message: LiveMessage }) => {
  const toolParts = message.parts.filter((part): part is LiveToolPart =>
    part.type.startsWith("tool-")
  );
  if (toolParts.length === 0) return null;
  const files = toolParts.flatMap(touchedFiles);
  const active = toolParts.some(
    (part) => part.state === "input-streaming" || part.state === "input-available"
  );
  return (
    <ChainOfThought defaultOpen={active}>
      <ChainOfThoughtHeader>
        {active ? "Working…" : "Chain of thought"}
      </ChainOfThoughtHeader>
      <ChainOfThoughtContent>
        {toolParts.map((part) => (
          <ChainOfThoughtStep
            description={
              part.state === "output-error" ? part.errorText : undefined
            }
            icon={
              part.toolName === "shell"
                ? TerminalIcon
                : part.toolName === "editor"
                  ? FileCodeIcon
                  : WrenchIcon
            }
            key={part.toolCallId}
            label={part.toolName}
            status={
              part.state === "output-available" || part.state === "output-error"
                ? "complete"
                : "active"
            }
          >
            {touchedFiles(part).length > 0 && (
              <ChainOfThoughtSearchResults>
                {touchedFiles(part).map((file) => (
                  <ChainOfThoughtSearchResult key={file}>
                    {file}
                  </ChainOfThoughtSearchResult>
                ))}
              </ChainOfThoughtSearchResults>
            )}
          </ChainOfThoughtStep>
        ))}
        {files.length > 0 && (
          <Task defaultOpen={false}>
            <TaskTrigger
              title={`Touched ${files.length} file${files.length > 1 ? "s" : ""}`}
            />
            <TaskContent>
              {files.map((file) => (
                <TaskItem key={file}>
                  Modified <TaskItemFile>{file}</TaskItemFile>
                </TaskItem>
              ))}
            </TaskContent>
          </Task>
        )}
      </ChainOfThoughtContent>
    </ChainOfThought>
  );
};

const TurnAudio = ({ url }: { url: string }) => (
  <AudioPlayer className="mt-2 w-full max-w-md rounded-lg border bg-card px-2 py-1">
    <AudioPlayerElement src={url} />
    <AudioPlayerControlBar>
      <AudioPlayerPlayButton />
      <AudioPlayerSeekBackwardButton seekOffset={5} />
      <AudioPlayerSeekForwardButton seekOffset={5} />
      <AudioPlayerTimeDisplay />
      <AudioPlayerTimeRange />
      <AudioPlayerDurationDisplay />
      <AudioPlayerMuteButton />
      <AudioPlayerVolumeRange />
    </AudioPlayerControlBar>
  </AudioPlayer>
);

export const ChatThread = ({ agent }: { agent: LiveAgent }) => {
  const copyMessage = useCallback((message: LiveMessage) => {
    navigator.clipboard?.writeText(messageText(message));
  }, []);

  const downloadable = agent.messages.map((message) => ({
    id: message.id,
    role: message.role,
    parts: message.parts
      .filter((part) => part.type === "text")
      .map((part) => ({ type: "text" as const, text: part.text })),
  })) as UIMessage[];

  return (
    <Conversation className="relative flex-1">
      <ConversationContent className="mx-auto w-full max-w-3xl">
        {agent.messages.length === 0 && (
          <ConversationEmptyState
            description={
              agent.status === "connected"
                ? "Say something or type below — the Gemini Live agent is listening."
                : "Connect to start a live text or voice session with the meta-tooling agent."
            }
            icon={<CheckCircleIcon className="size-8" />}
            title="RandD Live"
          />
        )}
        {agent.messages.map((message) => (
          <Message from={message.role} key={message.id}>
            <MessageContent>
              {message.role === "assistant" && (
                <AssistantChainOfThought message={message} />
              )}
              {message.parts.map((part, index) => {
                if (part.type === "text") {
                  return message.role === "assistant" ? (
                    <AssistantTextPart
                      key={index}
                      streaming={part.state === "streaming"}
                      text={part.text}
                    />
                  ) : (
                    <Fragment key={index}>{part.text}</Fragment>
                  );
                }
                if (part.type === "file") {
                  if (part.mediaType.startsWith("image/")) {
                    const base64 = part.url.split(",")[1] ?? "";
                    return (
                      <Image
                        alt={part.filename ?? "attachment"}
                        base64={base64}
                        className="max-w-xs rounded-lg border"
                        key={index}
                        mediaType={part.mediaType}
                        uint8Array={new Uint8Array()}
                      />
                    );
                  }
                  return (
                    <a href={part.url} key={index} rel="noreferrer" target="_blank">
                      {part.filename ?? part.url}
                    </a>
                  );
                }
                return <ToolPartView key={index} part={part as LiveToolPart} />;
              })}
              {message.audioUrl && <TurnAudio url={message.audioUrl} />}
              <MessageActions>
                <MessageAction
                  label="Copy"
                  onClick={() => copyMessage(message)}
                  tooltip="Copy message"
                >
                  <CopyIcon className="size-3.5" />
                </MessageAction>
                {message.role === "user" && (
                  <MessageAction
                    label="Retry"
                    onClick={() => agent.retryUserMessage(message)}
                    tooltip="Send again"
                  >
                    <RefreshCcwIcon className="size-3.5" />
                  </MessageAction>
                )}
              </MessageActions>
            </MessageContent>
          </Message>
        ))}
      </ConversationContent>
      <ConversationScrollButton />
      {agent.messages.length > 0 && (
        <ConversationDownload
          filename="randd-live-session.md"
          messages={downloadable}
        />
      )}
    </Conversation>
  );
};
