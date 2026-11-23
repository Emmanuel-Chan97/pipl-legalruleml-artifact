"""Paired, finite source-edit experiment using two released export CLIs.

The fixed test set below was specified before the first R3 run. Each edit
starts with the unmodified source for its own release. Expected invalidity is
a judgment about this PIPL encoding, not a prediction about the software.

The sample includes four motivating faults, six probes of roles, conditions
or scope (including a boundary case outside Articles 21, 47 and 57), and
three controls. A source-level catch requires the normal export CLI to reject
the editable input. For a rejected export there is no XML specimen to assess.
XSD, references and the XML profile are reported separately. For exactly two
cases, a corresponding direct edit of the baseline XML is also tested.
"""
import argparse
import csv
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from lxml import etree


@dataclass(frozen=True)
class Case:
    name: str
    expected: str
    where: str
    edit: str


CASES = (
    Case("F01", "invalid", "21.2c.content_expr", "Require return AND deletion instead of either"),
    Case("F02", "invalid", "E57-PERSON-WAIVER.target_ids", "Waive notification to department instead of individual"),
    Case("F03", "invalid", "47.1a.activation", "Condition proactive deletion on a prior request"),
    Case("F04", "invalid", "47.2.content_expr.object", "Remove storage from the retained activities"),
    Case("F05", "invalid", "21.2c.content_expr.args[return].recipient", "Return entrusted data to individual instead of controller"),
    Case("F06", "invalid", "57.2c.activation", "Trigger specific duty on departmental risk assessment without order"),
    Case("F07", "invalid", "47.1b.activation", "Delete the requirement that data have not yet been deleted"),
    Case("F08", "invalid", "47.2.activation", "Remove the statutory-retention obstacle; allow technical difficulty only"),
    Case("F09", "invalid", "57.1a.temporal.applies_to", "Assign immediacy exclusively to departmental notice, excluding remedies"),
    Case("F10", "invalid", "24.3a.participants[claim_holder].label", "Replace individual right holder with processor (outside target articles)"),
    Case("C01", "valid", "57.2a.field_annotations.conduct_force.note", "Append an editorial note"),
    Case("C02", "valid", "21.2c.content_expr.args", "Reverse the order of return/delete alternatives"),
    Case("C03", "valid", "47.1a.activation.args", "Reverse the order of the five alternative deletion grounds"),
)


def single(items):
    values = list(items)
    if len(values) != 1:
        raise ValueError(f"Expected exactly one entry, got {len(values)}")
    return values[0]


def edit_source(source, name):
    model = deepcopy(source)
    rows = {record["id"]: record for record in model["records"]}
    if name == "F01":
        rows["21.2c"]["content_expr"]["op"] = "all"
    elif name == "F02":
        waiver = single(e for e in model["exceptions"] if e["id"] == "E57-PERSON-WAIVER")
        waiver["target_ids"] = ["57.1b"]
    elif name == "F03":
        r = rows["47.1a"]
        r["activation"] = {"op": "all", "args": [r["activation"], {"op": "predicate", "text": "个人提出删除请求"}]}
    elif name == "F04":
        rows["47.2"]["content_expr"]["object"] = "除采取必要安全保护措施之外的个人信息处理活动"
    elif name == "F05":
        action = single(a for a in rows["21.2c"]["content_expr"]["args"] if a["predicate"] == "返还")
        action["recipient"] = "相关个人"
    elif name == "F06":
        rows["57.2c"]["activation"] = deepcopy(rows["57.2b"]["activation"])
    elif name == "F07":
        r = rows["47.1b"]
        remaining = single(a for a in r["activation"]["args"] if a.get("text") != "处理者尚未删除")
        r["activation"] = remaining
    elif name == "F08":
        both = rows["47.2"]["activation"]["args"]
        obstacles = single(a for a in both if any(term.get("text") == "法定保存期限未届满" for term in a.get("args", [])))
        technical = single(a for a in obstacles["args"] if a.get("text") == "从技术上难以删除")
        both[both.index(obstacles)] = technical
    elif name == "F09":
        single(rows["57.1a"]["temporal"])["applies_to"] = "仅通知履职部门，不包括采取补救措施"
    elif name == "F10":
        holder = single(p for p in rows["24.3a"]["participants"] if p["role"] == "claim_holder")
        holder["label"] = "个人信息处理者"
    elif name == "C01":
        rows["57.2a"]["field_annotations"]["conduct_force"]["note"] += "（术语已复核。）"
    elif name == "C02":
        rows["21.2c"]["content_expr"]["args"].reverse()
    elif name == "C03":
        rows["47.1a"]["activation"]["args"].reverse()
    else:
        raise ValueError(f"Unimplemented case {name}")
    if model == source:
        raise ValueError(f"Case {name}: mutation had no effect on source")
    return model


