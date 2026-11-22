import Link from "next/link";
import { ArrowRight, ArrowUpRight, AudioLines } from "lucide-react";
import { SignalArt } from "@/components/ui/SignalArt";

export default function LandingPage() {
  return (
    <div className="landing">
      {/* 3.B Hero Section */}
      <section className="broadcast-hero">
        <div className="broadcast-kicker">
          <p className="eyebrow">INDEPENDENT VOICE PRODUCTION</p>
          <p className="eyebrow">RECORDED BY YOU. REIMAGINED BY KOLREP.</p>
        </div>
        <h1 className="headline-enter">
          A voice of<br />
          <span>your own.</span>
        </h1>
        <div className="broadcast-intro">
          <p>
            Your voice has a character. Keep it.<br />
            Create expressive narration from an authorized recording, in a studio that runs entirely on your own device.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/dashboard" className="btn btn-primary">
              Enter the workspace <ArrowUpRight size={17} />
            </Link>
            <Link href="/voices" className="btn btn-secondary">
              Explore your voices <ArrowRight size={16} />
            </Link>
          </div>
        </div>
        <div className="broadcast-art" role="img" aria-label="Analog signal monitor">
          <span className="broadcast-art-label">FIG. 01 / THE HUMAN SIGNAL</span>
          <span className="broadcast-art-number" aria-hidden="true">
            KR—01
          </span>
          <SignalArt />
          <div className="broadcast-art-bottom">
            <span>ORIGINAL VOICE. NEW POSSIBILITIES.</span>
            <span>100% LOCAL</span>
          </div>
        </div>
      </section>

      {/* 3.C The Production Process */}
      <section className="broadcast-process">
        <div className="broadcast-section-header">
          <p className="eyebrow">
            A SIMPLE PRODUCTION PROCESS<br />
            01 — 03
          </p>
          <h2>
            From a recording.<br />
            To something worth hearing.
          </h2>
        </div>
        <div className="broadcast-steps">
          <article className="broadcast-step">
            <p className="eyebrow">01 / THE SOURCE</p>
            <h3>Start with your voice.</h3>
            <p>
              Record or upload an authorized voice sample. KolRep builds an acoustic profile locally in seconds without sending your biometric data to any cloud.
            </p>
            <Link href="/voices" className="text-link">
              Build your voice library <ArrowUpRight size={16} />
            </Link>
          </article>
          <article className="broadcast-step">
            <p className="eyebrow">02 / THE SESSION</p>
            <h3>Give the script a life.</h3>
            <p>
              Bring your words into the studio canvas. Fine-tune stability, pace, and style exaggeration with tactile faders, then synthesize studio-grade takes on-device.
            </p>
            <Link href="/studio" className="text-link">
              Take it to the studio <ArrowUpRight size={16} />
            </Link>
          </article>
          <article className="broadcast-step">
            <p className="eyebrow">03 / THE RECORD</p>
            <h3>Keep the story clear.</h3>
            <p>
              Every take is embedded with an imperceptible acoustic watermark and signed with dual-layer C2PA cryptographic provenance to certify ethical authorization.
            </p>
            <Link href="/verify" className="text-link">
              Inspect an audio file <ArrowUpRight size={16} />
            </Link>
          </article>
        </div>
      </section>

      {/* 3.D Core Pillars / Architecture Highlights Strip */}
      <section className="broadcast-metrics-section" style={{ padding: "0 clamp(24px, 5vw, 80px) 90px", maxWidth: "1600px", margin: "auto" }}>
        <div className="broadcast-kicker" style={{ marginBottom: "28px" }}>
          <p className="eyebrow">CORE ARCHITECTURE / 01 — 04</p>
          <p className="eyebrow">PHYSICAL INSTRUMENT TELEMETRY</p>
        </div>
        <div className="metrics-strip">
          <div className="metric">
            <p className="eyebrow">01 / LOCAL INFERENCE</p>
            <h3 style={{ fontSize: "20px", fontWeight: 500, margin: "14px 0 8px", letterSpacing: "-.04em" }}>
              Zero Cloud Latency
            </h3>
            <p className="metric-note" style={{ fontSize: "12px", lineHeight: 1.6 }}>
              Runs locally on PyTorch/F5-TTS with Apple Silicon (MPS) acceleration.
            </p>
          </div>
          <div className="metric">
            <p className="eyebrow">02 / COMPLETE PRIVACY</p>
            <h3 style={{ fontSize: "20px", fontWeight: 500, margin: "14px 0 8px", letterSpacing: "-.04em" }}>
              100% Air-Gapped
            </h3>
            <p className="metric-note" style={{ fontSize: "12px", lineHeight: 1.6 }}>
              Zero telemetries, no third-party APIs, no biometric cloud storage.
            </p>
          </div>
          <div className="metric">
            <p className="eyebrow">03 / C2PA AUTHENTICITY</p>
            <h3 style={{ fontSize: "20px", fontWeight: 500, margin: "14px 0 8px", letterSpacing: "-.04em" }}>
              Dual-Layer Provenance
            </h3>
            <p className="metric-note" style={{ fontSize: "12px", lineHeight: 1.6 }}>
              Cryptographically signed metadata manifests + acoustic watermarks.
            </p>
          </div>
          <div className="metric">
            <p className="eyebrow">04 / HIGH FIDELITY</p>
            <h3 style={{ fontSize: "20px", fontWeight: 500, margin: "14px 0 8px", letterSpacing: "-.04em" }}>
              Studio Quality
            </h3>
            <p className="metric-note" style={{ fontSize: "12px", lineHeight: 1.6 }}>
              36-step neural diffusion synthesizer for natural cadence and expressive nuance.
            </p>
          </div>
        </div>
      </section>

      {/* 3.E Broadcast Footer */}
      <footer className="broadcast-footer">
        <div className="broadcast-footer-top">
          <Link href="/" className="brand">
            <span className="brand-symbol">
              <AudioLines size={22} />
            </span>
            KolRep
          </Link>
          <div className="broadcast-footer-links">
            <Link href="/dashboard">Workspace</Link>
            <Link href="/studio">Voice studio</Link>
            <Link href="/history">Recording archive</Link>
            <Link href="/verify">Audio verification</Link>
          </div>
        </div>
        <div className="broadcast-footer-bottom">
          <span>YOUR DEVICE. YOUR VOICE.</span>
          <span>© {new Date().getFullYear()} KOLREP — LOCAL VOICE REPLICATION</span>
        </div>
      </footer>
    </div>
  );
}
