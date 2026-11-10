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
    current_count = count_words(markdown_pulse)
    if current_count <= max_words:
        return markdown_pulse

    # If over budget, condense paragraphs line by line
    lines = markdown_pulse.splitlines()
    condensed_lines = []

    for line in lines:
        stripped = line.strip()
        # Keep headers, quotes, and action ideas as-is
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
                if len(body_words) > 18:
                    body = " ".join(body_words[:18]) + "..."
                condensed_lines.append(f"{prefix} {body}")
            else:
                condensed_lines.append(line)
        elif re.match(r"^\d+\.\s+", stripped):
            # Action line: e.g. "1. **Instant Refund Protocol:** Long description..."
            match = re.match(r"^(\d+\.\s+\*\*[^*]+\*\*:?)\s*(.*)$", stripped)
            if match:
                prefix, body = match.groups()
                body_words = body.split()
                if len(body_words) > 16:
                    body = " ".join(body_words[:16]) + "..."
                condensed_lines.append(f"{prefix} {body}")
            else:
                condensed_lines.append(line)
        else:
            condensed_lines.append(line)

    result = "\n".join(condensed_lines)
    # Final check
    if count_words(result) > max_words:
        # Hard truncate trailing non-essential sentences if still over budget
        words = result.split()
        result = " ".join(words[:max_words])

    return result

