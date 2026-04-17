"""Safety scorer - combines all signals into a 0-100 safety score."""

import logging

from .models import ContractAnalysis, HolderAnalysis, HoneypotResult, LiquidityAnalysis, SafetyScore

logger = logging.getLogger(__name__)

# Penalty weights
PENALTY_CONTRACT_FLAG = 20      # per critical contract flag
PENALTY_HONEYPOT = 50           # if honeypot detected
PENALTY_HIGH_HOLDER_CONC = 20   # top holder >50%
PENALTY_LOW_LIQUIDITY = 20      # low liquidity
PENALTY_UNLOCKED_LP = 10        # LP tokens not locked

BASE_SCORE = 100


class SafetyScorer:
    def __init__(self) -> None:
        self._ml_scorer = None
        try:
            from .ml.ml_scorer import MLScorer
            scorer = MLScorer()
            if scorer.available:
                self._ml_scorer = scorer
                logger.info("ML scorer loaded successfully")
        except Exception:
            logger.debug("ML scorer not available, using rule-based only")

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
        rule_based_score = score

        # Try ML prediction
        scoring_method = "rule_based"
        ml_confidence: float | None = None

        if self._ml_scorer is not None:
            try:
                ml_score, ml_grade, confidence = self._ml_scorer.predict_from_analyses(
                    contract, holder, liquidity, honeypot,
                )
                if confidence < 0.3:
                    logger.info(
                        "ML confidence too low (%.3f), falling back to rule-based scoring",
                        confidence,
                    )
                elif 0 <= ml_score <= 100:
                    ml_rounded = int(round(ml_score))
                    # Guard against ML drifting too far from rule-based:
                    # if scores disagree by more than 20 points, blend them
                    diff = abs(ml_rounded - rule_based_score)
                    if diff > 20:
                        score = int(round(0.4 * ml_rounded + 0.6 * rule_based_score))
                        logger.info(
                            "ML/rule-based divergence (%d vs %d), blending to %d",
                            ml_rounded, rule_based_score, score,
                        )
                    else:
                        score = ml_rounded
                    scoring_method = "ml"
                    ml_confidence = round(confidence, 3)
                    logger.debug("ML score=%.1f grade=%s conf=%.3f", ml_score, ml_grade, confidence)
            except Exception:
                logger.debug("ML prediction failed, using rule-based fallback")

        # Honeypot safety guard: honeypot tokens should NEVER score above C grade.
        # Use the lower of ML score, rule-based score, and the 45 cap.
        if honeypot.is_honeypot:
            capped = min(score, 45, rule_based_score)
            if capped != score:
                logger.info("Honeypot safety guard: clamping score from %d to %d", score, capped)
            score = capped

        result = SafetyScore(
            address=address,
            score=score,
            penalties=penalties,
            contract=contract,
            holder=holder,
            liquidity=liquidity,
            honeypot=honeypot,
            scoring_method=scoring_method,
            ml_confidence=ml_confidence,
        )
        result.grade = result._compute_grade()
        return result
