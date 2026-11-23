# Article 57 source-link example

This separately generated illustration packages Article 57 of the 20 August 2021 PIPL. The Chinese text is taken from the fixed transcription used by model 4.0. The competent agency's publication is at https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm. The article, two paragraphs, three points and two inline spans appear in `art57.akn.xml`. The project assigned the AKN identifiers to this example. They do not identify an officially published AKN manifestation.

`art57.lrml` contains the six pilot normative statements and two priorities for Article 57 copied from the frozen exchange export. The two field-level links to the local AKN spans were created for this worked example. Each `LegalSource` points to a local file and AKN fragment through `sameAs`. Its `Association` connects the source to a keyed native modality. The 57.2b power remains represented in the sidecar; its wording and the modal reconstruction of the duty in 57.2c share a span. The file `source-and-fields.json` records the source, ranges, fields and evidence methods. The source ranges are zero-based, half-open, and measured in Unicode code points in that frozen article transcription. The example makes no changes to the main export or its mutation results.

## Verify the complete example offline

The package includes both schemas and the local resolver used for the main export. Its Python dependencies are the same as those listed in `../replication/requirements.txt`. With those installed, run the following command from the directory containing this README:

```sh
python3 run_all.py
```

The script checks the hashes of the two original AKN schema files, validates the AKN portion against the pinned OASIS 2018 1.0 Part 2 schema (namespace 3.0), then calls the sibling replication package to validate the LegalRuleML derivative against the 1.0 Compact XSD and verify its local keys and override references. Finally it reconstructs the full article and checks all three field claims against the two AKN spans and the two native modality links. Both parsers run with network access disabled. The source-only comparison can also be run with the standard library using `python3 verify_anchors.py`.

## Schema sources and attribution

The two original files in `schema-akn30/` are unmodified copies of files distributed by OASIS with [Akoma Ntoso Version 1.0, Part 2](https://docs.oasis-open.org/legaldocml/akn-core/v1.0/os/part2-specs/akn-core-v1.0-os-part2-specs.html). The AKN schema header identifies OASIS Open as its copyright holder, © 2018, and licenses the schema under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode). Its original notice and technical credits remain in the schema. The companion XML namespace schema is authored by W3C and distributed alongside it by OASIS. The files remain retrievable from the [official OASIS schema directory](https://docs.oasis-open.org/legaldocml/akn-core/v1.0/os/part2-specs/schemas/).

| Original file | SHA-256 |
|---|---|
| akomantoso30.xsd | 6f61fe84cbb6f8cb0e8418cd67b74a63da9990e6573b5a3491f623184f45c4fd |
| xml.xsd | 61960fb3131e38022caad5360e2f33a3382578ab3c80cd58bd74320ede61b20c |
