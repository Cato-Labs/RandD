import { AudioLinesIcon, PhoneIcon, PhoneOffIcon } from "lucide-react";
import { useState } from "react";
import { Persona } from "@/components/ai-elements/persona";
import {
  Transcription,
  TranscriptionSegment,
} from "@/components/ai-elements/transcription";
import {
  VoiceSelector,
  VoiceSelectorAccent,
  VoiceSelectorAge,
  VoiceSelectorAttributes,
  VoiceSelectorBullet,
  VoiceSelectorContent,
  VoiceSelectorDescription,
  VoiceSelectorEmpty,
  VoiceSelectorGender,
  VoiceSelectorGroup,
  VoiceSelectorInput,
  VoiceSelectorItem,
  VoiceSelectorList,
  VoiceSelectorName,
  VoiceSelectorTrigger,
} from "@/components/ai-elements/voice-selector";
import { Button } from "@/components/ui/button";
import type { LiveAgent } from "@/hooks/use-live-agent";

/** Voice dock: live persona, session controls, voice picker, rolling transcript. */
export const VoiceDock = ({ agent }: { agent: LiveAgent }) => {
  const [transcriptTime, setTranscriptTime] = useState(0);

  return (
    <aside className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l bg-sidebar p-4">
      <div className="flex flex-col items-center gap-2">
        <Persona
          className="size-40"
          state={agent.personaState}
          variant="halo"
        />
        <p className="font-medium text-sm">{agent.agentCard?.name ?? "RandD Live"}</p>
        <p className="text-muted-foreground text-xs capitalize">
          {agent.personaState}
          {agent.status === "connected" && ` · ${agent.voice}`}
        </p>
      </div>

      <div className="flex items-center justify-center gap-2">
        {agent.status === "connected" ? (
          <Button onClick={() => agent.disconnect()} variant="destructive">
            <PhoneOffIcon className="size-4" />
            End session
          </Button>
        ) : (
          <Button
            disabled={agent.status === "connecting"}
            onClick={() => agent.connect()}
          >
            <PhoneIcon className="size-4" />
            {agent.status === "connecting" ? "Connecting…" : "Connect"}
          </Button>
        )}
      </div>

      <VoiceSelector onValueChange={(value) => value && agent.setVoice(value)} value={agent.voice}>
        <VoiceSelectorTrigger asChild>
          <Button className="w-full justify-start" variant="outline">
            <AudioLinesIcon className="size-4" />
            Voice: {agent.voice}
          </Button>
        </VoiceSelectorTrigger>
        <VoiceSelectorContent title="Choose a Gemini Live voice">
          <VoiceSelectorInput placeholder="Search voices…" />
          <VoiceSelectorList>
            <VoiceSelectorEmpty>No voices found.</VoiceSelectorEmpty>
            <VoiceSelectorGroup heading="Gemini Live prebuilt voices">
              {agent.voices.map((voice) => (
                <VoiceSelectorItem key={voice.id} value={voice.id}>
                  <div className="flex flex-col gap-1">
                    <VoiceSelectorName>{voice.name}</VoiceSelectorName>
                    <VoiceSelectorDescription>
                      {voice.description}
                    </VoiceSelectorDescription>
                    <VoiceSelectorAttributes>
                      <VoiceSelectorGender value={voice.gender === "neutral" ? undefined : voice.gender} />
                      <VoiceSelectorBullet />
                      <VoiceSelectorAccent value={voice.accent.toLowerCase() as "american"} />
                      <VoiceSelectorBullet />
                      <VoiceSelectorAge>{voice.age}</VoiceSelectorAge>
                    </VoiceSelectorAttributes>
                  </div>
                </VoiceSelectorItem>
              ))}
            </VoiceSelectorGroup>
          </VoiceSelectorList>
        </VoiceSelectorContent>
      </VoiceSelector>
      {agent.status === "connected" && (
        <p className="text-center text-muted-foreground text-xs">
          Changing voice reconnects the live session.
        </p>
      )}

      <div className="min-h-0 flex-1">
        <p className="mb-2 font-medium text-muted-foreground text-xs uppercase tracking-wide">
          Live transcript
        </p>
        {agent.segments.length === 0 ? (
          <p className="text-muted-foreground text-xs">
            Transcript segments appear here as you and the agent speak.
          </p>
        ) : (
          <Transcription
            currentTime={transcriptTime}
            onSeek={setTranscriptTime}
            segments={agent.segments.map((segment) => ({
              text: segment.text,
              startSecond: segment.startSecond,
              endSecond: segment.endSecond,
            }))}
          >
            {(segment, index) => (
              <TranscriptionSegment
                className={
                  agent.segments[index]?.role === "user"
                    ? "font-medium"
                    : undefined
                }
                index={index}
                key={index}
                segment={segment}
              />
            )}
          </Transcription>
        )}
      </div>
    </aside>
  );
};