def load_profile(root, release):
    path = root / "qa" / "profile.py"
    spec = importlib.util.spec_from_file_location("paired_profile_" + release, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assess(doc, profile, schema):
    return ("pass" if schema.validate(doc) else "fail",
            "fail" if profile.check_links(doc) else "pass",
            "fail" if profile.check_pilot(doc) else "pass")


def direct_edit(name, raw, profile, schema):
    if name not in ("F01", "F02"):
        return ("not-tested",) * 3
    doc = etree.fromstring(raw)
    if name == "F01":
        path = "//lrml:PrescriptiveStatement[@key='r-21-2c']/ruleml:Rule/ruleml:then/lrml:Obligation/ruleml:Or"
        single(doc.xpath(path, namespaces=profile.NS)).tag = '{' + profile.NS["ruleml"] + '}And'
    else:
        path = "//lrml:Override[@over='#r-57-2a' and @under='#r-57-1c']"
        single(doc.xpath(path, namespaces=profile.NS)).set("under", "#r-57-1b")
    return assess(doc, profile, schema)


def launch(root, source, out):
    return subprocess.run([sys.executable, str(root / "exporter/export_native.py"), str(source), str(out)],
                          check=False, capture_output=True, text=True)


def run_release(root, release, work):
    model_file = root / "PIPL-model.json"
    source = json.loads(model_file.read_bytes())
    profile = load_profile(root, release)
    schema = profile.schema()
    out = work / "baseline.lrml"
    baseline = launch(root, model_file, out)
    if baseline.returncode:
        raise RuntimeError(f"{release} baseline export failed: {baseline.stderr}")
    raw = out.read_bytes()
    if raw != (root / source["interchange"]["file"]).read_bytes() or assess(etree.fromstring(raw), profile, schema) != ("pass",) * 3:
        raise RuntimeError(f"{release} clean baseline is inconsistent")
    rows = []
    for case in CASES:
        changed = work / "changed.json"
        changed.write_text(json.dumps(edit_source(source, case.name), ensure_ascii=False), encoding="utf-8")
        generated = work / "variant.lrml"
        generated.unlink(missing_ok=True)
        proc = launch(root, changed, generated)
        has_xml = generated.exists()
        if has_xml != (proc.returncode == 0):
            raise RuntimeError(f"{release} {case.name}: inconsistent exit code and output presence")
        row = {"case": case.name, "expected": case.expected, "editable_field": case.where, "edit": case.edit,
               "version": release, "source_decision": "accepted" if has_xml else "rejected",
               "xml_vs_baseline": "no-output", "xsd": "no-output", "xml_refs": "no-output",
               "xml_pilot": "no-output", "diagnostic": "", "baseline_xml_sha256": sha256(raw).hexdigest()}
        if has_xml:
            data = generated.read_bytes()
            row["xml_vs_baseline"] = "unchanged" if raw == data else "changed"
            row["xsd"], row["xml_refs"], row["xml_pilot"] = assess(etree.fromstring(data), profile, schema)
        else:
            diagnostic = (proc.stderr.strip() or proc.stdout.strip()).splitlines()
            row["diagnostic"] = diagnostic[-1] if diagnostic else f"exit {proc.returncode}"
        row["direct_xml_xsd"], row["direct_xml_refs"], row["direct_xml_pilot"] = direct_edit(case.name, raw, profile, schema)
        rows.append(row)
    return rows


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--r2-root", required=True, type=Path, help="Unpacked round-two release directory")
    cli.add_argument("--r3-root", required=True, type=Path, help="Unpacked round-three release directory")
    cli.add_argument("--output", required=True, type=Path, help="Destination for the complete long-format CSV")
    args = cli.parse_args()
    with TemporaryDirectory() as temp:
        root = Path(temp)
        rows = []
        for label, path in (("R2", args.r2_root), ("R3", args.r3_root)):
            dst = root / label
            dst.mkdir()
            rows.extend(run_release(path.resolve(), label, dst))
    rows.sort(key=lambda r: ([c.name for c in CASES].index(r["case"]), r["version"]))
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    for label in ("R2", "R3"):
        for status in ("invalid", "valid"):
            group = [r for r in rows if r["version"] == label and r["expected"] == status]
            print(f"{label} {status}: {sum(r['source_decision']=='rejected' for r in group)}/{len(group)} source edits rejected")


if __name__ == "__main__":
    main()
