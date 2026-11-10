"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AlertCircle, ArrowLeft, Bot, Mic, MicOff, PhoneCall, PhoneOff, Volume2, Waves } from "lucide-react";
import { PageHeader } from "@/components/ui/StudioUI";
import { api } from "@/lib/api";
import { Agent, AgentSessionConfig, Voice } from "@/types";

type AgentState = "disconnected" | "connecting" | "listening" | "thinking" | "speaking";

interface TranscriptMessage {
  id: string;
  sender: "user" | "agent";
  text: string;
  time: string;
}

export default function AgentPlaygroundPage() {
  const params = useParams();
  const router = useRouter();
  const agentId = params.id as string;

  const [agent, setAgent] = useState<Agent | null>(null);
  const [voice, setVoice] = useState<Voice | null>(null);
  const [loading, setLoading] = useState(true);
  const [agentState, setAgentState] = useState<AgentState>("disconnected");
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    loadAgentData();
    return () => {
      endConversation();
    };
  }, [agentId]);

  const loadAgentData = async () => {
    setLoading(true);
    try {
      const a = await api.getAgent(agentId);
      setAgent(a);
      if (a.voice_id) {
        const v = await api.getVoice(a.voice_id);
        setVoice(v);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load agent");
    } finally {
      setLoading(false);
    }
  };

  const startConversation = async () => {
    setErrorMessage(null);
    setAgentState("connecting");

    try {
      // 1. Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      mediaStreamRef.current = stream;

      // 2. Request authenticated session from backend
      const sessionConfig: AgentSessionConfig = await api.startAgentSession(agentId);

      // Add agent's first greeting to transcript
      if (agent?.first_message) {
        setTranscripts([
          {
            id: "greeting",
            sender: "agent",
            text: agent.first_message,
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      }

      // 3. Connect to WebSocket
      const ws = new WebSocket(sessionConfig.signed_url);
      socketRef.current = ws;

      ws.onopen = () => {
        setAgentState("listening");
        // Start call duration timer
        timerRef.current = setInterval(() => {
          setCallDuration((prev) => prev + 1);
        }, 1000);

        // Send conversation initiation config
        ws.send(
          JSON.stringify({
            type: "conversation_initiation_client_data",
            conversation_config_override: sessionConfig.session_config.overrides,
          })
        );

        // Start live microphone streaming over WebSocket
        try {
          const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus"
            : MediaRecorder.isTypeSupported("audio/webm")
            ? "audio/webm"
            : "audio/mp4";

          const recorder = new MediaRecorder(stream, { mimeType });
          mediaRecorderRef.current = recorder;

          recorder.ondataavailable = async (e) => {
            if (e.data && e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
              const reader = new FileReader();
              reader.onloadend = () => {
                const res = reader.result as string;
                const base64Audio = res.includes(",") ? res.split(",")[1] : res;
                if (base64Audio && ws.readyState === WebSocket.OPEN) {
                  ws.send(
                    JSON.stringify({
                      type: "audio_chunk",
                      data: base64Audio,
                    })
                  );
                }
              };
              reader.readAsDataURL(e.data);
            }
          };

          // Capture 750ms audio slices for responsive turnaround
          recorder.start(750);
        } catch (recErr) {
          console.warn("MediaRecorder streaming initialization warning:", recErr);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "agent_response") {
            setTranscripts((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                sender: "agent",
                text: data.agent_response_event?.agent_response || "",
                time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              },
            ]);
          } else if (data.type === "user_transcript") {
            setAgentState("thinking");
            setTranscripts((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                sender: "user",
                text: data.user_transcription_event?.user_transcript || "",
                time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              },
            ]);
          } else if (data.type === "audio") {
            // Play received agent voice audio packet through speakers
            const b64 = data.audio_event?.audio_base_64;
            if (b64) {
              try {
                if (currentAudioRef.current) {
                  currentAudioRef.current.pause();
                  currentAudioRef.current = null;
                }
                const audioBytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
                const audioBlob = new Blob([audioBytes], { type: "audio/mpeg" });
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                currentAudioRef.current = audio;
                setAgentState("speaking");

                audio.onended = () => {
                  URL.revokeObjectURL(audioUrl);
                  currentAudioRef.current = null;
                  setAgentState("listening");
                };

                audio.onerror = () => {
                  URL.revokeObjectURL(audioUrl);
                  currentAudioRef.current = null;
                  setAgentState("listening");
                };

                audio.play().catch(() => {
                  setAgentState("listening");
                });
              } catch (e) {
                setAgentState("listening");
              }
            }
          } else if (data.type === "interruption") {
            if (currentAudioRef.current) {
              currentAudioRef.current.pause();
              currentAudioRef.current = null;
            }
            setAgentState("listening");
          }
        } catch {
          // Non-JSON binary audio packet
        }
      };

      ws.onerror = () => {
        setErrorMessage("WebSocket connection error. Please verify voice agent configuration.");
        endConversation();
      };

      ws.onclose = () => {
        endConversation();
      };
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to start conversation session.");
      endConversation();
    }
  };

  const endConversation = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {}
      mediaRecorderRef.current = null;
    }
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setAgentState("disconnected");
  };

  const toggleMute = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = isMuted;
      });
      setIsMuted(!isMuted);
    }
  };

  const formatDuration = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  const getStateBadge = () => {
    switch (agentState) {
      case "connecting":
        return (
          <span className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            Connecting...
          </span>
        );
      case "listening":
        return (
          <span className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
            Listening to you...
          </span>
        );
      case "thinking":
        return (
          <span className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
            Thinking...
          </span>
        );
      case "speaking":
        return (
          <span className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
            <Volume2 className="h-3.5 w-3.5 text-purple-500 animate-bounce" />
            Speaking in {voice?.name || "cloned voice"}
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-soft  text-muted ">
            <span className="w-2 h-2 rounded-full bg-neutral-400"></span>
            Ready to call
          </span>
        );
    }
  };

  return (
    <div className="page playground-page space-y-6">
      {/* Top Bar */}
      <div className="flex items-center justify-between">
        <Link
          href="/agents"
          className="inline-flex items-center gap-2 text-xs font-medium text-muted hover:text-ink  transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Agents</span>
        </Link>

        {agentState !== "disconnected" && (
          <div className="font-mono text-xs px-3 py-1 rounded-full border border-line  bg-paper  text-muted ">
            Call Duration: {formatDuration(callDuration)}
          </div>
        )}
      </div>

      {errorMessage && (
        <div className="flex items-center gap-2 p-4 rounded-md bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      <PageHeader number="04" label="Agent playground" title={agent?.name || "Agent playground"} description="Your voice agent console. Start a conversation and follow the transcript." />
      {/* Main Conversation Container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Agent Profile & Interactive Call Card */}
        <div className="playground-console panel p-6 flex flex-col justify-between space-y-8">
          <div className="space-y-6 text-center">
            {/* Visual Call Orb */}
            <div className="relative mx-auto w-32 h-32 flex items-center justify-center">
              <div
                className={`absolute inset-0 rounded-full transition-all duration-700 ${
                  agentState === "speaking"
                    ? "bg-purple-500/20 scale-125 animate-ping"
                    : agentState === "listening"
                    ? "bg-emerald-500/20 scale-110 animate-pulse"
                    : "bg-soft "
                }`}
              ></div>
              <div className="relative z-10 w-24 h-24 rounded-full bg-accent  text-white  flex items-center justify-center ">
                <Bot className="h-10 w-10" />
              </div>
            </div>

            <div>
              <h2 className="text-xl font-bold text-ink ">
                {agent?.name || "AI Voice Agent"}
              </h2>
              <p className="text-xs text-muted mt-1">
                Speaking with: <span className="font-semibold text-ink ">{voice?.name || "Cloned Voice"}</span>
              </p>
            </div>

            <div className="flex justify-center">{getStateBadge()}</div>
          </div>

          {/* Call Controls */}
          <div className="space-y-3 pt-6 border-t border-line ">
            {agentState === "disconnected" ? (
              <button
                onClick={startConversation}
                className="w-full py-3.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm transition-all   flex items-center justify-center gap-2.5 active:scale-98"
              >
                <PhoneCall className="h-4 w-4" />
                <span>Start Voice Conversation</span>
              </button>
            ) : (
              <div className="flex items-center gap-3">
                <button
                  onClick={toggleMute}
                  title={isMuted ? "Unmute Microphone" : "Mute Microphone"}
                  className={`p-3.5 rounded-lg border transition-all ${
                    isMuted
                      ? "bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800 text-red-600"
                      : "bg-soft  border-line  text-ink "
                  }`}
                >
                  {isMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
                </button>

                <button
                  onClick={endConversation}
                  className="flex-1 py-3.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium text-sm transition-all  flex items-center justify-center gap-2.5 active:scale-98"
                >
                  <PhoneOff className="h-4 w-4" />
                  <span>End Conversation</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right: Live Transcript Stream */}
        <div className="playground-transcript panel lg:col-span-2 p-6 flex flex-col justify-between h-[520px]">
          <div className="flex items-center justify-between pb-3 border-b border-line ">
            <h3 className="font-semibold text-sm text-ink ">Live Conversation Transcript</h3>
            <span className="text-xs text-muted">Real-time turn stream</span>
          </div>

          <div className="flex-1 overflow-y-auto py-4 space-y-4">
            {transcripts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-muted space-y-2">
                <Waves className="h-8 w-8 stroke-1" />
                <p className="text-xs">Start a conversation and speak into your microphone.</p>
                <p className="text-[11px] text-muted">Transcripts will stream here in real time.</p>
              </div>
            ) : (
              transcripts.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-4 py-3 text-xs leading-relaxed  ${
                      msg.sender === "user"
                        ? "bg-accent  text-white  rounded-tr-xs"
                        : "bg-soft  text-ink  rounded-tl-xs"
                    }`}
                  >
                    <p>{msg.text}</p>
                  </div>
                  <span className="text-[10px] text-muted mt-1 px-1">{msg.time}</span>
                </div>
              ))
            )}
          </div>

          <div className="pt-3 border-t border-line  flex items-center justify-between text-[11px] text-muted">
            <span>Powered by VoiceRep Self-Hosted Neural Engine</span>
            <span>Interrupt speaking agent anytime</span>
          </div>
        </div>
      </div>
    </div>
  );
}
