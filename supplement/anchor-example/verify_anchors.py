"""Verify the Article 57 worked example using only the Python standard library."""
import json
from pathlib import Path
from urllib.parse import urldefrag
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
NS = {'a': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0',
      'l': 'http://docs.oasis-open.org/legalruleml/ns/v1.0/'}


def unique(items, description):
    if len(items) != 1:
        raise ValueError(f'Expected one {description}, found {len(items)}')
    return items[0]


def require(condition, description):
    if not condition:
        raise ValueError(description)


def verify():
    data = json.loads((ROOT / 'source-and-fields.json').read_text(encoding='utf-8'))
    akn = ET.parse(ROOT / 'art57.akn.xml')
    lrml = ET.parse(ROOT / 'art57.lrml')
    article = unique(akn.findall('.//a:article', NS), 'article')
    first, second = article.findall('a:paragraph', NS)
    # Reconstruct the line separators of the frozen plain-text edition.
    parts = [article.findtext('a:num', namespaces=NS) + '\u3000' +
             first.findtext('a:intro/a:p', namespaces=NS)]
    for point in first.findall('a:point', NS):
        parts.append(point.findtext('a:num', namespaces=NS) +
                     point.findtext('a:content/a:p', namespaces=NS))
    paragraph = unique(second.findall('a:content/a:p', NS), 'second paragraph text')
    parts.append(''.join(paragraph.itertext()))
    text = '\n\n'.join(parts)
    require(text == data['source']['text'], 'Article text differs from frozen source')
    local_source = {}
    for item in lrml.findall('.//l:LegalSource', NS):
        location, fragment = urldefrag(item.attrib['sameAs'])
        if location == 'art57.akn.xml':
            local_source[item.attrib['key']] = fragment

    field_names = set()
    span_ids = set()
    linked_keys = set()
    associations = lrml.findall('.//l:Association', NS)
    for field in data['fields']:
        identifier = field['eId']
        span = unique(akn.findall(f'.//a:span[@eId="{identifier}"]', NS), identifier)
        start, end = field['range']
        quote = ''.join(span.itertext())
        require(text[start:end] == field['quote'] == quote, f"Mismatch for {field['field']}")
        field_names.add(field['field'])
        span_ids.add(identifier)
        rule_key = field['rule_key']
        if rule_key is None:
            continue
        modality = unique([element for element in lrml.iter()
                           if element.get('key') in (rule_key, ':' + rule_key)], rule_key)
        require(modality.tag in [f'{{{NS["l"]}}}Permission', f'{{{NS["l"]}}}Obligation'],
                f'Expected a native modality at {rule_key}')
        assoc = unique([assoc for assoc in associations if any(
            t.get('keyref') == '#' + rule_key for t in assoc.findall('l:toTarget', NS)
        )], f'association for {rule_key}')
        src = unique(assoc.findall('l:appliesSource', NS), 'source operand')
        require(local_source[src.attrib['keyref'][1:]] == identifier, f'Wrong source for {rule_key}')
        linked_keys.add(rule_key)
    require(len(field_names) == 3 and len(span_ids) == 2 and len(linked_keys) == 2,
            'Expected three field claims, two spans, and two native modality links')
    print('Full Article 57 matches the pinned source. Three field claims, two AKN spans, '
          'and two native LegalRuleML modality links verified.')


if __name__ == '__main__':
    verify()
