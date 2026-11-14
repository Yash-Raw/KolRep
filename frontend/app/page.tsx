import Link from "next/link";
import { ArrowRight, ArrowUpRight, AudioLines } from "lucide-react";
import { SignalArt } from "@/components/ui/SignalArt";

export default function LandingPage() {
  return <div className="landing">
    <section className="broadcast-hero">
      <div className="broadcast-kicker"><p className="eyebrow">INDEPENDENT VOICE PRODUCTION</p><p className="eyebrow">RECORDED BY YOU. REIMAGINED BY VOICEREP.</p></div>
      <h1 className="headline-enter">A voice of<br /><span>your own.</span></h1>
      <div className="broadcast-intro"><p>Your voice has a character. Keep it.<br />Create expressive narration from an authorized recording, in a studio that runs on your own device.</p><div className="flex flex-wrap gap-3"><Link href="/dashboard" className="btn btn-primary">Enter the workspace <ArrowUpRight size={17} /></Link><Link href="/voices" className="btn btn-secondary">Explore your voices <ArrowRight size={16} /></Link></div></div>
      <div className="broadcast-art"><span className="broadcast-art-label">FIG. 01 / THE HUMAN SIGNAL</span><span className="broadcast-art-number" aria-hidden="true">VR—01</span><SignalArt /><div className="broadcast-art-bottom"><span>ORIGINAL VOICE. NEW POSSIBILITIES.</span><span>100% LOCAL</span></div></div>
    </section>
    <section className="broadcast-process"><div className="broadcast-section-header"><p className="eyebrow">A SIMPLE PRODUCTION PROCESS<br />01 — 03</p><h2>From a recording.<br />To something worth hearing.</h2></div><div className="broadcast-steps">
      <article className="broadcast-step"><p className="eyebrow">01 / THE SOURCE</p><h3>Start with your voice.</h3><p>Record or upload an authorized voice sample. Create a profile you can return to, again and again.</p><Link href="/voices" className="text-link">Build your voice library <ArrowUpRight size={16} /></Link></article>
      <article className="broadcast-step"><p className="eyebrow">02 / THE SESSION</p><h3>Give the script a life.</h3><p>Bring your words into the studio. Adjust the delivery, generate your narration, and listen back.</p><Link href="/studio" className="text-link">Take it to the studio <ArrowUpRight size={16} /></Link></article>
      <article className="broadcast-step"><p className="eyebrow">03 / THE RECORD</p><h3>Keep the story clear.</h3><p>Inspect audio for signed provenance and acoustic watermarks using the built-in verification tools.</p><Link href="/verify" className="text-link">Inspect an audio file <ArrowUpRight size={16} /></Link></article>
    </div></section>
    <footer className="broadcast-footer"><div className="broadcast-footer-top"><Link href="/" className="brand"><AudioLines size={28} />VoiceRep</Link><div className="broadcast-footer-links"><Link href="/dashboard">Workspace</Link><Link href="/studio">Voice studio</Link><Link href="/history">Recording history</Link><Link href="/verify">Verify audio</Link></div></div><div className="broadcast-footer-bottom"><span>YOUR DEVICE. YOUR VOICE.</span><span>© {new Date().getFullYear()} VOICEREP</span></div></footer>
  </div>;
}
