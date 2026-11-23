"""Verify the round-two release, its reversible projections and selected interpretation checks."""
import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from lxml import etree

from qa import profile
from storage import for_export, to_round_one


ROOT = Path(__file__).resolve().parent
R1_SHA = "c42a439da00f3b5f220e65b8db899c502e6ce87e9076ab3bb170b5a73c94e770"
EXPANDED_SHA = "afb46927f50901c124b825e566a3365816324b3813188a12a74624aa07b5e40b"
XML_SHA = "1c3389f64e8f0a9b20f79776e21ef056a20da7cf45eb8c268c279c9cfac42e8d"
FIELDS = {"participants", "content_expr", "conduct_force", "activation", "exceptions",
          "temporal", "applicability", "effects"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def read_json(path):
    return json.loads(path.read_bytes())


def records_by_id(model):
    return {record["id"]: record for record in model["records"]}


def check_new_storage(model):
    catalog = model["source_anchor_catalog"]
    require(len(catalog) == len({canonical(anchor) for anchor in catalog.values()}) == 407,
            "Expected 407 distinct full source anchors")
    uses = Counter()
    states = Counter()
    force_overrides = set()
    for r in model["records"]:
        require(set(r).isdisjoint(model["question_catalog"]), f"{r['id']}: legacy question key")
        require(all(set(p) == {"role", "label"} for p in r["participants"]),
                f"{r['id']}: unexpected per-participant metadata")
        meta = r["field_annotations"]
        require(set(meta) == FIELDS, f"{r['id']}: incomplete field mapping")
        if "note" in meta["conduct_force"]:
            force_overrides.add(r["id"])
        require("target_record_ids" not in meta["exceptions"] and
                "target_record_ids_override" not in meta["exceptions"],
                f"{r['id']}: duplicate legal target list")
        for field, info in meta.items():
            require("source_anchors" not in info, f"{r['id']}.{field}: inline anchors")
            if "answer_state" in info:
                states[info["answer_state"]] += 1
                require("coverage" not in info and "anchor_refs" not in info,
                        f"{r['id']}.{field}: repeated state or empty anchors")
            uses.update(info.get("anchor_refs", []))
    require(len(model["records"]) == 205 and set(uses) == set(catalog) and sum(uses.values()) == 2111,
            "Record count, ordered anchor use count or anchor catalog coverage changed")
    require(states == {"not_applicable": 73, "not_separately_annotated": 584},
            "Applicability and annotation coverage states changed")
    require(force_overrides == {"57.2a"}, "Expected 204 shared notes and the individual 57.2a rationale")
    print("PASS  1,640 field annotations; 407 anchors/2,111 uses; 657 distinct-state cases; 204 shared notes")


def check_restored_views(model, baseline_path):
    old = to_round_one(model)
    require(sha256(canonical(old)).hexdigest() == R1_SHA, "Restored round-one data differs from release")
    if baseline_path:
        require(old == read_json(baseline_path), "Restored data differs from supplied round-one JSON")
    require(sha256(canonical(for_export(model))).hexdigest() == EXPANDED_SHA,
            "Expanded full dataset differs from release")
    rows = records_by_id(old)
    reasons = {rid for rid, r in rows.items() if "basis" in r.get("does_conduct_force_apply", {})}
    require(reasons == {"5.a", "7.a", "13.1", "13.2b", "26.gate", "28.2", "58.principle"},
            "Substantive judgments on conduct-force applicability changed")
    require(rows["48"]["legalruleml"]["native_element"] == "lrml:Right" and
            rows["48"]["does_conduct_force_apply"]["answer_state"] == "not_applicable",
            "Article 48 Right lost its distinction from a conduct operator")
    require(rows["35"]["what_exceptions"]["target_record_ids"] == ["35", "17.1"],
            "Article 35 target ordering changed")
    require(rows["57.2a"]["what_exceptions"]["target_record_ids"] == ["57.1c"],
            "Article 57 waiver should target only the individual notification")
    time_anchors = rows["57.1a"]["when"]["source_anchors"]
    span = next(a for a in time_anchors if a["kind"] == "span" and a["relation"] == "field_excerpt")
    source = next(s for s in old["sources"] if s["id"] == span["source_id"])
    require(source["text"][span["start"]:span["end"]] == "应当立即采取补救措施",
            "Article 57 timing lost its precise field excerpt")
    print("PASS  Both complete JSON snapshots; Article 35 target order, Article 57 timing/waiver, seven force judgments")


def check_edit_propagation(model):
    changed = deepcopy(model)
    rows = records_by_id(changed)
    # A runtime test value allows us to distinguish an actual reference from a cached copy.
    rows["13.1"]["linguistic_form"]["scope_note"] = "shared edit for verification"
    rows["57.2a"]["linguistic_form"]["scope_note"] = "a different general note"
    expected_waiver_note = rows["57.2a"]["field_annotations"]["conduct_force"]["note"]
    waiver = next(item for item in changed["exceptions"] if item["id"] == "E57-PERSON-WAIVER")
    waiver["target_ids"] = ["57.1b"]  # Deliberately incorrect; check reference propagation only.
    restored = records_by_id(to_round_one(changed))
    require(restored["13.1"]["does_conduct_force_apply"]["note"] == "shared edit for verification" and
            restored["57.2a"]["what_force"]["note"] == expected_waiver_note,
            "Shared and individually written rationales did not respond correctly to an edit")
    require(all(restored[rid]["what_exceptions"]["target_record_ids"] == ["57.1b"]
                for rid in ("57.1c", "57.2a")),
            "The two exception field views did not follow the central target edit")
    print("PASS  Central exception edits, inherited notes and the independent waiver note propagate correctly")


def check_xml(model_path, model):
    with TemporaryDirectory() as work:
        out = Path(work) / "rebuilt.lrml"
        subprocess.run([sys.executable, str(ROOT / "exporter/export_native.py"),
                        str(model_path), str(out)], check=True)
        data = out.read_bytes()
        require(sha256(data).hexdigest() == XML_SHA and
                data == (ROOT / model["interchange"]["file"]).read_bytes(), "XML byte baseline mismatch")
        doc = etree.parse(out, etree.XMLParser(no_network=True, resolve_entities=False))
    schema = profile.schema()
    schema.assertValid(doc)
    errors = profile.check_links(doc) + profile.check_pilot(doc)
    require(not errors, repr(errors))
    waiver, = doc.xpath("//lrml:Override[@over='#r-57-2a']", namespaces=profile.NS)
    waiver.set("under", "#r-57-1b")
    schema.assertValid(doc)
    require(not profile.check_links(doc) and any("r-57-1c" in e for e in profile.check_pilot(doc)),
            "Independent Article 57 pilot constraint missed the wrong but well-formed XML target")
    print("PASS  Byte-identical XML, official Compact XSD and pilot checks; independent wrong-target test")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-r1", type=Path, help="Optional released round-one PIPL-model.json")
    parser.add_argument("--baseline", type=Path, help="Optional fully expanded v4.1 role/label JSON")
    args = parser.parse_args()
    model_path = ROOT / "PIPL-model.json"
    model = read_json(model_path)
    check_new_storage(model)
    check_restored_views(model, args.baseline_r1)
    if args.baseline:
        require(for_export(model) == read_json(args.baseline), "Full data differs from supplied v4.1 baseline")
    check_edit_propagation(model)
    check_xml(model_path, model)


if __name__ == "__main__":
    main()
