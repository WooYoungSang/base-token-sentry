import { DISCLAIMER } from "@/lib/types";

export default function Footer() {
  return (
    <footer className="border-t border-gray-800 bg-gray-950 mt-16">
      <div className="mx-auto max-w-7xl px-4 py-6 text-center text-xs text-gray-500">
        <p className="mb-1">⚠️ {DISCLAIMER}</p>
        <p>TokenSentry — Base Network Security Scanner</p>
      </div>
    </footer>
  );
}
