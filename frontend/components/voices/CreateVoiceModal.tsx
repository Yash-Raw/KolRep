"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Loader2, Mic, Play, RotateCcw, Square, UploadCloud, Volume2, X, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Voice } from "@/types";

interface CreateVoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newVoice: Voice) => void;
}

export function CreateVoiceModal({ isOpen, onClose, onSuccess }: CreateVoiceModalProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [mode, setMode] = useState<"upload" | "record">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [voiceName, setVoiceName] = useState("");
  const [transcript, setTranscript] = useState("");
  const [language, setLanguage] = useState("en");
  const [speakerRelationship, setSpeakerRelationship] = useState("self");
  const [speechGenAllowed, setSpeechGenAllowed] = useState(true);
  const [agentAllowed, setAgentAllowed] = useState(true);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // In-browser recording states
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordTimerRef = useRef<NodeJS.Timeout | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const stopRecordingCleanup = useCallback(() => {
    if (recordTimerRef.current) {
      clearInterval(recordTimerRef.current);
      recordTimerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsRecording(false);
  }, []);

  useEffect(() => {
    return () => {
      stopRecordingCleanup();
      if (recordedAudioUrl) {
        URL.revokeObjectURL(recordedAudioUrl);
      }
    };
  }, [recordedAudioUrl, stopRecordingCleanup]);

  const handleClose = () => {
    stopRecordingCleanup();
    onClose();
  };

  const startRecording = async () => {
    setErrorMessage(null);
    setRecordSeconds(0);
    audioChunksRef.current = [];
    if (recordedAudioUrl) {
      URL.revokeObjectURL(recordedAudioUrl);
      setRecordedAudioUrl(null);
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 24000,
        },
      });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const recFile = new File([audioBlob], `mic_recording_${Date.now()}.webm`, {
          type: mimeType,
        });
        setFile(recFile);
        const url = URL.createObjectURL(audioBlob);
        setRecordedAudioUrl(url);

        if (!voiceName) {
          setVoiceName("My Cloned Voice");
        }
        if (!transcript) {
          setTranscript("I authorize VoiceRep to clone my voice for personalized speech synthesis.");
        }
      };

      mediaRecorder.start(200);
      setIsRecording(true);

      const startTime = Date.now();
      recordTimerRef.current = setInterval(() => {
        const elapsed = Math.min(10, Math.floor((Date.now() - startTime) / 1000));
        setRecordSeconds(elapsed);
        if (elapsed >= 10) {
          stopRecording();
        }
      }, 250);
    } catch (err: any) {
      setErrorMessage(
        err.name === "NotAllowedError"
          ? "Microphone access was denied. Please allow microphone permissions in your browser."
          : `Failed to access microphone: ${err.message}`
      );
    }
  };

  const stopRecording = () => {
    stopRecordingCleanup();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (recordedAudioUrl) {
        URL.revokeObjectURL(recordedAudioUrl);
        setRecordedAudioUrl(null);
      }
      if (!voiceName) {
        const defaultName = selected.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
        setVoiceName(defaultName);
      }
      setErrorMessage(null);
    }
  };

  const handleNextToConsent = () => {
    if (!file) {
      setErrorMessage("Please upload or record an audio sample first.");
      return;
    }
    if (!voiceName.trim()) {
      setErrorMessage("Please enter a name for this voice clone.");
      return;
    }
    setErrorMessage(null);
    setStep(2);
  };

  const handleSubmit = async () => {
    if (!termsAccepted) {
      setErrorMessage("You must accept the terms of use and confirm speaker authorization.");
      return;
    }
    if (!file) return;

    setIsSubmitting(true);
    setErrorMessage(null);
    setStep(3);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", voiceName.trim());
      formData.append("language", language);
      formData.append("speaker_relationship", speakerRelationship);
      if (transcript.trim()) {
        formData.append("transcript", transcript.trim());
      }
      formData.append(
        "consent_scope",
        JSON.stringify({
          speech_generation: speechGenAllowed,
          ai_agent: agentAllowed,
        })
      );
      formData.append("terms_accepted", "true");

      const created = await api.createVoice(formData);
      onSuccess(created);
      handleClose();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to clone voice.");
      setStep(2);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-800">
          <div>
            <h3 className="font-semibold text-lg text-neutral-900 dark:text-white">Clone a Voice</h3>
            <p className="text-xs text-neutral-500">Step {step} of 3</p>
          </div>
          <button
            onClick={handleClose}
            className="p-1 rounded-lg text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {errorMessage && (
            <div className="mb-4 flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                  Voice Name
                </label>
                <input
                  type="text"
                  value={voiceName}
                  onChange={(e) => setVoiceName(e.target.value)}
                  placeholder="e.g. My Personal Narration Voice"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
                >
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="it">Italian</option>
                  <option value="ja">Japanese</option>
                  <option value="hi">Hindi</option>
                </select>
              </div>

              {/* Mode Toggle Tabs */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                  Reference Voice Audio
                </label>
                <div className="flex border-b border-neutral-200 dark:border-neutral-800 mb-4">
                  <button
                    type="button"
                    onClick={() => setMode("upload")}
                    className={`pb-2 text-xs font-semibold px-3 border-b-2 transition-all ${
                      mode === "upload"
                        ? "border-neutral-900 dark:border-white text-neutral-900 dark:text-white"
                        : "border-transparent text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <UploadCloud className="h-3.5 w-3.5" />
                      <span>Upload File</span>
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode("record")}
                    className={`pb-2 text-xs font-semibold px-3 border-b-2 transition-all ${
                      mode === "record"
                        ? "border-neutral-900 dark:border-white text-neutral-900 dark:text-white"
                        : "border-transparent text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <Mic className="h-3.5 w-3.5" />
                      <span>Record with Microphone</span>
                    </div>
                  </button>
                </div>

                {mode === "upload" ? (
                  <div className="flex justify-center px-6 pt-5 pb-6 border-2 border-dashed border-neutral-300 dark:border-neutral-700 rounded-xl hover:border-neutral-400 dark:hover:border-neutral-600 transition-colors">
                    <div className="space-y-1 text-center">
                      <UploadCloud className="mx-auto h-10 w-10 text-neutral-400" />
                      <div className="flex text-sm text-neutral-600 dark:text-neutral-400">
                        <label className="relative cursor-pointer font-medium text-neutral-900 dark:text-white underline hover:text-neutral-700">
                          <span>Upload an audio file</span>
                          <input
                            type="file"
                            accept="audio/*,video/mp4,video/webm"
                            onChange={handleFileChange}
                            className="sr-only"
                          />
                        </label>
                        <p className="pl-1">or drag and drop</p>
                      </div>
                      <p className="text-xs text-neutral-500">
                        6–12 seconds recommended (clean speech, minimal background noise)
                      </p>
                      {file && !recordedAudioUrl && (
                        <p className="mt-2 text-xs font-mono font-medium text-emerald-600 dark:text-emerald-400">
                          Selected: {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950/60 space-y-4">
                    {/* Prompt Box */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                          Prompt Script to Read Aloud:
                        </span>
                        <span className="text-xs font-mono font-semibold text-neutral-700 dark:text-neutral-300">
                          {recordSeconds}s / 10s
                        </span>
                      </div>
                      <p className="text-xs italic text-neutral-800 dark:text-neutral-200 bg-white dark:bg-neutral-900 p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-2xs leading-relaxed">
                        &ldquo;I authorize VoiceRep to clone my voice for personalized speech synthesis.&rdquo;
                      </p>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-neutral-200 dark:bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-red-500 h-full transition-all duration-200"
                        style={{ width: `${(recordSeconds / 10) * 100}%` }}
                      ></div>
                    </div>

                    {/* Recording Controls */}
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
                      {!isRecording && !recordedAudioUrl && (
                        <button
                          type="button"
                          onClick={startRecording}
                          className="w-full sm:w-auto px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-sm transition-all"
                        >
                          <Mic className="h-4 w-4" />
                          <span>Start 10s Recording</span>
                        </button>
                      )}

                      {isRecording && (
                        <div className="flex items-center justify-between w-full">
                          <div className="flex items-center gap-2 text-xs font-medium text-red-600 dark:text-red-400">
                            <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping"></span>
                            <span>Recording... Speak clearly</span>
                          </div>
                          <button
                            type="button"
                            onClick={stopRecording}
                            className="px-3 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-800 dark:text-neutral-200 text-xs font-medium hover:bg-neutral-100 flex items-center gap-1.5"
                          >
                            <Square className="h-3 w-3 fill-current text-red-500" />
                            <span>Done Speaking</span>
                          </button>
                        </div>
                      )}

                      {recordedAudioUrl && !isRecording && (
                        <div className="space-y-3 w-full">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                              <Check className="h-3.5 w-3.5" />
                              Audio Sample Recorded ({recordSeconds}s)
                            </span>
                            <button
                              type="button"
                              onClick={startRecording}
                              className="text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-white flex items-center gap-1"
                            >
                              <RotateCcw className="h-3 w-3" />
                              <span>Record Again</span>
                            </button>
                          </div>
                          <audio
                            src={recordedAudioUrl}
                            controls
                            className="w-full h-9 rounded-lg"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                    Spoken Transcript (Optional)
                  </label>
                  <span className="text-xs text-neutral-500">Auto-detected if blank</span>
                </div>
                <textarea
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder="What is said in the audio? Leave blank to auto-detect with Whisper AI."
                  rows={2}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white resize-none"
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={handleNextToConsent}
                  className="px-5 py-2.5 rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors"
                >
                  Continue to Consent
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-200 dark:border-neutral-700/60 space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
                  Speaker Authorization & Verification
                </h4>

                <div>
                  <label className="text-sm font-medium text-neutral-900 dark:text-white block mb-1">
                    Relationship to Speaker
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setSpeakerRelationship("self")}
                      className={`px-3 py-2 text-xs rounded-lg border font-medium transition-all ${
                        speakerRelationship === "self"
                          ? "border-neutral-900 dark:border-white bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white shadow-xs"
                          : "border-neutral-200 dark:border-neutral-800 text-neutral-600 dark:text-neutral-400"
                      }`}
                    >
                      I am the speaker
                    </button>
                    <button
                      type="button"
                      onClick={() => setSpeakerRelationship("authorized_representative")}
                      className={`px-3 py-2 text-xs rounded-lg border font-medium transition-all ${
                        speakerRelationship === "authorized_representative"
                          ? "border-neutral-900 dark:border-white bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white shadow-xs"
                          : "border-neutral-200 dark:border-neutral-800 text-neutral-600 dark:text-neutral-400"
                      }`}
                    >
                      Authorized Representative
                    </button>
                  </div>
                </div>

                <div className="space-y-2 pt-1">
                  <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300 block">
                    Permitted Scope
                  </label>
                  <label className="flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={speechGenAllowed}
                      onChange={(e) => setSpeechGenAllowed(e.target.checked)}
                      className="rounded border-neutral-300 dark:border-neutral-700 text-neutral-900"
                    />
                    <span>Allow Text-to-Speech narration generation</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={agentAllowed}
                      onChange={(e) => setAgentAllowed(e.target.checked)}
                      className="rounded border-neutral-300 dark:border-neutral-700 text-neutral-900"
                    />
                    <span>Allow Conversational AI Voice Agents</span>
                  </label>
                </div>
              </div>

              <label className="flex items-start gap-2.5 text-xs text-neutral-600 dark:text-neutral-400 cursor-pointer p-2">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-0.5 rounded border-neutral-300 dark:border-neutral-700 text-neutral-900"
                />
                <span>
                  I confirm that I have explicit authorization to clone this voice. I understand this synthetic profile will be used exclusively within VoiceRep and can be revoked at any time.
                </span>
              </label>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="px-4 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!termsAccepted || isSubmitting}
                  className="px-5 py-2.5 rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 disabled:opacity-50 transition-colors shadow-sm"
                >
                  Start Cloning
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="py-8 text-center space-y-4">
              <Loader2 className="h-10 w-10 animate-spin mx-auto text-neutral-900 dark:text-white" />
              <div>
                <h4 className="font-semibold text-neutral-900 dark:text-white">Cloning Voice...</h4>
                <p className="text-xs text-neutral-500 mt-1 max-w-xs mx-auto">
                  Validating audio quality, speech ratio, and generating high-fidelity acoustic embeddings.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
