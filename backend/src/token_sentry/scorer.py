"""Safety scorer - combines all signals into a 0-100 safety score."""

from .models import ContractAnalysis, HolderAnalysis, HoneypotResult, LiquidityAnalysis, SafetyScore

# Penalty weights
PENALTY_CONTRACT_FLAG = 20      # per critical contract flag
PENALTY_HONEYPOT = 50           # if honeypot detected
PENALTY_HIGH_HOLDER_CONC = 20   # top holder >50%
PENALTY_LOW_LIQUIDITY = 20      # low liquidity
PENALTY_UNLOCKED_LP = 10        # LP tokens not locked

BASE_SCORE = 100


class SafetyScorer:
    def score(
        self,
        address: str,
        contract: ContractAnalysis,
        holder: HolderAnalysis,
        liquidity: LiquidityAnalysis,
        honeypot: HoneypotResult,
    ) -> SafetyScore:
        score = BASE_SCORE
        penalties: list[str] = []

        # Honeypot: largest single penalty
        if honeypot.is_honeypot:
            score -= PENALTY_HONEYPOT
            penalties.append(f"honeypot_detected (-{PENALTY_HONEYPOT})")

        # Contract flags: -20 per critical flag
        flag_count = contract.critical_flag_count
        if flag_count > 0:
            deduction = min(flag_count * PENALTY_CONTRACT_FLAG, 60)
            score -= deduction
            penalties.append(f"contract_flags:{','.join(contract.risk_flags)} (-{deduction})")

        # Holder concentration
        if holder.single_holder_dominant:
            score -= PENALTY_HIGH_HOLDER_CONC
            penalties.append(f"single_holder_dominant (-{PENALTY_HIGH_HOLDER_CONC})")

        # Liquidity
        if liquidity.low_liquidity:
            score -= PENALTY_LOW_LIQUIDITY
            penalties.append(f"low_liquidity (-{PENALTY_LOW_LIQUIDITY})")
        if not liquidity.lp_locked:
            score -= PENALTY_UNLOCKED_LP
            penalties.append(f"lp_not_locked (-{PENALTY_UNLOCKED_LP})")

        score = max(0, min(100, score))

        result = SafetyScore(
            address=address,
            score=score,
            penalties=penalties,
            contract=contract,
            holder=holder,
            liquidity=liquidity,
            honeypot=honeypot,
        )
        result.grade = result._compute_grade()
        return result
