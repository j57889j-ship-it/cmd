from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ParsedQuestion:
    text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    explanation: str = ""


class ParseError(ValueError):
    pass


def _extract(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.strip().upper().startswith(prefix):
            return line.split(":", 1)[1].strip() if ":" in line else ""
    return ""


def parse_txt(content: str, limit: int = 100) -> tuple[list[ParsedQuestion], list[str], int]:
    blocks = []
    current: list[str] = []
    for raw in content.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)

    errors: list[str] = []
    parsed: list[ParsedQuestion] = []
    seen: set[str] = set()
    duplicate_count = 0

    for idx, lines in enumerate(blocks, start=1):
        question_lines = [line for line in lines if line and not line.upper().startswith(("A:", "B:", "C:", "D:", "ANSWER:", "EXPLANATION:"))]
        if question_lines and question_lines[0].split(".", 1)[0].isdigit():
            question_lines[0] = question_lines[0].split(".", 1)[1].strip()
        text = " ".join(question_lines).strip()
        a = _extract(lines, "A:")
        b = _extract(lines, "B:")
        c = _extract(lines, "C:")
        d = _extract(lines, "D:")
        ans = _extract(lines, "ANSWER:").upper()
        explanation = _extract(lines, "EXPLANATION:")
        errors_here: list[str] = []
        if not text:
            errors_here.append("savol matni yo‘q")
        if any(not value for value in (a, b, c, d)):
            errors_here.append("4 ta variant to‘liq emas")
        if ans not in {"A", "B", "C", "D"}:
            errors_here.append("ANSWER A/B/C/D bo‘lishi kerak")
        normalized = " ".join(text.casefold().split())
        if normalized in seen and normalized:
            duplicate_count += 1
            errors_here.append("fayl ichida duplicate")
        if errors_here:
            errors.append(f"{idx}-savol: " + ", ".join(errors_here))
            continue
        seen.add(normalized)
        parsed.append(ParsedQuestion(text, a, b, c, d, ans, explanation))
        if len(parsed) >= limit:
            break
    return parsed, errors, duplicate_count
