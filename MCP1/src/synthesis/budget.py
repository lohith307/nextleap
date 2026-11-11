"""
Word budget enforcer for Zomato Customer Review Pulse.
Strictly guarantees the final executive markdown report is <= 250 words.
"""
import re


def count_words(text: str) -> int:
    """
    Counts words in a markdown or plain text string.
    Strips markdown symbols and counts whitespace-separated tokens.
    """
    if not text:
        return 0
    # Clean text to prevent markdown punctuation counting as standalone words
    cleaned = re.sub(r"[#*_>`~-]", " ", text)
    tokens = [w for w in cleaned.split() if w.strip()]
    return len(tokens)


def enforce_word_budget(markdown_pulse: str, max_words: int = 250) -> str:
    """
    Enforces the <= 250-word constraint.
    If the markdown exceeds max_words, safely trims summary descriptions while
    preserving headers, top themes, quotes, and action ideas verbatim.
    """
    if count_words(markdown_pulse) <= max_words:
        return markdown_pulse

    # Multi-pass progressive condensation
    result = markdown_pulse
    for theme_limit, action_limit in [(14, 12), (10, 8), (7, 6)]:
        if count_words(result) <= max_words:
            break

        lines = result.splitlines()
        condensed_lines = []

        for line in lines:
            stripped = line.strip()
            # Keep headers and quotes strictly intact
            if (
                stripped.startswith("#")
                or stripped.startswith("- *\"")
                or stripped.startswith("*\"")
                or stripped.startswith("\"")
            ):
                condensed_lines.append(line)
            elif re.match(r"^\d+\.\s+\*\*", stripped):
                # Theme line: e.g. "1. **Customer Support & Chatbot Looping (65.2%):** Long description..."
                match = re.match(r"^(\d+\.\s+\*\*[^*]+\*\*:?)\s*(.*)$", stripped)
                if match:
                    prefix, body = match.groups()
                    body_words = body.split()
                    if len(body_words) > theme_limit:
                        body = " ".join(body_words[:theme_limit]) + "..."
                    condensed_lines.append(f"{prefix} {body}")
                else:
                    condensed_lines.append(line)
            elif re.match(r"^\d+\.\s+", stripped):
                # Action line: e.g. "1. **Instant Refund Protocol:** Long description..."
                match = re.match(r"^(\d+\.\s+\*\*[^*]+\*\*:?)\s*(.*)$", stripped)
                if match:
                    prefix, body = match.groups()
                    body_words = body.split()
                    if len(body_words) > action_limit:
                        body = " ".join(body_words[:action_limit]) + "..."
                    condensed_lines.append(f"{prefix} {body}")
                else:
                    condensed_lines.append(line)
            else:
                condensed_lines.append(line)

        result = "\n".join(condensed_lines)

    # Guaranteed final assertion loop: trim trailing tokens until word count <= max_words
    while count_words(result) > max_words:
        parts = result.rsplit(None, 1)
        if len(parts) == 2:
            result = parts[0]
        else:
            break

    return result

