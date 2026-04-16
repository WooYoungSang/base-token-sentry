"use client";
import { useQuery } from "@tanstack/react-query";
import { getRecentTokens } from "@/lib/api";
import Link from "next/link";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function WatchPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["recent-tokens"],
    queryFn: () => getRecentTokens(50),
    refetchInterval: 15_000,
  });

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Token Feed</h1>
          <p className="text-gray-500 text-sm mt-1">
            New tokens detected on Base via Uniswap PairCreated events
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="text-center py-16 text-gray-500">
            <div className="text-3xl mb-3 animate-scan">📡</div>
            Loading feed...
          </div>
        ) : isError ? (
          <div className="text-center py-16 text-red-400">
            Failed to load token feed. Is the API running?
          </div>
        ) : !data || data.tokens.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <div className="text-3xl mb-3">📡</div>
            <div>No new tokens detected yet.</div>
            <div className="text-xs mt-2 text-gray-600">
              The watcher monitors new Uniswap pair deployments on Base.
            </div>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                <th className="text-left py-3 px-4">Token Address</th>
                <th className="text-left py-3 px-4">Detected</th>
                <th className="text-left py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {data.tokens.map((t) => (
                <tr
                  key={t.address}
                  className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
                >
                  <td className="py-3 px-4 font-mono text-gray-300 text-xs break-all">
                    {t.address}
                  </td>
                  <td className="py-3 px-4 text-gray-500 text-xs whitespace-nowrap">
                    {timeAgo(t.detected_at)}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <Link
                      href={`/analyze?address=${t.address}`}
                      className="text-blue-400 hover:text-blue-300 text-xs transition-colors"
                    >
                      Analyze →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex items-center gap-2 mt-4 text-xs text-gray-600">
        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        Auto-refreshing every 15 seconds
      </div>
    </div>
  );
}
