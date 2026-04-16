import Link from "next/link";
import TokenSearch from "@/components/TokenSearch";

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-20">
      {/* Hero */}
      <div className="text-center mb-16">
        <div className="text-6xl mb-4">🛡️</div>
        <h1 className="text-4xl md:text-5xl font-black text-white mb-4 tracking-tight">
          Token<span className="text-blue-400">Sentry</span>
        </h1>
        <p className="text-gray-400 text-lg mb-2 max-w-xl mx-auto">
          Real-time token safety analysis and honeypot detection for the Base network.
        </p>
        <p className="text-gray-600 text-sm mb-10">
          Contract analysis · Holder distribution · Liquidity checks · Honeypot simulation
        </p>
        <div className="flex justify-center">
          <TokenSearch />
        </div>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
        {[
          { icon: "📜", title: "Contract Analysis", desc: "Detects mint, blacklist, proxy, and pause functions" },
          { icon: "👥", title: "Holder Distribution", desc: "Identifies whale dominance and creator holding" },
          { icon: "💧", title: "Liquidity Check", desc: "Verifies DEX liquidity depth and LP lock status" },
          { icon: "🍯", title: "Honeypot Detection", desc: "Simulates buy/sell to detect sell restrictions" },
        ].map((f) => (
          <div key={f.title} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="text-2xl mb-2">{f.icon}</div>
            <div className="font-semibold text-white text-sm mb-1">{f.title}</div>
            <div className="text-gray-500 text-xs">{f.desc}</div>
          </div>
        ))}
      </div>

      {/* CTAs */}
      <div className="flex flex-wrap justify-center gap-4">
        <Link
          href="/tokens"
          className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-medium transition-colors text-sm"
        >
          Browse Analyzed Tokens →
        </Link>
        <Link
          href="/watch"
          className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-6 py-3 rounded-lg font-medium transition-colors text-sm"
        >
          Live Token Feed →
        </Link>
      </div>
    </div>
  );
}
