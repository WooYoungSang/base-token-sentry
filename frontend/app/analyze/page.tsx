"use client";
import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { analyzeToken } from "@/lib/api";
import type { Grade } from "@/lib/types";
import Link from "next/link";
import TokenSearch from "@/components/TokenSearch";

const GRADE_STYLES: Record<Grade, string> = {
  A: "text-green-400",
  B: "text-blue-400",
  C: "text-yellow-400",
  D: "text-orange-400",
  F: "text-red-500",
};

function AnalyzeContent() {
  const params = useSearchParams();
  const address = params.get("address") ?? "";

  const mutation = useMutation({
    mutationFn: analyzeToken,
  });

  useEffect(() => {
    if (address) mutation.mutate(address);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [address]);

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold text-white mb-8">Analyze Token</h1>
      <div className="mb-8">
        <TokenSearch />
      </div>

      {mutation.isPending && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
          <div className="text-4xl mb-4 animate-scan">🔍</div>
          <div className="text-gray-300 font-medium">Analyzing token...</div>
          <div className="text-gray-500 text-sm mt-2">
            Running contract analysis, holder checks, liquidity verification, and honeypot simulation
          </div>
          <div className="mt-4 text-xs text-gray-600 font-mono break-all">{address}</div>
        </div>
      )}

      {mutation.isError && (
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-6">
          <div className="text-red-400 font-semibold mb-2">Analysis Failed</div>
          <div className="text-red-300 text-sm">
            {mutation.error instanceof Error ? mutation.error.message : "Unknown error"}
          </div>
          <div className="text-gray-500 text-xs mt-2">
            Make sure the address is a valid ERC-20 token contract on Base.
          </div>
        </div>
      )}

      {mutation.isSuccess && mutation.data && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <div className="text-xs text-gray-500 font-mono break-all mb-4">{mutation.data.address}</div>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className={`text-5xl font-black ${GRADE_STYLES[mutation.data.grade]}`}>
                  {mutation.data.score}
                </div>
                <div className="text-gray-500 text-xs mt-1">Safety Score</div>
              </div>
              <div className="text-center">
                <div className={`text-4xl font-black ${GRADE_STYLES[mutation.data.grade]}`}>
                  {mutation.data.grade}
                </div>
                <div className="text-gray-500 text-xs mt-1">Grade</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${mutation.data.is_honeypot ? "text-red-400" : "text-green-400"}`}>
                  {mutation.data.is_honeypot ? "🍯 YES" : "✅ NO"}
                </div>
                <div className="text-gray-500 text-xs mt-1">Honeypot</div>
              </div>
            </div>
          </div>

          <Link
            href={`/tokens/${mutation.data.address}`}
            className="block w-full text-center bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-lg transition-colors"
          >
            View Full Analysis →
          </Link>

          <p className="text-center text-xs text-gray-600">{mutation.data.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
