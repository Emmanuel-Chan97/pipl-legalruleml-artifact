"""Replay the PIPL paper's experiments using the archived code, inputs and expectations."""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from lxml import etree

ROOT = Path(__file__).resolve().parent
SUPPLEMENT = ROOT / "supplement"


def run(script, *args):
    """Run an archived entry point and retain its original stdout."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    env.pop("PYTHONOPTIMIZE", None)  # Some archived checks use assertions.
    command = [sys.executable, str(script), *map(str, args)]
    result = subprocess.run(command, cwd=script.parent, env=env, stdout=subprocess.PIPE)
    if result.returncode:
        sys.stderr.buffer.write(result.stdout)
        result.check_returncode()
    return result.stdout


def compare_csv(actual, expected):
    generated = actual.read_bytes()
    reference = expected.read_bytes()
    if generated == reference:
        return "byte-identical"
    if generated.replace(b"\r\n", b"\n") == reference.replace(b"\r\n", b"\n"):
        return "identical apart from line endings"
    raise ValueError(f"Replayed data differ from {expected.relative_to(ROOT)}")


def article47(release, destination):
    """Report the scenario inputs and expected outcomes after running the original assertions."""
    sys.path.insert(0, str(release))
    try:
        from qa import article47 as checks
        from storage import for_export

        source = json.loads((release / "PIPL-model.json").read_bytes())
        model = for_export(source)
        parser = etree.XMLParser(no_network=True, resolve_entities=False)
        tree = etree.parse(str(release / source["interchange"]["file"]), parser)
        checks.validate_source(model)
        checks.validate_projection(model, tree)
    finally:
        sys.path.pop(0)

    expected_sizes = (8, 3, 7)
    suites = (checks.PROACTIVE_CASES, checks.CLAIM_CASES, checks.RESTRICTION_CASES)
    if tuple(map(len, suites)) != expected_sizes:
        raise ValueError("The archived Article 47 scenario counts have changed")
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["record", "scenario", "facts", "action", "expected_active_or_must_stop",
                         "source_check", "xml_check"])
        for record_id, cases in (("47.1a", checks.PROACTIVE_CASES), ("47.1b", checks.CLAIM_CASES)):
            for name, groups, requested, pending, expected in cases:
                facts = sorted(checks.GROUP_MEMBERS[group][0] for group in groups)
                if requested:
                    facts.append("request")
                if pending:
                    facts.append("not_yet_deleted")
                writer.writerow([record_id, name, "|".join(facts), "", expected, "pass", "pass"])
        for index, (retention, difficulty, action, expected) in enumerate(checks.RESTRICTION_CASES, 1):
            facts = ["consent_withdrawn"]
            if retention:
                facts.append("statutory_period_running")
            if difficulty:
                facts.append("technical_difficulty")
            writer.writerow(["47.2", f"restriction_{index}", "|".join(facts), action,
                             expected, "pass", "not exported (absence checked)"])


def reproduce(output):
    if output == ROOT or output == SUPPLEMENT or SUPPLEMENT in output.parents:
        raise ValueError("Choose a results folder separate from the archived inputs")
    rounds = SUPPLEMENT / "round3"
    with TemporaryDirectory() as work:
        work = Path(work)
        staged = work / "results"
        staged.mkdir()
        log = []
        for directory, name in (("r2", "R2.zip"), ("first", "R3-first-assessment.zip"),
                                ("final", "R3-final.zip")):
            with ZipFile(rounds / name) as archive:
                archive.extractall(work / directory)
        r2, final = work / "r2", work / "final"
        paired = final / "experiments" / "paired_experiment.py"
        for directory, filename in (("first", "first_assessment.csv"),
                                    ("final", "post_repair_regression.csv")):
            report = staged / filename
            data = run(paired, "--r2-root", r2, "--r3-root", work / directory, "--output", report)
            log.append(f"{filename} ({compare_csv(report, rounds / filename)})\n" + data.decode("utf-8"))
        verification = run(final / "verify.py", "--baseline-r2", r2 / "PIPL-model.json")
        log.append("Final release verification\n" + verification.decode("utf-8"))
        article47(final, staged / "article47_scenarios.csv")
        log.append("Article 47: 8 proactive + 3 request + 7 restriction scenarios passed on source; "
                   "the XML checks cover the first 11 and confirm the paragraph-two restriction is absent.")
        for script in (SUPPLEMENT / "anchor-example" / "run_all.py", SUPPLEMENT / "check_source_swap.py"):
            log.append(f"{script.name}\n" + run(script).decode("utf-8"))
        for folder, script, filename in (("replication", "run.py", "observed.csv"),
                                         ("refined", "run_refined.py", "refined_observed.csv")):
            report = staged / filename
            report.write_bytes(run(SUPPLEMENT / folder / script))
            log.append(f"{filename}: {compare_csv(report, SUPPLEMENT / folder / filename)}")
        inventory = staged / "inventory.json"
        inventory.write_bytes(run(SUPPLEMENT / "replication" / "inventory.py"))
        if json.loads(inventory.read_bytes()) != json.loads((SUPPLEMENT / "replication/inventory.json").read_bytes()):
            raise ValueError("Recount differs from the archived corpus inventory")
        log.append("inventory.json: matched archived corpus inventory")
        transcript = "\n\n".join(log) + "\n"
        (staged / "verification.log").write_text(transcript, encoding="utf-8")
        output.mkdir(parents=True, exist_ok=True)
        for report in staged.iterdir():
            shutil.copyfile(report, output / report.name)
        print(transcript, end="")
        print(f"Verified results written to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("replay"),
                        help="directory for regenerated files (default: ./replay)")
    if not __debug__:
        parser.error("Run without -O so all archived assertions are enabled")
    reproduce(parser.parse_args().output.expanduser().resolve())
