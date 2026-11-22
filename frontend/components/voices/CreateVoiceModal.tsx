"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Loader2, Mic, RotateCcw, Square, UploadCloud, X, AlertCircle } from "lucide-react";
import { DialogFrame } from "@/components/ui/DialogFrame";
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

      let mimeType = "";
      if (typeof MediaRecorder !== "undefined" && typeof MediaRecorder.isTypeSupported === "function") {
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
          mimeType = "audio/webm;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/webm")) {
          mimeType = "audio/webm";
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
          mimeType = "audio/mp4";
        }
      }

      const options: MediaRecorderOptions = mimeType ? { mimeType } : {};
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        // Stop audio capture tracks cleanly after final recording chunk is emitted
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        const effectiveType = mediaRecorder.mimeType || mimeType || "audio/webm";
        const audioBlob = new Blob(audioChunksRef.current, { type: effectiveType });
        const ext = effectiveType.includes("mp4") ? "mp4" : effectiveType.includes("ogg") ? "ogg" : "webm";
        const recFile = new File([audioBlob], `mic_recording_${Date.now()}.${ext}`, {
          type: effectiveType,
        });
        setFile(recFile);
        const url = URL.createObjectURL(audioBlob);
        setRecordedAudioUrl(url);

        if (!voiceName) {
          setVoiceName("My Cloned Voice");
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
    if (recordTimerRef.current) {
      clearInterval(recordTimerRef.current);
      recordTimerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch (err) {
        // ignore
      }
    }
    setIsRecording(false);
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
    if (mode === "record" && recordSeconds > 0 && recordSeconds < 5) {
      setErrorMessage("Recorded audio sample is shorter than 5 seconds. Please record for at least 5 to 10 seconds.");
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
    <DialogFrame onClose={handleClose}>
      <div className="dialog-panel max-w-lg" role="dialog" aria-modal="true" aria-label="Clone a voice">
        {/* Header */}
        <div className="dialog-header flex items-center justify-between px-6 py-5 border-b border-line ">
          <div>
            <h3 className="font-semibold text-lg text-ink ">Clone a Voice</h3>
            <p className="text-xs text-muted">Step {step} of 3</p>
          </div>
          <button
            onClick={handleClose}
            aria-label="Close voice creation"
            className="p-1 rounded-lg text-muted hover:text-ink  hover:bg-soft  transition-colors"
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
                <label htmlFor="field-voiceName" className="block text-sm font-medium text-ink  mb-1">
                  Voice Name
                </label>
                <input id="field-voiceName"
                  type="text"
                  value={voiceName}
                  onChange={(e) => setVoiceName(e.target.value)}
                  placeholder="e.g. My Personal Narration Voice"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-line  bg-paper  text-ink  text-sm focus:outline-hidden focus:ring-2 focus:ring-accent "
                />
              </div>

              <div>
                <label htmlFor="field-language" className="block text-sm font-medium text-ink  mb-1">
                  Language
                </label>
                <select id="field-language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-line  bg-paper  text-ink  text-sm focus:outline-hidden focus:ring-2 focus:ring-accent "
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
                <label className="block text-sm font-medium text-ink  mb-2">
                  Reference Voice Audio
                </label>
                <div className="flex border-b border-line  mb-4">
                  <button
                    type="button"
                    onClick={() => {
                      if (mode !== "upload") {
                        stopRecordingCleanup();
                        setMode("upload");
                        if (file && file.name.startsWith("mic_recording_")) {
                          setFile(null);
                        }
                        if (recordedAudioUrl) {
                          URL.revokeObjectURL(recordedAudioUrl);
                          setRecordedAudioUrl(null);
                        }
                        if (transcript === "I authorize KolRep to clone my voice for personalized speech synthesis.") {
                          setTranscript("");
                        }
                        setErrorMessage(null);
                      }
                    }}
                    className={`pb-2 text-xs font-semibold px-3 border-b-2 transition-all ${
                      mode === "upload"
                        ? "border-ink  text-ink "
                        : "border-transparent text-muted hover:text-muted "
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <UploadCloud className="h-3.5 w-3.5" />
                      <span>Upload File</span>
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (mode !== "record") {
                        setMode("record");
                        if (file && !file.name.startsWith("mic_recording_")) {
                          setFile(null);
                        }
                        setErrorMessage(null);
                      }
                    }}
                    className={`pb-2 text-xs font-semibold px-3 border-b-2 transition-all ${
                      mode === "record"
                        ? "border-ink  text-ink "
                        : "border-transparent text-muted hover:text-muted "
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <Mic className="h-3.5 w-3.5" />
                      <span>Record with Microphone</span>
                    </div>
                  </button>
                </div>

                {mode === "upload" ? (
                  <div className="flex justify-center px-6 pt-5 pb-6 border-2 border-dashed border-line  rounded-md hover:border-neutral-400  transition-colors">
                    <div className="space-y-1 text-center">
                      <UploadCloud className="mx-auto h-10 w-10 text-muted" />
                      <div className="flex text-sm text-muted ">
                        <label className="relative cursor-pointer font-medium text-ink  underline hover:text-ink">
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
                      <p className="text-xs text-muted">
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
                  <div className="p-4 rounded-md border border-line  bg-canvas  space-y-4">
                    {/* Prompt Box */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                          Prompt Script to Read Aloud:
                        </span>
                        <span className="text-xs font-mono font-semibold text-ink ">
                          {recordSeconds}s / 10s
                        </span>
                      </div>
                      <p className="text-xs italic text-ink  bg-paper  p-3 rounded-lg border border-line   leading-relaxed">
                        &ldquo;I authorize KolRep to clone my voice for personalized speech synthesis.&rdquo;
                      </p>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-line  h-1.5 rounded-full overflow-hidden">
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
                          className="w-full sm:w-auto px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold flex items-center justify-center gap-2  transition-all"
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
                            className="px-3 py-1.5 rounded-lg border border-line  bg-paper  text-ink  text-xs font-medium hover:bg-soft flex items-center gap-1.5"
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
                              className="text-xs text-muted hover:text-ink  flex items-center gap-1"
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
                <div className="flex flex-wrap items-center justify-between gap-1 mb-2">
                  <label htmlFor="field-transcript" className="block text-sm font-medium text-ink ">
                    Spoken Transcript (Optional)
                  </label>
                  <span className="text-xs text-muted">Auto-detected if blank</span>
                </div>
                <textarea
                  id="field-transcript"
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder="What is said in the audio? Leave blank to auto-detect with Whisper AI."
                  rows={2}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-line  bg-paper  text-ink  text-sm focus:outline-hidden focus:ring-2 focus:ring-accent  resize-none"
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={handleNextToConsent}
                  className="px-5 py-2.5 rounded-lg bg-accent  text-white  text-sm font-medium hover:bg-soft  transition-colors"
                >
                  Continue to Consent
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-md bg-canvas  border border-line  space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Speaker Authorization & Verification
                </h4>

                <div>
                  <label className="text-sm font-medium text-ink  block mb-1">
                    Relationship to Speaker
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setSpeakerRelationship("self")}
                      className={`px-3 py-2 text-xs rounded-lg border font-medium transition-all ${
                        speakerRelationship === "self"
                          ? "border-ink  bg-paper  text-ink  "
                          : "border-line  text-muted "
                      }`}
                    >
                      I am the speaker
                    </button>
                    <button
                      type="button"
                      onClick={() => setSpeakerRelationship("authorized_representative")}
                      className={`px-3 py-2 text-xs rounded-lg border font-medium transition-all ${
                        speakerRelationship === "authorized_representative"
                          ? "border-ink  bg-paper  text-ink  "
                          : "border-line  text-muted "
                      }`}
                    >
                      Authorized Representative
                    </button>
                  </div>
                </div>

                <div className="space-y-2 pt-1">
                  <label className="text-xs font-medium text-ink  block">
                    Permitted Scope
                  </label>
                  <label className="flex items-center gap-2 text-xs text-muted  cursor-pointer">
                    <input
                      type="checkbox"
                      checked={speechGenAllowed}
                      onChange={(e) => setSpeechGenAllowed(e.target.checked)}
                      className="rounded border-line  text-ink"
                    />
                    <span>Allow Text-to-Speech narration generation</span>
                  </label>
                </div>
              </div>

              <label className="flex items-start gap-2.5 text-xs text-muted  cursor-pointer p-2">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-0.5 rounded border-line  text-ink"
                />
                <span>
                  I confirm that I have explicit authorization to clone this voice. I understand this synthetic profile will be used exclusively within KolRep and can be revoked at any time.
                </span>
              </label>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="px-4 py-2 text-sm text-muted  hover:text-ink"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!termsAccepted || isSubmitting}
                  className="px-5 py-2.5 rounded-lg bg-accent  text-white  text-sm font-medium hover:bg-soft  disabled:opacity-50 transition-colors "
                >
                  Start Cloning
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="py-8 text-center space-y-4">
              <Loader2 className="h-10 w-10 animate-spin mx-auto text-ink " />
              <div>
                <h4 className="font-semibold text-ink ">Cloning Voice...</h4>
                <p className="text-xs text-muted mt-1 max-w-xs mx-auto">
                  Validating audio quality, speech ratio, and generating high-fidelity acoustic embeddings.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </DialogFrame>
  );
}
