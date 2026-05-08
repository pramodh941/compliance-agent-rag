from collections import Counter
from datetime import datetime, timezone


def build_report(scan_results):
    violations = []
    risk_counts = Counter()

    for result in scan_results:
        analysis = result.get("analysis", {})
        risk_level = "UNKNOWN"

        if isinstance(analysis, dict):
            risk_level = analysis.get("risk_level", "UNKNOWN")
            for violation in analysis.get("violations", []):
                violations.append(
                    {
                        "email_id": result.get("email_id"),
                        "policy": violation.get("policy"),
                        "reason": violation.get("reason"),
                    }
                )
        elif analysis:
            risk_level = "REVIEW"
            violations.append(
                {
                    "email_id": result.get("email_id"),
                    "policy": "Review Required",
                    "reason": str(analysis)[:500],
                }
            )

        risk_counts[risk_level] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "email_count": len(scan_results),
        "risk_summary": dict(risk_counts),
        "violation_count": len(violations),
        "violations": violations,
    }
