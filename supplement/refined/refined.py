"""Audit six source-anchored roles in the PIPL project's Compact export."""
import json
from pathlib import Path
from lxml import etree

HERE = Path(__file__).resolve().parent
PROFILE = json.loads((HERE / "expectations.json").read_text(encoding="utf-8"))
LR = "{http://docs.oasis-open.org/legalruleml/ns/v1.0/}"
RL = "{http://ruleml.org/spec}"
P = PROFILE["predicate_namespace"]


class OutsideProfile(ValueError):
    """The selected source rule falls outside this profile's XML fragment."""


def parse_formula(node):
    """Represent the limited Compact fragment; atoms keep argument order."""
    if node.tag == RL + "Atom":
        children = list(node)
        if not children or children[0].tag != RL + "Rel":
            raise OutsideProfile("expected a relation followed by variables")
        iri = children[0].get("iri", "")
        variables = children[1:]
        if not iri.startswith(P) or any(v.tag != RL + "Var" or not v.text for v in variables):
            raise OutsideProfile("expected project predicate and variable arguments")
        return " ".join([iri[len(P):], *(v.text for v in variables)])
    operators = {RL + name: name for name in ("And", "Or", "Neg")}
    if node.tag not in operators:
        raise OutsideProfile("unsupported formula " + etree.QName(node).localname)
    return [operators[node.tag], *(parse_formula(child) for child in node)]


def shape(formula):
    """Canonical skeleton, ignoring variable spellings and commutative ordering."""
    if isinstance(formula, str):
        atom = formula.split()
        return ("Atom", atom[0], len(atom) - 1)
    op, *children = formula
    return (op, tuple(sorted(shape(child) for child in children)))


def match(wanted, found, binding):
    """Match the six declared shapes with an injective, rule-local renaming."""
    if shape(wanted) != shape(found):
        return False
    if isinstance(wanted, str):
        for role, variable in zip(wanted.split()[1:], found.split()[1:]):
            if role in binding and binding[role] != variable:
                return False
            if role not in binding and variable in binding.values():
                return False
            binding[role] = variable
        return True
    left = sorted(wanted[1:], key=shape)
    right = sorted(found[1:], key=shape)
    # Each sibling in the published profile has a distinct predicate skeleton.
    if len(set(map(shape, left))) != len(left):
        raise ValueError("ambiguous profile skeleton requires an explicit matching policy")
    return all(match(a, b, binding) for a, b in zip(left, right))


def check_source_spans(export):
    sources = {item["article"]: item for item in export["sources"]}
    for label, (article, start, end, quote) in PROFILE["source_evidence"].items():
        source = sources[article]
        if (source["text"][start:end] != quote or source["version"] != PROFILE["edition"]
                or source["url"] != PROFILE["source"]):
            raise ValueError("edition or source span mismatch: " + label)


def paragraph_targets(root):
    """Resolve actual local identifiers from citation and association elements."""
    references = {node.get("refersTo"): node.get("refID")
                  for node in root.iter(LR + "LegalReference")
                  if node.get("refIDSystemSource") == PROFILE["source"]}
    by_citation = {}
    for association in root.iter(LR + "Association"):
        targets = [x.get("keyref", "") for x in association.findall(LR + "toTarget")]
        for source in association.findall(LR + "appliesSource"):
            citation = references.get(source.get("keyref", "").removeprefix("#"))
            if citation is not None:
                by_citation.setdefault(citation, set()).update(targets)
    return by_citation


def contains_predicate(node, name):
    return node is not None and any(rel.get("iri") == P + name for rel in node.iter(RL + "Rel"))


def check_shapes(rule, spec):
    body = rule.find(RL + "if")
    head = rule.find(RL + "then")
    if body is None or head is None or len(body) != 1 or len(head) != 1:
        return ["expected one guard and one normative consequent"]
    modal = head[0]
    errors = []
    if modal.tag != LR + spec["modal"]:
        errors.append("expected " + spec["modal"])
    slots = modal.findall(RL + "slot")
    payloads = [child for child in modal if child.tag != RL + "slot"]
    if len(payloads) != 1:
        return errors + ["expected one consequent formula"]
    if len(slots) != 1 or [child.tag for child in slots[0]] != [LR + "Bearer", RL + "Var"]:
        return errors + ["expected one bearer variable"]
    binding = {}
    if not match(PROFILE["guards"][spec["guard"]], parse_formula(body[0]), binding):
        errors.append("guard differs from " + spec["guard"])
    if not match(spec["effect"], parse_formula(payloads[0]), binding):
        errors.append("effect shape or shared variable differs")
    if slots[0][1].text != binding.get(spec["bearer"]):
        errors.append("bearer differs from declared action participant")
    return errors


def check_refined(root):
    """Return project-profile diagnostics for an lxml Element or ElementTree."""
    if isinstance(root, etree._ElementTree):
        root = root.getroot()
    citation_targets = paragraph_targets(root)
    forms = {"#" + node.get("key"): node.find(RL + "Rule")
             for node in root.iter(LR + "PrescriptiveStatement") if node.get("key")}
    found = {}
    errors = []
    for role, spec in PROFILE["roles"].items():
        candidates = []
        for key in sorted(citation_targets.get(spec["citation"], ())):
            rule = forms.get(key)
            if rule is None or not contains_predicate(rule.find(RL + "then"), spec["find_effect"]):
                continue
            if "find_guard" in spec and not contains_predicate(rule.find(RL + "if"), spec["find_guard"]):
                continue
            candidates.append(key)
        if len(candidates) != 1:
            errors.append(f"{role}: expected one candidate at {spec['citation']}, got {len(candidates)}")
            continue
        target = found[role] = candidates[0]
        try:
            diagnostics = check_shapes(forms[target], spec)
        except OutsideProfile as error:
            diagnostics = [str(error)]
        errors.extend(f"{role}: {message}" for message in diagnostics)

    edges = list(root.iter(LR + "Override"))
    for role, targets in PROFILE["outgoing_priority_targets"].items():
        if role not in found or any(r not in found for r in targets):
            continue  # missing/ambiguous source roles have already been reported
        actual = sorted(node.get("under", "") for node in edges if node.get("over") == found[role])
        if actual != sorted(found[r] for r in targets):
            errors.append(f"{role}: outgoing priorities must target exactly {', '.join(targets)}")
    return errors
