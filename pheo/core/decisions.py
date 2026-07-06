HUMAN_APPROVAL = "human_triage"
HUMAN_CORRECTION = "human_correction"
METHODOLOGY_ONBOARDING = "methodology_onboarding"


def decision_weight(action: str, corrected_output: str = "") -> float:
    if action in {"edit", "correct"} or corrected_output:
        return 1.0
    if action == "approve":
        return 0.9
    if action == "reject":
        return 0.6
    return 0.75
