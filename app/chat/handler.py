from app.verification.comparator import compare

def compose_reply(message: str, evidence: dict,
                  verification, quality_fail: bool, quality_reason: str | None) -> str:
    if quality_fail:
        return (
            "I couldn't read your file clearly "
            f"({quality_reason}). Could you re-upload a sharper, "
            "well-lit photo or the original PDF?"
        )

    if verification.status == "conflict":
        return (
            "I found a mismatch between your message and the file:\n- "
            + "\n- ".join(verification.conflicts)
            + "\n\nCould you confirm which is correct, or upload the "
              "matching document?"
        )

    if verification.status == "insufficient_evidence":
        return (
            "I don't see enough information in the file to verify your "
            "request. Could you share the order ID, amount, or date shown on "
            "your document?"
        )

    lines = ["Thanks — here's what I verified from your document:"]
    for k, v in verification.matched_fields.items():
        lines.append(f"- {k}: {v}")
    if verification.notes:
        lines.append("Notes: " + "; ".join(verification.notes))
    if not verification.matched_fields:
        lines.append(
            "I couldn't extract any matching fields, but no contradiction "
            "was found. Can you clarify what you need help with?")
    return "\n".join(lines)

def decide(message: str, evidence: dict):
    verification = compare(message, evidence)
    quality_fail = not evidence.get("quality_ok", True)
    reason = evidence.get("quality_reason")
    reply = compose_reply(message, evidence, verification, quality_fail, reason)
    status = "needs_clarification" if (
        quality_fail or verification.status in ("conflict", "insufficient_evidence")
    ) else "answered"
    return reply, verification, status