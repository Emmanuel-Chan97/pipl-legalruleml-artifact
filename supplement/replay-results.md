# Replication of the archived PIPL experiments

The supplied supplement was copied into a fresh directory. The three archives were extracted separately and both paired comparisons were run from the instructions in `supplement/round3/README.md`. Python 3.12.4 and lxml 6.1.3 were used. This independently reruns the supplied tests and their expectations. It provides no independent legal annotation.

## Paired source edits

Each release accepted the three valid controls. The ordinary R2 exporter accepted all ten faulty source records. The first R3 accepted F09 and F10. After repairs the ordinary exporter rejected all ten on the same cases. The final release verifier also passed its separate preservation, schema, reference, completeness and consistency checks.

| Source edits, grouped by output from R2 | IDs | R2 decisions | First R3 decisions | Repaired R3 decisions |
| --- | --- | --- | --- | --- |
| Faults leaving XML byte-identical | F01, F02, F04, F05, F06, F08, F09 | 0/7 rejected | 6/7 rejected, F09 missed | 7/7 rejected |
| Faults changing XML bytes | F03, F07, F10 | 0/3 rejected | 2/3 rejected, F10 missed | 3/3 rejected |
| Valid changes leaving XML byte-identical | C01, C02 | 2/2 accepted | 2/2 accepted | 2/2 accepted |
| Valid change altering XML bytes | C03 | 1/1 accepted | 1/1 accepted | 1/1 accepted |

XSD, reference checks and the previous XML pilot checks passed all 13 R2 outputs. Direct edits to the output for F01 and F02 passed XSD and reference checks, and were flagged by the previous XML pilot. A rejected source edit produced no XML specimen. These groups use R2’s output behavior to classify each source edit.

## Article 47

The final Article 47 source and XML checker functions were separately rerun on the clean release. The case lists contain eight proactive-duty cases, three right-to-request cases and seven restrictions on other processing. All 18 passed in the editable data. The XML check for the two paragraph-one records passed, and the paragraph-two restriction was confirmed absent from the exchange.

## Earlier XML and anchor experiments

- Fixed-key XML assertions rejected 3/5 deliberately faulty variants M1–M5 (M1–M3). Refined assertions rejected 5/5. The Compact XSD and local-link tests accepted all five. Under the refined assertions, a consistent rename, reversed alternatives, their combination and alpha-renaming (C2–C5) passed. Equivalent regrouping of the positive conjunction (C6) was rejected. Unprofiled remedy-operator change B1 passed; binding the order and notification to different persons (B2) was rejected.
- The clean Article 57 excerpt passed the pinned OASIS AKN 3.0 and Compact XSD checks, its reference and source-text comparisons, and the three field claims, two AKN spans and two native modality links.
- Exchanging the two full-model source references passed the Compact XSD, links, fixed and role-based checks. In the separate excerpt fixture the corresponding span swap was rejected with `Wrong source for r-57-2a-modality`.

## Byte-for-byte result comparisons

All four locally regenerated CSVs are identical to the originals, including their line endings.

| Archived path within supplement | Size in bytes | Replayed SHA-256 |
| --- | ---: | --- |
| round3/first_assessment.csv | 7117 | b973ed6c8321b10618b5aaf956c7551ff597f8eefd5124cf68445b641c5b3afb |
| round3/post_repair_regression.csv | 7436 | f8862cf34c6dd160ac9e89993451d01cd95e7e3a6c60330c1fffc587ed398c20 |
| replication/observed.csv | 1109 | 1c1cd99766add08a6f0406d15ab80427bfd3d9b6d541eec96aef9860104ef928 |
| refined/refined_observed.csv | 1464 | d42826af149e512577db4d9aa0b1e809c157744bf584b09c56506a00c589192e |
