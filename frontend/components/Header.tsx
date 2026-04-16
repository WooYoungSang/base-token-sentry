"use client";
import Link from "next/link";

export default function Header() {
  return (
    <header className="border-b border-gray-800 bg-gray-950">
      <div className="mx-auto max-w-7xl px-4 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-2xl">🛡️</span>
          <span className="font-bold text-lg text-white tracking-tight">
            Token<span className="text-blue-400">Sentry</span>
          </span>
        </Link>
        <nav className="flex gap-6 text-sm text-gray-400">
          <Link href="/analyze" className="hover:text-white transition-colors">Analyze</Link>
          <Link href="/tokens" className="hover:text-white transition-colors">Tokens</Link>
          <Link href="/watch" className="hover:text-white transition-colors">Watch</Link>
        </nav>
      </div>
    </header>
  );
}
