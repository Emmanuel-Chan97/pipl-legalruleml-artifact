"""Reproduce one-change diagnostics on independent in-memory copies of the v4 XML."""
import csv
import hashlib
from pathlib import Path
import sys

from lxml import etree
from profile import NS, check_links, check_pilot, schema

BASE = Path(__file__).resolve().parent
XML = BASE / 'model' / 'PIPL-LegalRuleML-1.0.lrml'
CHECKSUM = '1c3389f64e8f0a9b20f79776e21ef056a20da7cf45eb8c268c279c9cfac42e8d'


def change_tag(node, name):
    node.tag = etree.QName(etree.QName(node).namespace, name)


def change_one(root, expression, action):
    matches = root.xpath(expression, namespaces=NS)
    if len(matches) != 1:
        raise ValueError(f'Expected one node for {expression}, found {len(matches)}')
    action(matches[0])


def consequent(key):
    return f"//lrml:PrescriptiveStatement[@key='{key}']/ruleml:Rule/ruleml:then"


WAIVER_EDGE = "//lrml:Override[@over='#r-57-2a' and @under='#r-57-1c']"
ORDER_PREDICATE = "//lrml:PrescriptiveStatement[@key='r-57-2c']//ruleml:if//ruleml:Rel[@iri='urn:pipl-pilot:predicate:valid_notice_order']"


def rename_identifier(root):
    # Rename the XML statement key and its local references, preserving all other keys.
    old = 'r-57-1c'
    new = 'r-57-1c-renamed'
    definition_count = 0
    reference_count = 0
    for node in root.iter():
        if node.get('key') == old:
            node.set('key', new)
            definition_count += 1
        for name in ('keyref', 'over', 'under'):
            if node.get(name) == '#' + old:
                node.set(name, '#' + new)
                reference_count += 1
    if definition_count != 1 or not reference_count:
        raise ValueError('Incomplete alpha-renaming control')


def mutations():
    return [
        ('C0', 'clean', lambda root: None),
        ('M1', 'Art21 return-or-delete to return-and-delete', lambda root: change_one(root, consequent('r-21-2c') + '/lrml:Obligation/ruleml:Or', lambda node: change_tag(node, 'And'))),
        ('M2', 'Art21 retention prohibition to duty', lambda root: change_one(root, consequent('r-21-2d') + '/lrml:Prohibition', lambda node: change_tag(node, 'Obligation'))),
        ('M3', 'Art57 waiver redirected to regulator notice', lambda root: change_one(root, WAIVER_EDGE, lambda node: node.set('under', '#r-57-1b'))),
        ('M4', 'Art57 permitted omission to obligatory omission', lambda root: change_one(root, consequent('r-57-2a') + '/lrml:Permission', lambda node: change_tag(node, 'Obligation'))),
        ('M5', 'Art57 order occurrence to authority harm assessment', lambda root: change_one(root, ORDER_PREDICATE, lambda node: node.set('iri', 'urn:pipl-pilot:predicate:authority_considers_harm_possible'))),
        ('C1', 'dangling waiver target', lambda root: change_one(root, WAIVER_EDGE, lambda node: node.set('under', '#missing-local-statement'))),
        ('C2', 'consistent local statement rename', rename_identifier),
    ]


def main():
    source = XML.read_bytes()
    if hashlib.sha256(source).hexdigest() != CHECKSUM:
        raise ValueError('XML checksum mismatch')
    xsd = schema()
    writer = csv.writer(sys.stdout, lineterminator='\n')
    writer.writerow(('id', 'change', 'compact_xsd', 'local_links', 'fixed_pilot', 'link_diagnostic', 'pilot_diagnostic'))
    for key, description, mutate in mutations():
        root = etree.fromstring(source, etree.XMLParser(no_network=True, resolve_entities=False))
        mutate(root)
        link_errors = check_links(root)
        pilot_errors = check_pilot(root)
        passed = (xsd.validate(root), not link_errors, not pilot_errors)
        statuses = ['pass' if check else 'flag' for check in passed]
        writer.writerow((key, description, *statuses, ' | '.join(link_errors), ' | '.join(pilot_errors)))


if __name__ == '__main__':
    main()
