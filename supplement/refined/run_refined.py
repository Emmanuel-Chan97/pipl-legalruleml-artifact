"""Replay the fixed cases and disclosed additional controls against the refined profile."""
import csv
import hashlib
import json
from pathlib import Path
import sys

from lxml import etree
from refined import check_refined, check_source_spans, RL

HERE = Path(__file__).resolve().parent
# The supplementary materials can place this directory beside or within replication.
REP = next(path for path in (HERE.parent / "replication", HERE.parent)
           if (path / "run.py").exists() and (path / "model").is_dir())
sys.path.insert(0, str(REP))
from run import CHECKSUM, NS, XML, change_one, change_tag, consequent, mutations
from profile import check_links, check_pilot, schema


def reverse_alternatives(root):
    expression = consequent("r-21-2c") + "/lrml:Obligation/ruleml:Or"
    def reverse(node):
        node[:] = list(reversed(node))
    change_one(root, expression, reverse)


def rename_statements_and_reverse(root):
    # Opaque labels for all 124 statement nodes; update references to each.
    nodes = root.xpath("//lrml:PrescriptiveStatement | //lrml:ConstitutiveStatement", namespaces=NS)
    replacements = {"#" + node.get("key"): "#opaque-s" + str(i) for i, node in enumerate(nodes)}
    reverse_alternatives(root)
    for node in nodes:
        node.set("key", replacements["#" + node.get("key")][1:])
    for node in root.iter():
        for name in ("keyref", "under", "over"):
            if node.get(name) in replacements:
                node.set(name, replacements[node.get(name)])


def rename_order_variables(root):
    statement = root.xpath("//lrml:PrescriptiveStatement[@key='r-57-2c']", namespaces=NS)[0]
    variables = list(statement.iter(RL + "Var"))
    substitutions = {name: "X" + str(i) for i, name in enumerate(sorted({v.text for v in variables}))}
    for v in variables:
        v.text = substitutions[v.text]


def regroup_conjunction(root):
    """P and Q and R and S -> (P and Q) and R and S in one guard."""
    expression = "//lrml:PrescriptiveStatement[@key='r-57-2c']//ruleml:if/ruleml:And"
    def nest_first_pair(node):
        nested = etree.Element(RL + "And")
        nested.extend(list(node)[:2])
        node.insert(0, nested)
    change_one(root, expression, nest_first_pair)


def additional():
    order_person = "//lrml:PrescriptiveStatement[@key='r-57-2c']//ruleml:Atom[ruleml:Rel[@iri='urn:pipl-pilot:predicate:valid_notice_order']]/ruleml:Var[3]"
    return [
        ("C3", "reverse the two disjuncts in the return/delete duty", reverse_alternatives),
        ("C4", "consistently rename every statement key and reverse the disjunction", rename_statements_and_reverse),
        ("C5", "alpha-rename all variables in the ordered notice rule", rename_order_variables),
        ("C6", "regroup the positive conjunction in the ordered notice guard", regroup_conjunction),
        ("B1", "unprofiled remedy obligation changed to permission",
         lambda root: change_one(root, consequent("r-57-1a") + "/lrml:Obligation", lambda node: change_tag(node, "Permission"))),
        ("B2", "bind order to a different person from the notice recipient",
         lambda root: change_one(root, order_person, lambda node: setattr(node, "text", "OtherPerson"))),
    ]


def main():
    source = XML.read_bytes()
    if hashlib.sha256(source).hexdigest() != CHECKSUM:
        raise ValueError("wrong input XML checksum")
    export = json.loads((REP / "model" / "interchange-data.json").read_text(encoding="utf-8"))
    check_source_spans(export)
    xsd = schema()
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(("id", "change", "compact_xsd", "local_links", "fixed_pilot", "source_role_profile", "refined_diagnostic"))
    for key, description, mutate in [*mutations(), *additional()]:
        root = etree.fromstring(source, etree.XMLParser(no_network=True, resolve_entities=False))
        mutate(root)
        diagnostics = check_refined(root)
        passes = (xsd.validate(root), not check_links(root), not check_pilot(root), not diagnostics)
        out.writerow((key, description, *("pass" if passed else "flag" for passed in passes), " | ".join(diagnostics)))


if __name__ == "__main__":
    main()
