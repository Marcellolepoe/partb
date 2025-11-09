import json
import os
import sys
from typing import Dict, List


LETTER_ORDER = ["A", "B", "C", "D"]
VERB_SEQUENCE = ["Argues", "Maintains", "Contends", "Posits"]
MAX_WORDS = 38

TARGET_DIRECTORIES = [
    os.path.join(
        "Question Bank Raw",
        "5 Contemporary Legal Knowledge",
        "2 Laws and Technology",
    ),
    os.path.join(
        "QUESTION BANK PLATFORM",
    ),
]

TARGET_FILES = [f"clk-lt-module{index}-questions.json" for index in range(1, 5)]

CYCLE_MAP: Dict[str, List[str]] = {
    "clk-lt-module1-questions.json": ["C", "A", "D", "B"],
    "clk-lt-module2-questions.json": ["A", "D", "B", "C"],
    "clk-lt-module3-questions.json": ["D", "B", "C", "A"],
    "clk-lt-module4-questions.json": ["B", "C", "A", "D"],
}


def truncate_words(text: str, limit: int = MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    trimmed = " ".join(words[:limit])
    if trimmed.endswith((".", ",", ";", ":")):
        trimmed = trimmed[:-1]
    return trimmed + "..."


def rewrite_option(text: str, verb: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped

    stripped = stripped.replace(";", ".")
    sentences = [sentence.strip() for sentence in stripped.split(".") if sentence.strip()]
    if sentences:
        primary = sentences[0]
        secondary = sentences[1] if len(sentences) > 1 else ""
        core = f"{primary} {secondary}".strip()
    else:
        core = stripped

    core = truncate_words(core)
    core = core[0].lower() + core[1:] if core else core
    rewritten = f"{verb} that {core}".strip()
    if not rewritten.endswith("."):
        rewritten += "."
    return rewritten


def rebalance_question(question: Dict, index: int, cycle: List[str]) -> None:
    desired_letter = cycle[index % len(cycle)]
    current_letter = question.get("correct_answer", "A")

    options = question.get("options", {})
    explanation = question.get("explanation", {})
    incorrect_map = explanation.get("incorrect", {})

    if desired_letter != current_letter:
        options[current_letter], options[desired_letter] = (
            options.get(desired_letter, ""),
            options.get(current_letter, ""),
        )

        if incorrect_map:
            incorrect_map[current_letter], incorrect_map[desired_letter] = (
                incorrect_map.get(desired_letter, ""),
                incorrect_map.get(current_letter, ""),
            )

        question["correct_answer"] = desired_letter

    ordered_options = {}
    for offset, letter in enumerate(LETTER_ORDER):
        verb = VERB_SEQUENCE[offset % len(VERB_SEQUENCE)]
        option_text = options.get(letter, "")
        ordered_options[letter] = rewrite_option(option_text, verb)
        if incorrect_map:
            incorrect_map.setdefault(letter, "")
    question["options"] = ordered_options

    if incorrect_map:
        question["explanation"]["incorrect"] = {
            letter: incorrect_map.get(letter, "") for letter in LETTER_ORDER if letter in incorrect_map
        }


def process_file(directory: str, filename: str) -> None:
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    cycle = CYCLE_MAP.get(filename, LETTER_ORDER)
    questions = data.get("questions", [])
    for idx, question in enumerate(questions):
        rebalance_question(question, idx, cycle)

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def verify_alignment() -> None:
    mismatches = []
    for directory in TARGET_DIRECTORIES:
        for filename in TARGET_FILES:
            path = os.path.join(directory, filename)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            for question in data.get("questions", []):
                letter = question.get("correct_answer")
                incorrect = question.get("explanation", {}).get("incorrect", {})
                tags = [key for key, value in incorrect.items() if key in LETTER_ORDER and "correct answer" in value.lower()]
                if letter and tags and tags != [letter]:
                    mismatches.append((path, question.get("id"), letter, tags))

    if mismatches:
        for entry in mismatches:
            print(f"[WARN] {entry[0]} {entry[1]} -> correct={entry[2]}, flagged={entry[3]}")
    else:
        print("All incorrect maps align with declared correct answers.")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_alignment()
        return

    for directory in TARGET_DIRECTORIES:
        for filename in TARGET_FILES:
            process_file(directory, filename)


if __name__ == "__main__":
    main()

