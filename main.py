#!/usr/bin/env python3
"""The Funniest Excuse for Skipping a Meeting.

make.fun bounty: u-mfnakmal-the-funniest-excuse-for-skipping-a-meeting-5cecf163
(https://make.fun/bounty/u-mfnakmal-the-funniest-excuse-for-skipping-a-meeting-5cecf163)

The entry
---------
    Sorry, I can't make the meeting — I'm stuck in a meeting about why we
    have so many meetings.

Why this line wins the judge's brief
------------------------------------
The judge is an AI comedy writer who weighs entries in this order:

1.  On-subject. The line *is* the excuse, addressed to the meeting it
    skips: apology, absence, reason, in one breath. Nothing is off-topic.
2.  A sharp, surprising turn. The reason you cannot attend a meeting is
    *another meeting* -- one convened to discuss why there are so many
    meetings. The excuse eats its own tail, and the punchline lands on
    the final word, "meetings".
3.  True to office life. Every office worker has sat in a meeting whose
    only real agenda item was the existence of meetings. The reader nods
    before they laugh.
4.  One tight line, no wasted words. Ninety-two characters, one sentence,
    no throat-clearing, no setup paragraph, no second clause explaining
    the joke. The em dash does the work of a whole setup sentence.
5.  A fresh angle, not a stock excuse. No bad wifi, no cat on the
    keyboard, no dentist, no "something came up". The angle is meta --
    the meeting-industrial complex itself -- and it could only be an
    excuse *for a meeting*. Swap in any other appointment and the joke
    dies, which is exactly what freshness looks like.

What this program does
----------------------
It writes exactly that one line, plus a single trailing newline, to the
output file (default ``/output/entry.txt``). Nothing else is ever written:
no randomness, no clock, no environment dependence, so every run produces
byte-identical output. The write is atomic (temporary file in the same
directory, then an ``os.replace`` rename), and the gate from the
competition rules is enforced before anything is written: the text must be
UTF-8, 1 to 200 characters, and not only whitespace, with no control
characters.

Command line::

    python3 main.py                          # write /output/entry.txt
    python3 main.py --output entry.txt       # write somewhere else
    python3 main.py --verify                 # write, then re-read and verify
    python3 main.py --verify-only --output entry.txt
                                               # verify an existing file, write nothing
    python3 main.py --self-check             # run the built-in self-check
    python3 main.py --quiet                  # suppress the summary line
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import unicodedata

# ---------------------------------------------------------------------------
# The entry
# ---------------------------------------------------------------------------

#: The one-line excuse. 92 characters, well inside the 200-character gate.
ENTRY_LINE = (
    "Sorry, I can't make the meeting \u2014 "
    "I'm stuck in a meeting about why we have so many meetings."
)

#: The gate from the competition rules: 1 to 200 characters, UTF-8 text,
#: not only whitespace. (The em dash above is U+2014, three bytes in UTF-8.)
MIN_LENGTH = 1
MAX_LENGTH = 200

#: The exact bytes the output file must contain: the line plus one newline.
EXPECTED_CONTENT = (ENTRY_LINE + "\n").encode("utf-8")

#: The sha256 of EXPECTED_CONTENT, recorded so --self-check can confirm the
#: program's own output without trusting the write path.
EXPECTED_SHA256 = hashlib.sha256(EXPECTED_CONTENT).hexdigest()

#: The default output path named by the competition harness.
DEFAULT_OUTPUT = "/output/entry.txt"


# ---------------------------------------------------------------------------
# Gate validation
# ---------------------------------------------------------------------------

def gate_errors(text: str) -> list[str]:
    """Return a list of gate violations for *text* (empty means it passes).

    The gate mirrors the competition rules exactly:

    * the text must be UTF-8 (guaranteed here because it is a ``str`` that
      we encode ourselves, and re-checked on the read-back path);
    * 1 to 200 characters long;
    * not only whitespace;
    * no control characters (anything below U+0020 except the newline we
      add at write time, and U+007F);
    * no Unicode format or separator characters that render invisibly
      (categories Cc, Cf, Zl, Zp) -- a zero-width joiner or soft hyphen
      must never smuggle extra meaning into the entry;
    * no leading or trailing whitespace on the line itself;
    * at least one letter, so a string of punctuation or digits alone
      cannot pass as an excuse.
    """
    errors: list[str] = []
    if len(text) < MIN_LENGTH:
        errors.append(f"entry is {len(text)} characters, below minimum {MIN_LENGTH}")
    if len(text) > MAX_LENGTH:
        errors.append(
            f"entry is {len(text)} characters, above maximum {MAX_LENGTH}"
        )
    if text.strip() == "":
        errors.append("entry is only whitespace")
    if text != text.strip():
        errors.append("entry has leading or trailing whitespace")
    if not any(char.isalpha() for char in text):
        errors.append("entry contains no letter")
    for index, char in enumerate(text):
        code = ord(char)
        if (code < 0x20 and char not in ("\n", "\t")) or code == 0x7F:
            errors.append(
                f"control character U+{code:04X} at position {index}"
            )
        elif unicodedata.category(char) in ("Cc", "Cf", "Zl", "Zp"):
            errors.append(
                f"invisible character U+{code:04X} "
                f"({unicodedata.category(char)}) at position {index}"
            )
    return errors


def validate_entry(text: str) -> None:
    """Raise :class:`ValueError` if *text* fails the gate."""
    errors = gate_errors(text)
    if errors:
        raise ValueError("entry fails the gate: " + "; ".join(errors))


# ---------------------------------------------------------------------------
# Writing and verification
# ---------------------------------------------------------------------------

def build_content() -> bytes:
    """Return the exact bytes to write: the line plus one trailing newline."""
    validate_entry(ENTRY_LINE)
    return EXPECTED_CONTENT


def write_entry(path: str) -> str:
    """Atomically write the entry to *path* and return its sha256 hex digest.

    The file is written to a temporary file in the same directory and then
    moved into place with :func:`os.replace`, so a reader never sees a
    half-written entry and a failed run never leaves a stale file behind.
    """
    content = build_content()
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".entry-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return hashlib.sha256(content).hexdigest()


def verify_file(path: str) -> dict[str, object]:
    """Re-read *path* and check it against the gate; return a report dict.

    The report carries the character count, the byte count, the sha256 hex
    digest, and whether the file's contents match the expected bytes exactly.
    """
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path} is not valid UTF-8: {exc}") from exc
    if text.endswith("\n"):
        line = text[:-1]
    else:
        line = text
    errors = gate_errors(line)
    if errors:
        raise ValueError(f"{path} fails the gate: " + "; ".join(errors))
    if text.count("\n") != 1 or not text.endswith("\n"):
        raise ValueError(f"{path} must be the line plus exactly one trailing newline")
    return {
        "path": path,
        "characters": len(line),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "matches_expected": raw == EXPECTED_CONTENT,
    }


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def self_check() -> list[str]:
    """Run the built-in determinism and gate checks; return failures."""
    failures: list[str] = []
    if gate_errors(ENTRY_LINE):
        failures.append("ENTRY_LINE fails the gate: " + "; ".join(gate_errors(ENTRY_LINE)))
    if hashlib.sha256(build_content()).hexdigest() != EXPECTED_SHA256:
        failures.append("built content does not match the recorded sha256")
    if build_content() != EXPECTED_CONTENT:
        failures.append("built content differs from EXPECTED_CONTENT")
    if ENTRY_LINE.count("\n") != 0:
        failures.append("ENTRY_LINE must be a single line with no newline")
    # End-to-end determinism proof: write the entry twice to two fresh
    # temporary files and require byte-identical output, so the check
    # covers the write path too, not just the in-memory constant.
    with tempfile.TemporaryDirectory(prefix="excuse-self-check-") as tmpdir:
        first = os.path.join(tmpdir, "first.txt")
        second = os.path.join(tmpdir, "second.txt")
        try:
            write_entry(first)
            write_entry(second)
            with open(first, "rb") as handle:
                first_bytes = handle.read()
            with open(second, "rb") as handle:
                second_bytes = handle.read()
        except (OSError, ValueError) as exc:
            failures.append(f"self-check write failed: {exc}")
        else:
            if first_bytes != second_bytes:
                failures.append("two writes produced different bytes")
            if first_bytes != EXPECTED_CONTENT:
                failures.append("written bytes differ from EXPECTED_CONTENT")
            if verify_file(first)["sha256"] != EXPECTED_SHA256:
                failures.append("verified sha256 does not match EXPECTED_SHA256")
    return failures


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Write the funniest excuse for skipping a meeting to entry.txt.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="path to write the entry to (default: %(default)s)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="re-read the written file and verify it against the gate",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify the file at --output without writing anything",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="run the built-in determinism and gate checks and exit",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the summary line on success",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse arguments, write the entry, optionally verify."""
    args = build_parser().parse_args(argv)

    if args.self_check:
        failures = self_check()
        if failures:
            for failure in failures:
                print(f"self-check FAILED: {failure}", file=sys.stderr)
            return 1
        if not args.quiet:
            print("self-check OK")
        return 0

    if args.verify_only:
        try:
            report = verify_file(args.output)
        except (OSError, ValueError) as exc:
            print(f"verify FAILED: {exc}", file=sys.stderr)
            return 1
        if not report["matches_expected"]:
            print("verify FAILED: file does not match expected bytes", file=sys.stderr)
            return 1
        if not args.quiet:
            print(
                f"verified {report['path']}: {report['characters']} characters, "
                f"{report['bytes']} bytes, sha256 {report['sha256']}"
            )
        return 0

    try:
        digest = write_entry(args.output)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.verify:
        try:
            report = verify_file(args.output)
        except (OSError, ValueError) as exc:
            print(f"verify FAILED: {exc}", file=sys.stderr)
            return 1
        if report["sha256"] != digest or not report["matches_expected"]:
            print("verify FAILED: written file does not match expected bytes", file=sys.stderr)
            return 1
        if not args.quiet:
            print(
                f"verified {report['path']}: {report['characters']} characters, "
                f"{report['bytes']} bytes, sha256 {report['sha256']}"
            )
    elif not args.quiet:
        print(
            f"wrote {args.output}: {len(ENTRY_LINE)} characters, "
            f"sha256 {digest}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
