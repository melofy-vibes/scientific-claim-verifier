"""Color helper functions for NLI labels and evidence scores."""


def label_color(label: str, palette: dict) -> str:
    """Return the hex color associated with an NLI label."""
    if label == "SUPPORTS":
        return palette["success"]
    if label == "CONTRADICTS":
        return palette["error"]
    return palette["warning"]


def score_color(score: float, palette: dict) -> str:
    """Return the hex color associated with an evidence-strength score."""
    if score >= 70:
        return palette["success"]
    if score >= 40:
        return palette["warning"]
    return palette["error"]


def theme_color(name: str, palette: dict) -> str:
    """Generic lookup into the active palette, with a safe fallback."""
    return palette.get(name, palette["text"])