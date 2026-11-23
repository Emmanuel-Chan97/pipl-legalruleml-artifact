"""Replay the separate field-source swap used in the illustrated draft."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
from lxml import etree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "refined"))
sys.path.insert(0, str(HERE / "anchor-example"))
import run_refined as pilot
import verify_anchors as anchors


def exchange_sources(tree):
    """Exchange the source operands of the two selected modal associations."""
    sources = []
    for suffix in ("2a", "2c"):
        key = f"#r-57-{suffix}-modality"
        matches = tree.xpath("//lrml:Association[lrml:toTarget/@keyref=$key]/lrml:appliesSource",
                             namespaces=pilot.NS, key=key)
        if len(matches) != 1:
            raise ValueError(f"Expected one source for {key}")
        sources.append(matches[0])
    left, right = sources
    first, second = left.attrib["keyref"], right.attrib["keyref"]
    if first == second:
        raise ValueError("Control sources must differ")
    left.set("keyref", second)
    right.set("keyref", first)
    print(f"Exchanged {first} and {second}")


def run():
    export = json.loads((pilot.REP / "model" / "interchange-data.json").read_text(encoding="utf-8"))
    pilot.check_source_spans(export)
    tree = etree.parse(str(pilot.XML))
    xsd = pilot.schema()
    def results():
        return xsd.validate(tree), not pilot.check_links(tree), not pilot.check_pilot(tree), not pilot.check_refined(tree)
    assert all(results()), "Full-law baseline rejected"
    exchange_sources(tree)
    actual = results()
    print("Full-law XSD, links, fixed, role accepted:", actual)
    if not all(actual):
        raise RuntimeError("Unexpected full-law outcome")
    anchors.verify()
    with tempfile.TemporaryDirectory() as temporary:
        dest = Path(temporary)
        for name in ("source-and-fields.json", "art57.akn.xml", "art57.lrml"):
            shutil.copyfile(anchors.ROOT / name, dest / name)
        sub = etree.parse(str(dest / "art57.lrml"))
        exchange_sources(sub)
        sub.write(str(dest / "art57.lrml"), encoding="UTF-8", xml_declaration=True)
        old = anchors.ROOT
        try:
            anchors.ROOT = dest
            try:
                anchors.verify()
            except ValueError as error:
                if str(error) != "Wrong source for r-57-2a-modality":
                    raise
                print("Article 57 field-to-excerpt verifier rejected:", error)
            else:
                raise RuntimeError("Expected a wrong-source diagnostic")
        finally:
            anchors.ROOT = old


if __name__ == "__main__":
    run()

