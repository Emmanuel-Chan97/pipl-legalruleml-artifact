"""Recount stored record types, native XML and source-precision indicators."""
from collections import Counter
import json
from pathlib import Path

from lxml import etree

BASE = Path(__file__).resolve().parent / 'model'
NS = {'lrml': 'http://docs.oasis-open.org/legalruleml/ns/v1.0/'}


def main():
    data = json.loads((BASE / 'interchange-data.json').read_text(encoding='utf-8'))
    xml = etree.parse(str(BASE / 'PIPL-LegalRuleML-1.0.lrml'), etree.XMLParser(no_network=True, resolve_entities=False))
    records = data['records']
    scopes = Counter(r['analysis_scope'] for r in records)
    tiers = Counter(r['legalruleml']['tier'] for r in records)
    encoded = [r for r in records if r['legalruleml']['status'] == 'encoded']
    node_types = ('Obligation', 'Prohibition', 'Permission', 'Right', 'ConstitutiveStatement', 'Override', 'Association')
    nodes = {tag: len(xml.xpath('//lrml:' + tag, namespaces=NS)) for tag in node_types}
    snippets = [a.get('refID', '') for a in xml.xpath('//lrml:LegalReference', namespaces=NS)]
    modal_anchor = next(a for r in records if r['id'] == '57.2a' for a in r['evidence']['modality']['source_anchors'] if a['precision'] == 'exact_field_excerpt')
    source = next(s['text'] for s in data['sources'] if s['id'] == modal_anchor['source_id'])
    out = {
        'model_version': data['schema_version'], 'articles': len(data['sources']), 'records': len(records),
        'record_scopes': scopes, 'record_tiers': tiers, 'encoded_records': len(encoded),
        'articles_with_encoded_record': len({r['article'] for r in encoded}),
        'competence_records': sum(r['rule_function'] == 'competence' for r in records),
        'project_arrays': {k: len(data[k]) for k in ('source_fragments','legal_relations','exceptions','effect_templates')},
        'xml_nodes': nodes,
        'native_statements': len(xml.xpath('//lrml:PrescriptiveStatement | //lrml:ConstitutiveStatement', namespaces=NS)),
        'xml_codepoint_references': sum(' Unicode code points ' in s for s in snippets),
        'waiver_excerpt': {'source': modal_anchor['source_id'], 'start': modal_anchor['start'], 'end': modal_anchor['end'], 'text': source[modal_anchor['start']:modal_anchor['end']]},
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
