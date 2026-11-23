"""Validate a PIPL Compact file plus independently specified pilot invariants."""
import argparse
from collections import Counter
from pathlib import Path
from lxml import etree

BASE = Path(__file__).resolve().parent / 'schemas'
NS = {'lrml':'http://docs.oasis-open.org/legalruleml/ns/v1.0/', 'ruleml':'http://ruleml.org/spec'}

class OfflineResolver(etree.Resolver):
    def resolve(self, url, _public_id, context):
        local = {'http://www.w3.org/2009/01/xml.xsd': 'xml-2009.xsd', 'http://www.w3.org/2001/XMLSchema-datatypes': 'XMLSchema-datatypes.xsd'}.get(url)
        return self.resolve_filename(str(BASE/'w3c'/local), context) if local else None


def schema():
    parser = etree.XMLParser(no_network=True)
    parser.resolvers.add(OfflineResolver())
    return etree.XMLSchema(etree.parse(str(BASE/'xsd-schema/compact/lrml-compact.xsd'), parser))


def check_links(root):
    errors = []
    keys = Counter(k.removeprefix(':') for k in root.xpath('//@key'))
    reference_ids = set(root.xpath('//lrml:LegalReference/@refersTo | //lrml:Reference/@refersTo', namespaces=NS))
    for key, count in keys.items():
        if count > 1:
            errors.append(f'non-unique @key {key}: {count} occurrences')
    known = set(keys) | reference_ids
    for ref in root.xpath('//@keyref | //@over | //@under'):
        if ref.startswith('#') and ref[1:] not in known:
            errors.append(f'nonexistent local reference {ref} at line {ref.getparent().sourceline}')
    statement_keys = set(root.xpath('//lrml:PrescriptiveStatement/@key | //lrml:ConstitutiveStatement/@key', namespaces=NS))
    for override in root.xpath('//lrml:Override', namespaces=NS):
        for target in (override.get('over'), override.get('under')):
            if target and target.startswith('#') and target[1:] not in statement_keys:
                errors.append(f'profile Override target {target} is not a statement')
    return errors


def check_pilot(root):
    errors = []
    def evaluates(expression):
        return bool(root.xpath(expression, namespaces=NS))
    # Independently read Articles 21(2) and 57(2): return OR delete; waive notice to person only.
    returning = "//lrml:PrescriptiveStatement[@key='r-21-2c']/ruleml:Rule/ruleml:then/lrml:Obligation/ruleml:Or"
    if not evaluates(returning + "[count(ruleml:Atom)=2 and ruleml:Atom/ruleml:Rel[@iri='urn:pipl-pilot:predicate:return_personal_information'] and ruleml:Atom/ruleml:Rel[@iri='urn:pipl-pilot:predicate:delete_personal_information']]"):
        errors.append('Art. 21(2): expected one Obligation of return OR delete')
    preserving = "//lrml:PrescriptiveStatement[@key='r-21-2d']/ruleml:Rule/ruleml:then/lrml:Prohibition"
    if not evaluates(preserving):
        errors.append('Art. 21(2): expected independent Prohibition on retention')
    overrides = root.xpath("//lrml:Override[@over='#r-57-2a']/@under", namespaces=NS)
    if overrides != ['#r-57-1c']:
        errors.append('Art. 57(2): personal-notification waiver may override only the ordinary personal-notification obligation r-57-1c')
    if not evaluates("//lrml:Override[@over='#r-57-2c' and @under='#r-57-2a']"):
        errors.append('PIPL pilot reconstruction: valid regulator notice order must override personal-notification waiver')
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=Path)
    parser.add_argument('--pilot', action='store_true', help='Run original Article 21/57 regression invariants as well')
    args = parser.parse_args()
    root = etree.parse(str(args.file), etree.XMLParser(no_network=True, resolve_entities=False))
    xsd = schema()
    passed = xsd.validate(root)
    print('OASIS Compact XSD:', 'PASS' if passed else 'FAIL')
    if not passed:
        print(xsd.error_log)
        raise SystemExit(1)
    errors = check_links(root)
    print('Keys/source and override references:', 'PASS' if not errors else 'FAIL')
    if args.pilot:
        pilot_errors = check_pilot(root)
        print('Article 21/57 pilot semantics:', 'PASS' if not pilot_errors else 'FAIL')
        errors.extend(pilot_errors)
    if errors:
        print('\n'.join(errors))
        raise SystemExit(1)

if __name__ == '__main__':
    main()
