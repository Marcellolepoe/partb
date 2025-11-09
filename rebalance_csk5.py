import json
import os
import sys


BASE_DIRS = [
    os.path.join(
        "Question Bank Raw",
        "5 Contemporary Legal Knowledge",
        "5 CSK-5",
    ),
]

MODULE_FILES = {
    base: sorted(
        fname
        for fname in os.listdir(base)
        if fname.startswith("csk5-module") and fname.endswith("-questions.json")
    )
    for base in BASE_DIRS
}

LETTERS = ["A", "B", "C", "D"]

# Rotational patterns staggered per module to smooth distribution
TARGET_CYCLES = {
    "csk5-module1-questions.json": ["A", "C", "D", "B"],
    "csk5-module2-questions.json": ["C", "A", "B", "D"],
    "csk5-module3-questions.json": ["D", "B", "A", "C"],
    "csk5-module4-questions.json": ["B", "D", "C", "A"],
    "csk5-module5-questions.json": ["C", "D", "A", "B"],
}


def _restore_core(text: str) -> str:
    stripped = text.strip()
    prefixes = [
        "Advocates for ",
        "Advocates ",
        "Assumes that ",
        "Suggests that ",
        "Maintains that ",
        "Positions ",
        "Claims that ",
        "Claims this emphasis ",
    ]
    for prefix in prefixes:
        if stripped.lower().startswith(prefix.lower()):
            stripped = stripped[len(prefix) :]
            break
    stripped = stripped.strip()
    if stripped.endswith("."):
        stripped = stripped[:-1]
    if stripped:
        stripped = stripped[0].upper() + stripped[1:]
    return stripped


def rewrite_option(text: str) -> str:
    """Normalise option phrasing to reduce obvious length differences."""
    core = _restore_core(text)
    if not core:
        return text.strip()

    if len(core) > 1 and core[1].isupper():
        lowered = core
    else:
        lowered = core[0].lower() + core[1:] if len(core) > 1 else core.lower()
    lowered = lowered.replace("  ", " ")

    if lowered.startswith("because "):
        rest = lowered[len("because ") :]
        return f"Assumes that {rest}."

    if lowered.startswith("to "):
        rest = lowered[len("to ") :]
        if rest.startswith("support "):
            rest = "supports " + rest[len("support ") :]
        return f"Claims this emphasis {rest}."

    if lowered.startswith("so "):
        lowered = lowered[len("so ") :]

    if lowered.startswith("support "):
        rest = lowered[len("support ") :]
        return f"Claims this emphasis supports {rest}."

    adjective_starters = {
        "large",
        "small",
        "purely",
        "general",
        "exclusive",
        "codified",
        "resident",
        "doctrinal",
        "investigative",
        "comprehensive",
        "broad",
        "narrow",
        "formal",
        "written",
        "constant",
        "subjective",
        "state",
        "private",
        "historic",
        "historically",
        "technical",
        "modular",
        "layered",
        "jury-centric",
    }
    first_word = lowered.split()[0]
    if first_word.rstrip(",") in adjective_starters:
        return f"Claims that the model rests on {lowered}."

    return f"Claims that {lowered}."


def rebalance_module(base_dir: str, module_file: str) -> None:
    cycle = TARGET_CYCLES.get(module_file, LETTERS)
    with open(os.path.join(base_dir, module_file), encoding="utf-8") as handle:
        data = json.load(handle)

    questions = data.get("questions", [])
    for index, question in enumerate(questions):
        desired_letter = cycle[index % len(cycle)]
        current_letter = question.get("correct_answer", "A")

        option_texts = [question["options"][letter] for letter in LETTERS]
        expl_entries = [question["explanation"]["options"][letter] for letter in LETTERS]

        if desired_letter != current_letter:
            current_idx = LETTERS.index(current_letter)
            desired_idx = LETTERS.index(desired_letter)
            option_texts[current_idx], option_texts[desired_idx] = (
                option_texts[desired_idx],
                option_texts[current_idx],
            )
            expl_entries[current_idx], expl_entries[desired_idx] = (
                expl_entries[desired_idx],
                expl_entries[current_idx],
            )
            question["correct_answer"] = desired_letter

        question["options"] = {letter: option_texts[i] for i, letter in enumerate(LETTERS)}
        question["explanation"]["options"] = {
            letter: expl_entries[i] for i, letter in enumerate(LETTERS)
        }

        for letter in LETTERS:
            question["options"][letter] = rewrite_option(question["options"][letter])

    with open(os.path.join(base_dir, module_file), "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def verify_modules() -> None:
    issues = []
    for module in MODULE_FILES:
        with open(os.path.join(BASE_DIR, module), encoding="utf-8") as handle:
            data = json.load(handle)
        for question in data.get("questions", []):
            correct_letter = question.get("correct_answer")
            option_expl = question.get("explanation", {}).get("options", {})
            true_letters = [letter for letter in LETTERS if option_expl.get(letter, {}).get("is_correct")]
            if true_letters != [correct_letter]:
                issues.append((module, question.get("id"), correct_letter, true_letters))
    if issues:
        for module, qid, correct_letter, true_letters in issues:
            print(f"[WARN] {module} {qid}: correct_answer={correct_letter}, true_flags={true_letters}")
    else:
        print("All modules have aligned correct_answer values and is_correct flags.")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_modules()
        return

    for base, files in MODULE_FILES.items():
        for module in files:
            rebalance_module(base, module)


if __name__ == "__main__":
    main()

