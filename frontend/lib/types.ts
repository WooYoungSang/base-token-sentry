export const DISCLAIMER = "Safety scores are informational only, not investment advice.";

export type Grade = "A" | "B" | "C" | "D" | "F";

export interface ContractAnalysis {
  has_hidden_mint: boolean;
  has_blacklist: boolean;
  has_fee_on_transfer: boolean;
  is_proxy: boolean;
  has_owner_pause: boolean;
  has_owner_blacklist: boolean;
  has_owner_mint: boolean;
  risk_flags: string[];
  verified_source: boolean;
  critical_flag_count: number;
}

export interface HolderAnalysis {
  top10_concentration: number;
  whale_percentage: number;
  creator_holding: number;
  single_holder_dominant: boolean;
  creator_dominant: boolean;
  total_holders: number;
}

export interface LiquidityAnalysis {
  total_liquidity_usd: number;
  liquidity_mcap_ratio: number;
  lp_locked: boolean;
  low_liquidity: boolean;
  pool_count: number;
}

export interface HoneypotResult {
  is_honeypot: boolean;
  buy_tax: number;
  sell_tax: number;
  buy_blocked: boolean;
  sell_blocked: boolean;
  details: string;
}

export interface TokenDetail {
  address: string;
  score: number;
  grade: Grade;
  penalties: string[];
  contract: ContractAnalysis | null;
  holder: HolderAnalysis | null;
  liquidity: LiquidityAnalysis | null;
  honeypot: HoneypotResult | null;
  analyzed_at: string | null;
  disclaimer: string;
}

export interface SafetyScore {
  address: string;
  score: number;
  grade: Grade;
  penalties: string[];
  disclaimer: string;
}

export interface AnalyzeResponse {
  address: string;
  score: number;
  grade: Grade;
  is_honeypot: boolean;
  disclaimer: string;
}

export interface TokenListItem {
  address: string;
  score: number;
  grade: Grade;
  is_honeypot: boolean;
  analyzed_at: string | null;
}

export interface TokenListResponse {
  tokens: TokenListItem[];
  total: number;
  page: number;
  page_size: number;
  disclaimer: string;
}

export interface RecentToken {
  address: string;
  detected_at: string;
}

export interface RecentTokensResponse {
  tokens: RecentToken[];
  count: number;
}
