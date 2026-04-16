"use client";
import type { Grade } from "@/lib/types";

const GRADE_COLORS: Record<Grade, string> = {
  A: "text-green-400 border-green-400",
  B: "text-blue-400 border-blue-400",
  C: "text-yellow-400 border-yellow-400",
  D: "text-orange-400 border-orange-400",
  F: "text-red-500 border-red-500",
};

const SCORE_BAR_COLORS: Record<Grade, string> = {
  A: "bg-green-500",
  B: "bg-blue-500",
  C: "bg-yellow-500",
  D: "bg-orange-500",
  F: "bg-red-600",
};

interface Props {
  score: number;
  grade: Grade;
}

export default function SafetyScoreGauge({ score, grade }: Props) {
  const colors = GRADE_COLORS[grade];
  const barColor = SCORE_BAR_COLORS[grade];

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`w-24 h-24 rounded-full border-4 flex flex-col items-center justify-center ${colors}`}
      >
        <span className="text-3xl font-bold">{score}</span>
        <span className="text-xs opacity-70">/ 100</span>
      </div>
      <div className={`text-2xl font-black px-4 py-1 rounded border-2 ${colors}`}>
        Grade {grade}
      </div>
      <div className="w-48 bg-gray-700 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${barColor}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
