"use client";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { HolderAnalysis } from "@/lib/types";

const COLORS = ["#ef4444", "#f97316", "#eab308", "#3b82f6", "#8b5cf6"];

interface Props {
  holder: HolderAnalysis;
}

export default function HolderDistribution({ holder }: Props) {
  const top10 = holder.top10_concentration;
  const rest = Math.max(0, 1 - top10);

  const data = [
    { name: "Top Holder", value: Math.round(holder.whale_percentage * 100) },
    {
      name: "Top 2-10 Holders",
      value: Math.round((top10 - holder.whale_percentage) * 100),
    },
    { name: "Rest", value: Math.round(rest * 100) },
  ].filter((d) => d.value > 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-gray-800 rounded p-3">
          <div className="text-gray-400 text-xs mb-1">Top 10 Concentration</div>
          <div
            className={`font-bold text-lg ${top10 > 0.8 ? "text-red-400" : top10 > 0.5 ? "text-yellow-400" : "text-green-400"}`}
          >
            {(top10 * 100).toFixed(1)}%
          </div>
        </div>
        <div className="bg-gray-800 rounded p-3">
          <div className="text-gray-400 text-xs mb-1">Largest Holder</div>
          <div
            className={`font-bold text-lg ${holder.single_holder_dominant ? "text-red-400" : "text-green-400"}`}
          >
            {(holder.whale_percentage * 100).toFixed(1)}%
            {holder.single_holder_dominant && (
              <span className="text-xs text-red-400 ml-1">⚠️ dominant</span>
            )}
          </div>
        </div>
        <div className="bg-gray-800 rounded p-3">
          <div className="text-gray-400 text-xs mb-1">Total Holders</div>
          <div className="font-bold text-lg text-white">{holder.total_holders.toLocaleString()}</div>
        </div>
        <div className="bg-gray-800 rounded p-3">
          <div className="text-gray-400 text-xs mb-1">Creator Holding</div>
          <div
            className={`font-bold text-lg ${holder.creator_dominant ? "text-red-400" : "text-green-400"}`}
          >
            {(holder.creator_holding * 100).toFixed(1)}%
          </div>
        </div>
      </div>
      {data.length > 0 && (
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(v: any) => `${v}%`}
              contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 8 }}
              labelStyle={{ color: "#9ca3af" }}
            />
            <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
