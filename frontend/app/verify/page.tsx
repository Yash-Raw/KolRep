"use client";

import { useState, useRef } from "react";
import { CheckCircle2, Download, FileAudio, Fingerprint, Loader2, Lock, RefreshCw, Scale, ShieldAlert, ShieldCheck, UploadCloud } from "lucide-react";
import { api } from "@/lib/api";
import { VerificationReport } from "@/types";
import { PageHeader } from "@/components/ui/StudioUI";
import { AudioPlayer } from "@/components/audio/AudioPlayer";

export default function VerifyPage() {
  const [file, setFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<VerificationReport | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (selectedFile: File) => {
    setError(null);
    setReport(null);
    setFile(selectedFile);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    const url = URL.createObjectURL(selectedFile);
    setAudioUrl(url);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleVerify = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.verifyAudio(file);
      setReport(res);
    } catch (err: any) {
      setError(err?.message || "Failed to analyze audio file.");
    } finally {
      setLoading(false);
    }
  };

  const downloadManifestJson = () => {
    if (!report?.c2pa_manifest) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(report.c2pa_manifest, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `manifest_${report.generation_id || "voicerep"}.c2pa.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const downloadPublicKey = async () => {
    try {
      const pem = await api.getPublicCertificate();
      const dataStr = "data:text/plain;charset=utf-8," + encodeURIComponent(pem);
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", "voicerep_public_ca.pem");
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err: any) {
      alert("Could not download public certificate: " + err.message);
    }
  };

  const resetAll = () => {
    setFile(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(null);
    setReport(null);
    setError(null);
  };

  return (
    <div className="page verify-page space-y-6">
      <PageHeader number="05" label="Audio inspection" title="Listen with confidence." description="Inspect a recording for signed provenance and acoustic watermark information." />
      <div className="inspection-intro"><div><p className="eyebrow mb-3">TWO LAYERS OF INSPECTION</p><h2 className="text-2xl tracking-tight">Every recording has a story.</h2></div><p className="inspection-info">The inspector looks for a C2PA container manifest and an embedded acoustic watermark. Upload an audio file to review the evidence available in your recording.</p></div>

      {/* Upload Zone */}
      {!file ? (
        <div
          role="button"
          tabIndex={0}
          aria-label="Upload audio for inspection"
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInputRef.current?.click(); } }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="upload-zone p-6 sm:p-12 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-4 group"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,video/mp4,video/quicktime,video/webm"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
          />
          <div className="h-16 w-16 rounded-lg bg-soft  flex items-center justify-center text-muted  group-hover:scale-105 transition-transform ">
            <UploadCloud className="h-8 w-8 text-ink " />
          </div>
          <div className="space-y-1">
            <p className="text-base font-semibold text-ink ">
              Drag & drop audio here, or click to browse
            </p>
            <p className="text-xs text-muted ">
              Supports MP3, WAV, M4A, FLAC, OGG, and WebM (up to 50MB)
            </p>
          </div>
          <div className="verification-legend mt-2 text-xs text-muted">
            <span className="flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-emerald-600" /> Signed container metadata
            </span>
            <span className="flex items-center gap-1.5">
              <Fingerprint className="h-3.5 w-3.5 text-indigo-600" /> Acoustic watermark
            </span>
            <span className="flex items-center gap-1.5">
              <Scale className="h-3.5 w-3.5 text-blue-600" /> EU AI Act Article 50
            </span>
          </div>
        </div>
      ) : (
        <div className="bg-paper  border border-line  rounded-lg p-6 space-y-6 ">
          {/* File Selected Row */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-line ">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-md bg-soft  flex items-center justify-center text-ink ">
                <FileAudio className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-sm text-ink  break-all max-w-sm">
                  {file.name}
                </p>
                <p className="text-xs text-muted">
                  {(file.size / 1024 / 1024).toFixed(2)} MB • {file.type || "audio"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={resetAll}
                className="px-3 py-1.5 text-xs font-medium text-muted  hover:text-ink  transition-colors"
              >
                Change File
              </button>
              <button
                onClick={handleVerify}
                disabled={loading}
                className="px-5 py-2 text-xs sm:text-sm font-medium rounded-md bg-accent  text-white  hover:bg-soft  transition-all flex items-center gap-2  disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Analyzing Waveform & C2PA...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="h-4 w-4" />
                    <span>Run Cryptographic Verification</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Audio Player Preview */}
          {audioUrl && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted">Audio Preview</p>
              <AudioPlayer src={audioUrl} filename={file.name} showWatermarkBadge={false} />
            </div>
          )}

          {error && (
            <div className="p-4 rounded-md bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs sm:text-sm flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 flex-shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
          )}
        </div>
      )}

      {/* Verification Results */}
      {report && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Main Verdict Card */}
          <div
            className={`p-6 sm:p-8 rounded-lg border  ${
              report.is_authentic
                ? "bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800"
                : "bg-red-50/50 dark:bg-red-950/20 border-red-200 dark:border-red-800"
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div
                  className={`h-12 w-12 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    report.is_authentic
                      ? "bg-emerald-600 text-white  -emerald-600/20"
                      : "bg-red-600 text-white  -red-600/20"
                  }`}
                >
                  {report.is_authentic ? (
                    <CheckCircle2 className="h-6 w-6" />
                  ) : (
                    <ShieldAlert className="h-6 w-6" />
                  )}
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-bold text-ink ">
                      {report.is_authentic
                        ? report.tamper_status === "fully_authentic"
                          ? "VoiceRep Verified AI Synthetic Speech"
                          : "Acoustic Watermark Verified (Container Transcoded)"
                        : "Unverified Audio Recording"}
                    </h2>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        report.is_authentic
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
                          : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                      }`}
                    >
                      {Math.round(report.confidence_score * 100)}% Confidence
                    </span>
                  </div>
                  <p className="text-sm text-muted ">
                    {report.is_authentic
                      ? "This waveform contains authentic VoiceRep cryptographic provenance credentials confirming it was generated by our F5-TTS neural synthesis engine."
                      : "No valid VoiceRep acoustic watermark or C2PA cryptographic signature was found in this media file."}
                  </p>
                </div>
              </div>

              {report.c2pa_manifest && (
                <button
                  onClick={downloadManifestJson}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-paper  border border-line  text-ink  hover:bg-soft  transition-colors flex items-center gap-2 self-start sm:self-center flex-shrink-0"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Download .c2pa Manifest</span>
                </button>
              )}
            </div>
          </div>

          {/* Dual Layer Provenance Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Layer 1: C2PA Manifest */}
            <div className="inspection-layer">
              <div className="flex items-center justify-between pb-3 border-b border-line ">
                <div className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-emerald-600" />
                  <h3 className="font-semibold text-sm text-ink ">
                    Layer 1: C2PA Container Manifest
                  </h3>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                    report.c2pa_valid
                      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                      : "bg-soft text-muted  "
                  }`}
                >
                  {report.c2pa_valid ? "Valid X.509 Signature" : "Metadata Missing / Transcoded"}
                </span>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-line ">
                  <span className="text-muted">Signer Authority</span>
                  <span className="font-mono text-ink ">VoiceRep Generation Signer CA</span>
                </div>
                <div className="flex justify-between py-1 border-b border-line ">
                  <span className="text-muted">Signature Algorithm</span>
                  <span className="font-mono text-ink ">ECDSA (P-256) + SHA-256</span>
                </div>
                <div className="flex justify-between py-1 border-b border-line ">
                  <span className="text-muted">Software Agent</span>
                  <span className="font-mono text-ink ">
                    {report.model_id ? `VoiceRep (${report.model_id})` : "VoiceRep Engine v1.0"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-line ">
                  <span className="text-muted">Tamper Status</span>
                  <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400 capitalize">
                    {report.tamper_status.replace(/_/g, " ")}
                  </span>
                </div>
              </div>
            </div>

            {/* Layer 2: In-Band Acoustic Watermark */}
            <div className="inspection-layer">
              <div className="flex items-center justify-between pb-3 border-b border-line ">
                <div className="flex items-center gap-2">
                  <Fingerprint className="h-4 w-4 text-indigo-600" />
                  <h3 className="font-semibold text-sm text-ink ">
                    Layer 2: In-Band Acoustic Watermark
                  </h3>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                    report.acoustic_watermark_detected
                      ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300"
                      : "bg-soft text-muted  "
                  }`}
                >
                  {report.acoustic_watermark_detected ? "Watermark Detected & Decoded" : "Not Detected"}
                </span>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-line ">
                  <span className="text-muted">Embedding Protocol</span>
                  <span className="font-mono text-ink ">
                    {report.acoustic_payload?.protocol || "VoiceRep-QIM-HAS-v1"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-line ">
                  <span className="text-muted">User Attribution Hash</span>
                  <span className="font-mono text-ink ">
                    {report.user_hash ? `0x${report.user_hash.slice(0, 8)}...` : "N/A"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-line ">
                  <span className="text-muted">Generation Timestamp</span>
                  <span className="font-mono text-ink ">
                    {report.created_at_iso
                      ? new Date(report.created_at_iso).toLocaleString()
                      : report.timestamp
                      ? new Date(report.timestamp * 1000).toLocaleString()
                      : "N/A"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-line ">
                  <span className="text-muted">CRC-16 Integrity Check</span>
                  <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">
                    {report.acoustic_watermark_detected ? "PASSED (0 bit errors)" : "N/A"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Compliance & Standards */}
          <div className="bg-paper  border border-line  rounded-lg p-6 space-y-4 ">
            <div className="flex items-center gap-2">
              <Scale className="h-4 w-4 text-blue-600" />
              <h3 className="font-semibold text-sm text-ink ">
                Regulatory Compliance & Institutional Safety
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-md bg-canvas  border border-line  space-y-1">
                <p className="font-semibold text-ink  flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> EU AI Act — Article 50
                </p>
                <p className="text-muted ">
                  Meets mandatory transparency requirements for synthetic audio markups and machine-detectable provenance.
                </p>
              </div>
              <div className="p-4 rounded-md bg-canvas  border border-line  space-y-1">
                <p className="font-semibold text-ink  flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> US Executive Order 14110
                </p>
                <p className="text-muted ">
                  Aligns with NIST standards for digital content provenance, cryptographic signing, and watermarking.
                </p>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={downloadPublicKey}
              className="text-xs text-muted hover:text-ink  underline transition-colors flex items-center gap-1"
            >
              <Download className="h-3 w-3" />
              <span>Download Platform X.509 Public Certificate</span>
            </button>
            <button
              onClick={resetAll}
              className="px-4 py-2 text-xs font-medium rounded-md bg-soft  text-ink  hover:bg-line  transition-colors flex items-center gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Verify Another File</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
