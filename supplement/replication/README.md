# PIPL v4 source and frozen validation profile

`model/interchange-data.json` contains the complete version 4.0 interchange dataset dated 21 November 2026, including 74 Chinese article texts, 205 annotated record views and evidence fields. `model/PIPL-LegalRuleML-1.0.lrml` is the 402,492-byte Compact XML export on which all diagnostic edits operate. Article 21 and Article 57 use pilot predicates and variables. The remaining structural projections include project text predicates. Source texts link to the Chinese government publication at <https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm>.

## Reproduction

Use Python 3.9 or later with `lxml`. This run used Python 3.12.4, lxml 6.1.3 and libxml2 2.14.6. All paths resolve relative to these scripts. After `lxml` is installed, the checks run offline. Run from this directory:

```sh
python3 -m pip install -r requirements.txt
python3 profile.py model/PIPL-LegalRuleML-1.0.lrml --pilot
python3 run.py > replay.csv
diff observed.csv replay.csv
python3 inventory.py > recounted.json
diff inventory.json recounted.json
```

`profile.py` carries over the existing pilot's Compact schema test, local-link checks and four fixed XPath assertions. Its only porting change is the local schema directory. `run.py` verifies the baseline model's SHA-256 hash and starts each mutation or control from the same input bytes. Its three columns run independently, including for a dangling target. `pass` means a check accepted that particular document. `flag` means it raised a diagnostic. Five mutations describe source-sensitive changes. C0 is the untouched control. C1 supplies an unknown target to exercise link checking. C2 consistently renames one statement's local key and all references to that key. It deliberately retains independently named child nodes, predicate IRIs and comments. The previous checker's literal key comparison flags C2. These are designed diagnostic cases with a fixed, two-article profile.

`inventory.py` counts records from JSON, counts elements in the XML tree, and resolves the Art. 57(2) modal excerpt in the stored Chinese source. The zero-based half-open range [214,221) refers to Unicode code points in that specific transcription, including the article label, ideographic space and paragraph breaks. The underlying statute was promulgated on 20 August 2021.

## Source schemas

The `schemas` subdirectory preserves the OASIS LegalRuleML Core 1.0 Compact schemas and imported dependencies, with their original headers. `profile.py` maps the two W3C import URIs to their local copies. The entry point is `schemas/xsd-schema/compact/lrml-compact.xsd`. Normative distribution and dependencies:

- OASIS LegalRuleML Core 1.0, approved 30 August 2021: <https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/legalruleml-core-spec-v1.0-os.html>.
- OASIS XSD directory: <https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/xsd-schema/>.
- RuleML licensing reference in the datatype schema: <https://ruleml.org/licensing/RSL1.0-RuleML>.
- W3C XML namespace schema: <https://www.w3.org/2009/01/xml.xsd>.
- W3C XML Schema datatypes dependency: <https://www.w3.org/2001/XMLSchema-datatypes>.
- W3C software license: <https://www.w3.org/copyright/software-license/>.

The XML schema test reports application of the published XSD to this snapshot. The link and pilot checks are research code. The legal interpretations and project-level assumptions in the JSON remain attributable to the study. Schema copyright and source notices are retained separately from the project files.
