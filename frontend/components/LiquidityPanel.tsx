import type { LiquidityAnalysis } from "@/lib/types";

interface Props {
  liquidity: LiquidityAnalysis;
}

export default function LiquidityPanel({ liquidity }: Props) {
  const fmt = (v: number) =>
    v >= 1_000_000
      ? `$${(v / 1_000_000).toFixed(2)}M`
      : v >= 1_000
      ? `$${(v / 1_000).toFixed(1)}K`
      : `$${v.toFixed(0)}`;

  return (
    <div className="grid grid-cols-2 gap-3 text-sm">
      <div className="bg-gray-800 rounded p-3">
        <div className="text-gray-400 text-xs mb-1">Total Liquidity</div>
        <div
          className={`font-bold text-lg ${liquidity.low_liquidity ? "text-red-400" : "text-green-400"}`}
        >
          {fmt(liquidity.total_liquidity_usd)}
          {liquidity.low_liquidity && (
            <span className="text-xs text-red-400 ml-1">⚠️ low</span>
          )}
        </div>
      </div>
      <div className="bg-gray-800 rounded p-3">
        <div className="text-gray-400 text-xs mb-1">LP Lock Status</div>
        <div className={`font-bold text-lg ${liquidity.lp_locked ? "text-green-400" : "text-red-400"}`}>
          {liquidity.lp_locked ? "🔒 Locked" : "🔓 Unlocked"}
        </div>
      </div>
      <div className="bg-gray-800 rounded p-3">
        <div className="text-gray-400 text-xs mb-1">Liquidity / MCap</div>
        <div className="font-bold text-lg text-white">
          {(liquidity.liquidity_mcap_ratio * 100).toFixed(1)}%
        </div>
      </div>
      <div className="bg-gray-800 rounded p-3">
        <div className="text-gray-400 text-xs mb-1">Pool Count</div>
        <div className="font-bold text-lg text-white">{liquidity.pool_count}</div>
      </div>
    </div>
  );
}
