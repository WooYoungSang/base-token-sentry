"use client";
import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { getToken } from "@/lib/api";
import SafetyScoreGauge from "@/components/SafetyScoreGauge";
import ContractFlags from "@/components/ContractFlags";
import HolderDistribution from "@/components/HolderDistribution";
import LiquidityPanel from "@/components/LiquidityPanel";
import HoneypotResultComponent from "@/components/HoneypotResult";
import type { Grade } from "@/lib/types";

interface Props {
  params: Promise<{ address: string }>;
}

export default function TokenDetailPage({ params }: Props) {
  const { address } = use(params);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["token", address],
    queryFn: () => getToken(address),
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12 text-center">
        <div className="text-4xl animate-scan mb-4">🔍</div>
        <p className="text-gray-400">Loading analysis...</p>
      </div>
    );
  }

  if (isError || !data) {
    const msg = error instanceof Error ? error.message : "Token not found";
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-6">
          <div className="text-red-400 font-semibold mb-2">Token Not Found</div>
          <div className="text-red-300 text-sm">{msg}</div>
          <a href={`/analyze?address=${address}`} className="mt-4 inline-block text-blue-400 hover:text-blue-300 text-sm">
            Run analysis →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <div className="mb-8">
        <div className="text-xs text-gray-500 font-mono mb-2 break-all">{data.address}</div>
        <h1 className="text-2xl font-bold text-white">Token Safety Report</h1>
        {data.analyzed_at && (
          <div className="text-xs text-gray-600 mt-1">
            Analyzed: {new Date(data.analyzed_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Score */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6 flex flex-col items-center gap-4">
        <SafetyScoreGauge score={data.score} grade={data.grade as Grade} />
        {data.penalties.length > 0 && (
          <div className="w-full max-w-md">
            <div className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Score Penalties</div>
            {data.penalties.map((p, i) => (
              <div key={i} className="text-xs text-red-400 font-mono mb-1">— {p}</div>
            ))}
          </div>
        )}
      </div>

      {/* Analysis sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Contract */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">
            📜 Contract Analysis
          </h2>
          {data.contract ? (
            <ContractFlags contract={data.contract} />
          ) : (
            <p className="text-gray-500 text-sm">No contract data available</p>
          )}
        </section>

        {/* Honeypot */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">
            🍯 Honeypot Detection
          </h2>
          {data.honeypot ? (
            <HoneypotResultComponent honeypot={data.honeypot} />
          ) : (
            <p className="text-gray-500 text-sm">No honeypot data available</p>
          )}
        </section>

        {/* Holders */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">
            👥 Holder Distribution
          </h2>
          {data.holder ? (
            <HolderDistribution holder={data.holder} />
          ) : (
            <p className="text-gray-500 text-sm">No holder data available</p>
          )}
        </section>

        {/* Liquidity */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">
            💧 Liquidity
          </h2>
          {data.liquidity ? (
            <LiquidityPanel liquidity={data.liquidity} />
          ) : (
            <p className="text-gray-500 text-sm">No liquidity data available</p>
          )}
        </section>
      </div>

      <p className="text-center text-xs text-gray-600 mt-8">{data.disclaimer}</p>
    </div>
  );
}
