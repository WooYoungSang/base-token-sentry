import type { ContractAnalysis } from "@/lib/types";

interface FlagItem {
  key: keyof ContractAnalysis;
  label: string;
  severity: "critical" | "warning" | "info";
}

const FLAGS: FlagItem[] = [
  { key: "has_owner_mint", label: "Owner can mint tokens", severity: "critical" },
  { key: "has_hidden_mint", label: "Hidden mint function", severity: "critical" },
  { key: "has_owner_blacklist", label: "Owner can blacklist addresses", severity: "critical" },
  { key: "has_blacklist", label: "Blacklist functionality", severity: "critical" },
  { key: "is_proxy", label: "Upgradeable proxy (risk flag)", severity: "critical" },
  { key: "has_owner_pause", label: "Owner can pause transfers", severity: "warning" },
  { key: "has_fee_on_transfer", label: "Fee-on-transfer", severity: "warning" },
];

const SEVERITY_STYLES = {
  critical: "bg-red-900/30 border-red-700 text-red-300",
  warning: "bg-yellow-900/30 border-yellow-700 text-yellow-300",
  info: "bg-blue-900/30 border-blue-700 text-blue-300",
};

const SEVERITY_ICONS = { critical: "🚨", warning: "⚠️", info: "ℹ️" };

interface Props {
  contract: ContractAnalysis;
}

export default function ContractFlags({ contract }: Props) {
  const active = FLAGS.filter((f) => contract[f.key] === true);

  if (active.length === 0) {
    return (
      <div className="flex items-center gap-2 text-green-400 text-sm">
        <span>✅</span>
        <span>No critical contract flags detected</span>
        {contract.verified_source && (
          <span className="text-xs text-gray-500 ml-2">(verified source)</span>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {!contract.verified_source && (
        <div className="text-xs text-yellow-500 mb-3">
          ⚠️ Source not verified on Basescan — flags derived from bytecode only
        </div>
      )}
      {active.map((f) => (
        <div
          key={f.key}
          className={`flex items-center gap-2 text-sm border rounded px-3 py-2 ${SEVERITY_STYLES[f.severity]}`}
        >
          <span>{SEVERITY_ICONS[f.severity]}</span>
          <span>{f.label}</span>
        </div>
      ))}
    </div>
  );
}
