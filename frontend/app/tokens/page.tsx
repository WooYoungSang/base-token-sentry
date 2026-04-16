"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listTokens } from "@/lib/api";
import TokenTable from "@/components/TokenTable";
import type { Grade } from "@/lib/types";

const GRADES: Grade[] = ["A", "B", "C", "D", "F"];

export default function TokensPage() {
  const [page, setPage] = useState(1);
  const [grade, setGrade] = useState<string>("");
  const [honeypotFilter, setHoneypotFilter] = useState<boolean | undefined>(undefined);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["tokens", page, grade, honeypotFilter],
    queryFn: () => listTokens({ page, page_size: 20, grade: grade || undefined, is_honeypot: honeypotFilter }),
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="mx-auto max-w-7xl px-4 py-12">
      <h1 className="text-2xl font-bold text-white mb-6">Analyzed Tokens</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={grade}
          onChange={(e) => { setGrade(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        >
          <option value="">All Grades</option>
          {GRADES.map((g) => <option key={g} value={g}>Grade {g}</option>)}
        </select>

        <select
          value={honeypotFilter === undefined ? "" : String(honeypotFilter)}
          onChange={(e) => {
            setHoneypotFilter(e.target.value === "" ? undefined : e.target.value === "true");
            setPage(1);
          }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        >
          <option value="">All Tokens</option>
          <option value="false">Safe Only</option>
          <option value="true">Honeypots Only</option>
        </select>

        {(grade || honeypotFilter !== undefined) && (
          <button
            onClick={() => { setGrade(""); setHoneypotFilter(undefined); setPage(1); }}
            className="text-gray-400 hover:text-white text-sm transition-colors"
          >
            Clear filters ✕
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="text-center py-16 text-gray-500">Loading tokens...</div>
        ) : isError ? (
          <div className="text-center py-16 text-red-400">Failed to load tokens. Is the API running?</div>
        ) : (
          <TokenTable tokens={data?.tokens ?? []} />
        )}
      </div>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-800 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-700 transition-colors"
          >
            ← Prev
          </button>
          <span className="px-4 py-2 text-gray-400 text-sm">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 bg-gray-800 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-700 transition-colors"
          >
            Next →
          </button>
        </div>
      )}

      {data && (
        <p className="text-center text-xs text-gray-600 mt-4">{data.disclaimer}</p>
      )}
    </div>
  );
}
