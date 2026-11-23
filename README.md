# Auditing normative scope in China's Personal Information Protection Law

[中文说明](README.zh-CN.md) · [Evidence for each figure and table](EVIDENCE.md)

Research materials for *Auditing Normative Scope from Editable Records to LegalRuleML: A Case Study of China's Personal Information Protection Law*, by Jie Chen, Qingjing Chen, Yan Zhou, Hanrui Chen, Zigeng Huang and Ziqi Wang.

## Start with one edit

[Article 57, case F02](examples/article57-waiver/README.md) shows two ways of changing the target of the permission to omit notice. Follow the before/after JSON and XML excerpts to see why the earlier exporter accepted a changed record yet wrote exactly the same XML. The results table records what happened when the XML itself was edited.

## Inspect the materials

| What to examine | File |
|---|---|
| The final editable model, including Chinese statutory text and analytical records | [R3 model](r3-final/PIPL-model.json). For an interactive view, download the repository, open [view.html](r3-final/view.html) locally and select that JSON. |
| What was exchanged | [Final LegalRuleML XML](r3-final/PIPL-role-label.lrml) and [exporter](r3-final/exporter/export_native.py) |
| How the Article 57 source is linked to rules | [AKN specimen](supplement/anchor-example/art57.akn.xml), [linked LegalRuleML](supplement/anchor-example/art57.lrml), [field-level evidence](supplement/anchor-example/source-and-fields.json). The AKN specimen covers this article. |
| The edits behind Table 2 | [13 edit definitions](r3-final/experiments/paired_experiment.py), [first assessment](supplement/round3/first_assessment.csv), [same cases after repair](supplement/round3/post_repair_regression.csv) |
| The 18 Article 47 scenarios | [Scenario inputs and expected outcomes](examples/article47-scenarios.csv), [original executable checks](r3-final/qa/article47.py). The seven paragraph-two cases are checked in the editable data. The XML check confirms their rule is absent from the export. |
| Counts behind Table 1 | [Archived inventory](supplement/replication/inventory.json), [counting rules](EVIDENCE.md) |

## Reproduce the results

From the repository root, with Python 3.12:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reproduce.py --output replay
```

On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\python.exe` in the last two commands. The reference run used Python 3.12.4 and lxml 6.1.3. After dependency installation, the checks run offline with the bundled schemas.

The command unpacks three frozen releases into a temporary directory and runs their original checks. It generates two paired-edit CSVs, the earlier fixed and refined XML test CSVs, the corpus inventory, the Article 47 scenario table and a verification log in `replay/`. The four archived result CSVs are the comparison files. A substantive mismatch makes the command fail. The log distinguishes byte-identical output from output differing only in line endings.

| Software tested | Faulty edits rejected (of 10) | Valid edits accepted (of 3) |
|---|---:|---:|
| Earlier exporter (R2) | 0 | 3 |
| First R3 assessment | 8 | 3 |
| R3 after two repairs, same cases | 10 | 3 |

Seven faulty R2 edits left the XML unchanged. The other three changed its bytes; all ten outputs passed the Compact XSD, local reference checks and earlier XML assertions. These case outcomes test the authors’ stated legal readings. The two repaired cases were part of the first assessment.

## Versions and provenance

The [three ZIP snapshots](supplement/round3/README.md) are the frozen inputs to the replay. [r3-final/](r3-final/) is the exact extracted final snapshot for browsing. If you edit that directory to try a new hypothesis, run its own exporter and verifier; the root replay always tests the frozen snapshots. The [earlier interchange model](supplement/replication/model/interchange-data.json) supports the inventory and earlier XML experiments.

The [source-link note](supplement/anchor-example/README.md) identifies the Chinese statute, the locally assigned identifiers and the AKN schema. The bundled OASIS and W3C files retain their original identifiers and notices; see the [LegalRuleML notice](supplement/replication/schemas/OASIS-NOTICES.txt) and the [AKN schema header](supplement/anchor-example/schema-akn30/akomantoso30.xsd).
