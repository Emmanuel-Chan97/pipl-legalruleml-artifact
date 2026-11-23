# Evidence for the paper

The two inventory and results tables count different things. Table 1 counts records and XML statements in the unedited corpus. Table 2 counts what the exporter did when a single field was edited. The 18 Article 47 scenarios are a separate test of the unedited model.

## Table 1 — corpus and export coverage

[Inventory](supplement/replication/inventory.json) · [Counting script](supplement/replication/inventory.py) · [Editable interchange data](supplement/replication/model/interchange-data.json) · [Native XML](supplement/replication/model/PIPL-LegalRuleML-1.0.lrml)

| Quantity | Where to check |
|---|---|
| 74 articles, 137 source fragments, 205 records, 198 normative units | Count `sources`, `source_fragments` and `records` in the interchange JSON. Count distinct `records[].norm_unit_id` for units. |
| 29 legal relationships, 16 exceptions, 28 modeled effects | Count `legal_relations`, `exceptions` and `effect_templates` in the same file. |
| 122 exported records across 57 articles | Select records with `legalruleml.status == "encoded"`; count their distinct `article` values. The `legalruleml.tier` values identify 13 detailed pilot records and 109 structural projections. |
| 83 local records | The `project_annotation` tier includes 29 records with a conduct operator (25 obligations and 4 prohibitions). All eight Article 66 records are local. |
| 124 native normative statements and two separately counted priorities | The XML contains 85 obligations, 14 prohibitions, 4 permissions, 7 rights and 14 constitutive statements. `inventory.py` separately counts the two `Override` elements. |

## Figures 1 and 2 — inspect the two representations

**Figure 1, Article 57.** Open the [AKN text of Article 57](supplement/anchor-example/art57.akn.xml), the [linked LegalRuleML excerpt](supplement/anchor-example/art57.lrml) and the [field-level source annotations](supplement/anchor-example/source-and-fields.json) side by side. The words **可以不通知个人** occupy the zero-based half-open range `[214,221)` in the supplied article transcription. Record `57.2a` qualifies the duty to notify the individual (`57.1c`). The departmental notice duty is `57.1b`. The words **有权要求** support the express power in the local record `57.2b`; the exported `57.2c` records the inferred duty once the department validly exercises that power. The [anchor verifier](supplement/anchor-example/run_all.py) checks this worked specimen. The AKN file covers Article 57 only.

**Figure 2, Article 57 fault F02.** In the [first-assessment results](supplement/round3/first_assessment.csv), locate `case=F02` for both versions. The edited field is `E57-PERSON-WAIVER.target_ids`. Under R2 the change was accepted but the separate pilot declaration still produced XML identical to the original. Under R3 the field check rejected the change before writing XML. The last three columns record a separate operation: directly changing the priority target in clean XML passed the schema and reference checks, but failed the pilot assertion.

**Article 21 fault F01.** The same comparison is available for editing `21.2c.content_expr` from “return or delete” to “return and delete”. Record `21.2d` holds the separate prohibition on retention. For F01 and F02 the disputed changes can be detected by the old pilot assertions when made directly in the XML.

## Table 2 — all 13 edits and the two assessment stages

[First assessment](supplement/round3/first_assessment.csv) · [Replay after repairs](supplement/round3/post_repair_regression.csv) · [Snapshot replay instructions](supplement/round3/README.md)

Each CSV has 26 data rows: one row for each of the 13 edits under R2 and another under its R3 comparator. Use `case`, `version`, `expected` and `source_decision` for Table 2. The columns `xml_vs_baseline`, `xsd`, `xml_refs`, `xml_pilot` and `diagnostic` show where the edit became visible. The three `direct_xml_*` columns refer to the separate direct-XML tests for F01 and F02. A rejected export has no XML to validate.

| Cases | What was edited | R2 | First R3 | Repaired R3 |
|---|---|---:|---:|---:|
| F01–F02 | Choice between actions; target of waiver | 0/2 | 2/2 | 2/2 |
| F03–F04 | Deletion trigger; storage exclusion | 0/2 | 2/2 | 2/2 |
| F05–F08 | Return recipient; valid-order trigger; deletion conditions | 0/4 | 4/4 | 4/4 |
| F09–F10 | Action qualified by “immediately”; holder of the Article 24 explanation right | 0/2 | 0/2 | 2/2 |
| **Faults rejected** | **Ten changes to the recorded interpretation** | **0/10** | **8/10** | **10/10** |
| **C01–C03, valid edits accepted** | Editorial note; reordered Article 21 alternatives; reordered Article 47 grounds | **3/3** | **3/3** | **3/3** |

Of the ten faulty edits, F01, F02, F04, F05, F06, F08 and F09 left the R2 XML byte-identical. F03, F07 and F10 changed it. All ten R2 outputs passed the schema, reference and existing pilot checks. The repaired R3 was run on the same panel after its two first-assessment misses were known.

The [R2 snapshot](supplement/round3/R2.zip), [first R3 snapshot](supplement/round3/R3-first-assessment.zip) and [repaired R3 snapshot](supplement/round3/R3-final.zip) retain the versions that produced these results. In the [browsable copy of the repaired snapshot](r3-final/), [experiments/paired_experiment.py](r3-final/experiments/paired_experiment.py) defines the 13 edits and the direct XML comparison. `qa/pilot_consistency.py` checks the pilot rules and `qa/post_challenge.py` implements the two repairs.

## Article 47 — 18 scenarios

See the [18 scenario rows](examples/article47-scenarios.csv) and the [original Article 47 checks](r3-final/qa/article47.py) in the repaired snapshot. Its `PROACTIVE_CASES` cover the duty to delete (8), `CLAIM_CASES` cover the right to request deletion (3), and `RESTRICTION_CASES` cover the duty to stop other processing, with exceptions for storage and necessary security measures (7). The inputs and expected outcomes are explicit. `validate_source` checks all three sets against records `47.1a`, `47.1b` and `47.2`. `validate_projection` checks the first two records in XML and verifies that the third record, which remains local, has no XML statement.

The statute, the authors’ interpretation, and the program’s verdict are distinct evidence. Reproducing these results tests the software against the authors’ stated readings and expected outcomes. Independent legal annotation and evaluation on new statutes remain future work.
