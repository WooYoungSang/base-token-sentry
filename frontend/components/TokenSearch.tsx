"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function TokenSearch() {
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const isValidAddress = (addr: string) => /^0x[0-9a-fA-F]{40}$/.test(addr);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = address.trim();
    if (!isValidAddress(trimmed)) {
      setError("Please enter a valid EVM address (0x...)");
      return;
    }
    setError("");
    router.push(`/analyze?address=${trimmed}`);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="flex gap-2">
        <input
          type="text"
          value={address}
          onChange={(e) => { setAddress(e.target.value); setError(""); }}
          placeholder="Enter token contract address (0x...)"
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 text-sm"
          spellCheck={false}
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-3 rounded-lg transition-colors text-sm"
        >
          Analyze
        </button>
      </div>
      {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
    </form>
  );
}
