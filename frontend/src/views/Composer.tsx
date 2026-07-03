import { MicIcon, MicOffIcon, WorkflowIcon, XIcon } from "lucide-react";
import { useCallback, useState } from "react";
import {
  Attachment,
  AttachmentInfo,
  AttachmentHoverCard,
  AttachmentHoverCardContent,
  AttachmentHoverCardTrigger,
  AttachmentPreview,
  AttachmentRemove,
  Attachments,
} from "@/components/ai-elements/attachments";
import {
  MicSelector,
  MicSelectorContent,
  MicSelectorEmpty,
  MicSelectorInput,
  MicSelectorItem,
  MicSelectorLabel,
  MicSelectorList,
  MicSelectorTrigger,
  MicSelectorValue,
} from "@/components/ai-elements/mic-selector";
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuTrigger,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputHeader,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInputAttachments,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import {
  Queue,
  QueueItem,
  QueueItemAction,
  QueueItemActions,
  QueueItemContent,
  QueueItemIndicator,
  QueueList,
  QueueSection,
  QueueSectionContent,
  QueueSectionLabel,
  QueueSectionTrigger,
} from "@/components/ai-elements/queue";
import { SpeechInput } from "@/components/ai-elements/speech-input";
import type { LiveAgent } from "@/hooks/use-live-agent";

const ComposerAttachments = () => {
  const attachments = usePromptInputAttachments();
  if (attachments.files.length === 0) return null;
  return (
    <Attachments variant="inline">
      {attachments.files.map((file) => (
        <AttachmentHoverCard key={file.id}>
          <AttachmentHoverCardTrigger asChild>
            <Attachment
              data={file}
              onRemove={() => attachments.remove(file.id)}
            >
              <AttachmentPreview />
              <AttachmentRemove />
            </Attachment>
          </AttachmentHoverCardTrigger>
          <AttachmentHoverCardContent>
            <AttachmentPreview className="size-40" />
            <AttachmentInfo />
          </AttachmentHoverCardContent>
        </AttachmentHoverCard>
      ))}
    </Attachments>
  );
};

const PromptQueue = ({ agent }: { agent: LiveAgent }) => {
  const pending = agent.queue.filter((entry) => entry.status === "pending");
  const completed = agent.queue.filter((entry) => entry.status === "completed");
  if (agent.queue.length === 0) return null;
  return (
    <Queue className="mx-auto mb-2 w-full max-w-3xl">
      <QueueSection defaultOpen>
        <QueueSectionTrigger>
          <QueueSectionLabel count={pending.length} label="Queued prompts" />
        </QueueSectionTrigger>
        <QueueSectionContent>
          <QueueList>
            {pending.map((entry) => (
              <QueueItem key={entry.id}>
                <QueueItemIndicator />
                <QueueItemContent>{entry.text}</QueueItemContent>
                <QueueItemActions>
                  <QueueItemAction
                    aria-label="Remove from queue"
                    onClick={() => agent.cancelQueued(entry.id)}
                  >
                    <XIcon className="size-3" />
                  </QueueItemAction>
                </QueueItemActions>
              </QueueItem>
            ))}
          </QueueList>
        </QueueSectionContent>
      </QueueSection>
      {completed.length > 0 && (
        <QueueSection>
          <QueueSectionTrigger>
            <QueueSectionLabel count={completed.length} label="Sent" />
          </QueueSectionTrigger>
          <QueueSectionContent>
            <QueueList>
              {completed.map((entry) => (
                <QueueItem key={entry.id}>
                  <QueueItemIndicator completed />
                  <QueueItemContent completed>{entry.text}</QueueItemContent>
                </QueueItem>
              ))}
            </QueueList>
          </QueueSectionContent>
        </QueueSection>
      )}
    </Queue>
  );
};

export const Composer = ({
  agent,
  workflowOpen,
  onToggleWorkflow,
}: {
  agent: LiveAgent;
  workflowOpen: boolean;
  onToggleWorkflow: () => void;
}) => {
  const [text, setText] = useState("");

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      agent.submit({
        text: message.text,
        files: message.files.map((file) => ({
          url: file.url,
          mediaType: file.mediaType ?? "application/octet-stream",
          filename: file.filename,
        })),
      });
      setText("");
    },
    [agent]
  );

  const toggleMic = useCallback(() => {
    if (agent.micActive) {
      agent.stopMic();
    } else {
      agent.startMic();
    }
  }, [agent]);

  return (
    <div className="border-t bg-background/95 px-4 pt-2 pb-4 backdrop-blur">
      <PromptQueue agent={agent} />
      <PromptInput
        accept="image/*"
        className="mx-auto w-full max-w-3xl"
        globalDrop
        multiple
        onSubmit={handleSubmit}
      >
        <PromptInputHeader>
          <ComposerAttachments />
        </PromptInputHeader>
        <PromptInputBody>
          <PromptInputTextarea
            onChange={(event) => setText(event.target.value)}
            placeholder={
              agent.status === "connected"
                ? "Message the live agent… (drop images anywhere)"
                : "Connect first, then message the live agent…"
            }
            value={text}
          />
        </PromptInputBody>
        <PromptInputFooter>
          <PromptInputTools>
            <PromptInputActionMenu>
              <PromptInputActionMenuTrigger />
              <PromptInputActionMenuContent>
                <PromptInputActionAddAttachments label="Attach images" />
              </PromptInputActionMenuContent>
            </PromptInputActionMenu>
            <SpeechInput
              className="shrink-0"
              onTranscriptionChange={setText}
              size="icon-sm"
              variant="ghost"
            />
            <PromptInputButton
              disabled={agent.status !== "connected"}
              onClick={toggleMic}
              variant={agent.micActive ? "default" : "ghost"}
            >
              {agent.micActive ? (
                <MicOffIcon className="size-4" />
              ) : (
                <MicIcon className="size-4" />
              )}
              <span>{agent.micActive ? "Mute" : "Mic"}</span>
            </PromptInputButton>
            <MicSelector
              onValueChange={(deviceId) =>
                deviceId && agent.selectMicDevice(deviceId)
              }
              value={agent.micDeviceId}
            >
              <MicSelectorTrigger
                className="h-8 max-w-48 border-none text-muted-foreground"
                size="sm"
                variant="ghost"
              >
                <MicSelectorValue className="truncate text-xs" />
              </MicSelectorTrigger>
              <MicSelectorContent>
                <MicSelectorInput placeholder="Search microphones…" />
                <MicSelectorList>
                  {(devices) => (
                    <>
                      <MicSelectorEmpty>No microphones found.</MicSelectorEmpty>
                      {devices.map((device) => (
                        <MicSelectorItem
                          key={device.deviceId}
                          value={device.deviceId}
                        >
                          <MicSelectorLabel device={device} />
                        </MicSelectorItem>
                      ))}
                    </>
                  )}
                </MicSelectorList>
              </MicSelectorContent>
            </MicSelector>
            <PromptInputButton
              onClick={onToggleWorkflow}
              variant={workflowOpen ? "default" : "ghost"}
            >
              <WorkflowIcon className="size-4" />
              <span>Workflow</span>
            </PromptInputButton>
          </PromptInputTools>
          <PromptInputSubmit
            disabled={agent.status !== "connected" && !text.trim()}
            status={agent.chatStatus === "ready" ? undefined : agent.chatStatus}
          />
        </PromptInputFooter>
      </PromptInput>
    </div>
  );
};
