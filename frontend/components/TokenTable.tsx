"use client";
import Link from "next/link";
import type { Grade, TokenListItem } from "@/lib/types";

const GRADE_BADGE: Record<Grade, string> = {
  A: "bg-green-900 text-green-300 border-green-700",
  B: "bg-blue-900 text-blue-300 border-blue-700",
  C: "bg-yellow-900 text-yellow-300 border-yellow-700",
  D: "bg-orange-900 text-orange-300 border-orange-700",
  F: "bg-red-900 text-red-300 border-red-700",
};

interface Props {
  tokens: TokenListItem[];
}

function shortAddr(addr: string) {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function TokenTable({ tokens }: Props) {
  if (tokens.length === 0) {
    return <div className="text-gray-500 text-center py-12">No tokens found.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
            <th className="text-left py-3 px-4">Address</th>
            <th className="text-left py-3 px-4">Score</th>
            <th className="text-left py-3 px-4">Grade</th>
            <th className="text-left py-3 px-4">Honeypot</th>
            <th className="text-left py-3 px-4">Analyzed</th>
            <th className="text-left py-3 px-4"></th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((t) => (
            <tr
              key={t.address}
              className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
            >
              <td className="py-3 px-4 font-mono text-gray-300">{shortAddr(t.address)}</td>
              <td className="py-3 px-4 font-bold text-white">{t.score}</td>
              <td className="py-3 px-4">
                <span
                  className={`text-xs font-bold border rounded px-2 py-0.5 ${GRADE_BADGE[t.grade]}`}
                >
                  {t.grade}
                </span>
              </td>
              <td className="py-3 px-4">
                {t.is_honeypot ? (
                  <span className="text-red-400 text-xs">🍯 YES</span>
                ) : (
                  <span className="text-green-400 text-xs">✅ NO</span>
                )}
              </td>
              <td className="py-3 px-4 text-gray-500 text-xs">{timeAgo(t.analyzed_at)}</td>
              <td className="py-3 px-4">
                <Link
                  href={`/tokens/${t.address}`}
                  className="text-blue-400 hover:text-blue-300 text-xs transition-colors"
                >
                  Details →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
