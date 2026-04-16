import type { HoneypotResult as HoneypotResultType } from "@/lib/types";

interface Props {
  honeypot: HoneypotResultType;
}

export default function HoneypotResult({ honeypot }: Props) {
  return (
    <div className="space-y-4">
      <div
        className={`flex items-center gap-3 p-4 rounded-lg border text-lg font-bold ${
          honeypot.is_honeypot
            ? "bg-red-900/30 border-red-700 text-red-300"
            : "bg-green-900/30 border-green-700 text-green-300"
        }`}
      >
        <span className="text-2xl">{honeypot.is_honeypot ? "🍯" : "✅"}</span>
        <div>
          {honeypot.is_honeypot ? "HONEYPOT DETECTED" : "No Honeypot Detected"}
          {honeypot.details && (
            <div className="text-sm font-normal mt-1 opacity-80">{honeypot.details}</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-gray-800 rounded p-3">
          <div className="text-gray-400 text-xs mb-1">Buy Tax</div>
          <div
            className={`font-bold text-lg ${honeypot.buy_blocked ? "text-red-400" : honeypot.buy_tax > 0.1 ? "text-orange-400" : "text-green-400"}`}
          >
            {honeypot.buy_blocked ? "BLOCKED" : `${(honeypot.buy_tax * 100).toFixed(1)}%`}
          </div>
        </div>
        <div className="bg-gray-800 rounded p-3">
          <div className="text-gray-400 text-xs mb-1">Sell Tax</div>
          <div
            className={`font-bold text-lg ${honeypot.sell_blocked ? "text-red-400" : honeypot.sell_tax > 0.1 ? "text-red-400" : "text-green-400"}`}
          >
            {honeypot.sell_blocked ? "BLOCKED" : `${(honeypot.sell_tax * 100).toFixed(1)}%`}
          </div>
        </div>
      </div>
    </div>
  );
}
