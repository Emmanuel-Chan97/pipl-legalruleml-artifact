"""Export the PIPL native-operator model as LegalRuleML 1.0 Compact XML."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

from lxml import etree as E

# The release can run directly from an unpacked folder without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import for_export
from qa import article47, pilot_consistency, post_challenge

LRML = 'http://docs.oasis-open.org/legalruleml/ns/v1.0/'
RULEML = 'http://ruleml.org/spec'
NS = {'lrml': LRML, 'ruleml': RULEML}
VOCAB = 'urn:pipl:projection:'
OPERATORS = {'Obligation', 'Permission', 'Prohibition'}
ELEMENTS = OPERATORS | {'Right', 'ConstitutiveStatement'}
DEFINITION_TERMS = {
    '4.1': '个人信息', '4.2': '个人信息处理', '28.1': '敏感个人信息',
    '60.3': '履行个人信息保护职责的部门', '73.1': '个人信息处理者',
    '73.2': '自动化决策', '73.3': '去标识化', '73.4': '匿名化',
}
CLAIM_RIGHTS = {
    '24.3a': (('explanation', '请求说明', '对个人权益有重大影响的自动化决定'),),
    '45.1': (('access', '查阅', '本人个人信息'), ('copy', '复制', '本人个人信息')),
    '46.1': (('correct', '请求更正', '本人不准确的个人信息'), ('supplement', '请求补充', '本人不完整的个人信息')),
    '47.1b': (('deletion', '请求删除', '依法应删除而尚未删除的本人个人信息'),),
    '48': (('explanation', '请求解释说明', '个人信息处理规则'),),
}
ROLE_PRIORITY = ('obligor', 'actor')


class ProjectionError(ValueError):
    pass


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def name_id(value: str):
    return re.sub(r'[^A-Za-z0-9_-]+', '-', value)


def add(parent, namespace, name, text=None, **attrs):
    node = E.SubElement(parent, E.QName(namespace, name), **attrs)
    if text is not None:
        node.text = text
    return node


def rule(parent, name, text=None, **attrs):
    return add(parent, RULEML, name, text, **attrs)


def legal(parent, name, text=None, **attrs):
    return add(parent, LRML, name, text, **attrs)


def atom(parent, predicate, variables=(), values=()):
    node = rule(parent, 'Atom')
    rule(node, 'Rel', iri=f'{VOCAB}{predicate}')
    for variable in variables:
        rule(node, 'Var', variable)
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ProjectionError(f'Invalid text parameter for {predicate}: {value!r}')
        rule(node, 'Data', value)
    return node


def slot(parent, role, variable):
    node = rule(parent, 'slot')
    keyed_role = legal(node, role)
    rule(node, 'Var', variable)
    return keyed_role


def render_expr(parent, expression, variables=()):
    """Project the Boolean shape. Text-only leaves remain profile predicates."""
    op = expression.get('op')
    args = expression.get('args', [])
    if op in ('all', 'any'):
        if not args:
            raise ProjectionError(f'Empty {op} expression')
        if len(args) == 1:
            return render_expr(parent, args[0], variables)
        branch = rule(parent, 'And' if op == 'all' else 'Or')
        for child in args:
            render_expr(branch, child, variables)
        return branch
    if op == 'not':
        if len(args) != 1:
            raise ProjectionError('Negation must have one operand')
        branch = rule(parent, 'Neg')
        render_expr(branch, args[0], variables)
        return branch
    if op == 'predicate':
        return atom(parent, 'condition_text', variables, [expression['text']])
    if op in ('action', 'state'):
        signature = [expression['predicate'], expression['object']]
        actor = expression.get('actor')
        recipient = expression.get('recipient')
        relation = f'{op}_text'
        if actor is not None:
            relation += '_with_actor_label'
            signature.append(actor)
        if recipient is not None:
            relation += '_with_recipient_label'
            signature.append(recipient)
        return atom(parent, relation, variables, signature)
    raise ProjectionError(f'No safe projection for content operator {op!r}')


FIELD_QUESTIONS = {'participants': 'who_is_involved', 'content':'what_action',
                   'activation':'what_triggers_it', 'native_operator':'what_force',
                   'conduct_force_assessment':'does_conduct_force_apply'}


def choose_participant(record, roles):
    for role in roles:
        for entry in record['participants']:
            if entry['role'] == role and entry.get('label') not in (None, '', '尚未确定'):
                return entry['label']
    return None


def native_mode(mapping):
    value = mapping.get('native_element')
    if not isinstance(value, str) or not value.startswith('lrml:') or value[5:] not in ELEMENTS:
        raise ProjectionError(f'Unsupported native LegalRuleML element {value!r}')
    return value[5:]


def pilot_formula(parent, expr):
    op = expr['op']
    args = expr['args']
    if op == 'predicate':
        target = rule(parent, 'Atom')
        rule(target, 'Rel', iri=expr['iri'])
        for term in args:
            if set(term) != {'var'} or not term['var']:
                raise ProjectionError(f'Unsupported pilot term {term!r}')
            rule(target, 'Var', term['var'])
        return target
    connectives = {'all': 'And', 'any': 'Or', 'not': 'Neg'}
    if op not in connectives or not args or (op == 'not' and len(args) != 1):
        raise ProjectionError(f'Invalid pilot formula {expr!r}')
    target = rule(parent, connectives[op])
    for arg in args:
        pilot_formula(target, arg)
    return target


class Exporter:
    def __init__(self, data, pilot_root):
        data = for_export(data)
        self.data = data
        self.root = pilot_root
        self.doc_url = data.get('source', 'https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm')
        self.by_article = {source['article']: source for source in data['sources']}
        self.fragments = {fragment['id']: fragment for fragment in data['source_fragments']}
        self.references = pilot_root.find(f'{{{LRML}}}LegalReferences')
        self.associations = pilot_root.find(f'{{{LRML}}}Associations')
        self.statements = pilot_root.find(f'{{{LRML}}}Statements')
        self.reference_ids = {node.get('refersTo') for node in self.references}
        self.pilot_keys = {node.get('key'): node for node in self.statements if node.get('key')}
        self.existing_associations = set()
        self.exceptions_by_target = defaultdict(list)
        for exception in data['exceptions']:
            for target in exception['target_ids']:
                self.exceptions_by_target[target].append(exception['id'])

    def add_reference(self, identifier, citation):
        if identifier not in self.reference_ids:
            legal(self.references, 'LegalReference', refersTo=identifier, refID=citation,
                  refIDSystemName='PIPL-2021-08-20 项目条文与引文标识', refIDSystemSource=self.doc_url)
            self.reference_ids.add(identifier)
        return identifier

    def cite_anchor(self, article, fragment_id=None, citation=None):
        if fragment_id:
            fragment = self.fragments.get(fragment_id)
            if fragment is None or fragment['article'] != article:
                raise ProjectionError(f'Unresolved or mismatched source fragment {fragment_id!r} at Article {article}')
        default_citation = f'第{article}条'
        ident = f'cite-{name_id(fragment_id)}' if fragment_id else f'cite-a{article}'
        if article not in self.by_article:
            raise ProjectionError(f'Missing source for Article {article}')
        label = (citation or default_citation) + (f' [{fragment_id}]' if fragment_id else '')
        return self.add_reference(ident, label)

    def link(self, source, target):
        if (source, target) in self.existing_associations:
            return
        edge = legal(self.associations, 'Association')
        legal(edge, 'appliesSource', keyref=f'#{source}')
        legal(edge, 'toTarget', keyref=f'#{target}')
        self.existing_associations.add((source, target))

    def record_citations(self, record, statement):
        key = statement.get('key')
        article_citation = self.cite_anchor(record['article'])
        self.link(article_citation, key)
        for ref in record.get('source_refs', []):
            frag = self.fragments.get(ref.get('fragment_id'))
            if frag is not None:
                identifier = self.cite_anchor(frag['article'], frag['id'], ref.get('citation'))
                self.link(identifier, key)

    def field_citations(self, record, field, node, key):
        if node is None:
            return
        evidence = record[FIELD_QUESTIONS[field]]
        anchors = []
        evidence_anchors = evidence.get('source_anchors', [])
        spans = [anchor for anchor in evidence_anchors if anchor.get('kind') == 'span']
        if spans:
            for span in spans:
                article = int(span['article_ref'].removeprefix('a'))
                source = self.by_article[article]
                start, end = span['start'], span['end']
                if source['id'] != span['source_id'] or not 0 <= start < end <= len(source['text']):
                    raise ProjectionError(f'Invalid exact evidence span in {record["id"]}.{field}')
                identifier = f'cite-a{article}-cp{start}-{end}'
                label = f'{span["citation"]} [{source["id"]} Unicode code points {start}:{end}]'
                anchors.append(self.add_reference(identifier, label))
        else:
            # The HTML preserves article-level contextual sources and evidence methods.
            for anchor in evidence_anchors:
                fragment = self.fragments.get(anchor.get('fragment_id'))
                if fragment is not None and anchor.get('kind') == 'fragment':
                    anchors.append(self.cite_anchor(fragment['article'], fragment['id'], anchor.get('citation')))
        if not anchors:
            return
        if node.get('key') is None:
            prefix = ':' if E.QName(node).namespace == RULEML else ''
            node.set('key', f'{prefix}{key}')
        target = node.get('key').removeprefix(':')
        for source in anchors:
            self.link(source, target)

    def annotate_fields(self, record, statement, modal, content, activation, participant):
        key = statement.get('key')
        self.record_citations(record, statement)
        force_field = 'native_operator' if 'what_force' in record else 'conduct_force_assessment'
        for field, node in [(force_field, modal), ('content', content), ('activation', activation), ('participants', participant)]:
            suffix = 'modality' if field == force_field else field  # Stable, externally referenced XML ID.
            self.field_citations(record, field, node, f'{key}-{suffix}')

    def structure_rule(self, record, key, mode, right=None):
        ident = record['id']
        tag = 'ConstitutiveStatement' if mode == 'ConstitutiveStatement' else 'PrescriptiveStatement'
        statement = E.Element(E.QName(LRML, tag), key=key)
        comment = f"{record['citation']}｜{record['content']}"
        if record['temporal']:
            times = '；'.join(f"{entry['text']}（作用于{entry['applies_to']}）" for entry in record['temporal'])
            comment += f'。时间限定（文本元数据） {times}'
        legal(statement, 'Comment', comment)
        template = rule(statement, 'Rule', closure='universal')
        antecedent = rule(template, 'if')
        body = rule(antecedent, 'And')
        consequence = rule(template, 'then')
        base_scope = record['applicability']['text']
        atom(body, 'scope_text', values=[ident, base_scope])
        guarded = self.exceptions_by_target[ident]
        modal = None
        participant = None
        if mode == 'ConstitutiveStatement':
            variables = ('Entity',)
            if ident in DEFINITION_TERMS:
                # The definition criteria are kept as a compound source description, including non-exhaustive wording.
                atom(body, 'matches_source_definition', variables, [ident, record['source_quote']])
                content_node = atom(consequence, 'classified_as', variables, [DEFINITION_TERMS[ident]])
            else:
                content_node = render_expr(consequence, record['content_expr'], variables)
        elif mode == 'Right':
            variables = ('Claimant', 'DutyCounterparty')
            atom(body, 'claim_relationship_roles', variables, [choose_participant(record, ('claim_holder',)),
                                                                choose_participant(record, ('duty_counterparty',))])
            modal = legal(consequence, 'Right')
            participant = slot(modal, 'Bearer', 'Claimant')
            slot(modal, 'AuxiliaryParty', 'DutyCounterparty')
            _, action, target = right
            content_node = atom(modal, 'exercise_right_text', variables, [action, target])
        else:
            variables = ('Bearer',)
            atom(body, 'has_bearer_role', variables, [choose_participant(record, ROLE_PRIORITY)])
            modal = legal(consequence, mode)
            participant = slot(modal, 'Bearer', 'Bearer')
            if ident == '18.1':
                content_node = rule(modal, 'Neg')
                atom(content_node, 'action_text_with_recipient_label', variables,
                     ['告知', '第17条第一款规定的事项', '个人'])
            else:
                content_node = render_expr(modal, record['content_expr'], variables)
        activation_node = None
        if record['activation']:
            activation_node = render_expr(body, record['activation'], variables)
        for exception_id in guarded:
            atom(body, 'exception_does_not_apply', variables, [exception_id, ident])
        if len(body) == 1:
            antecedent.replace(body, body[0])
        return statement, modal, content_node, activation_node, participant

    def update_record(self, record):
        mapping = record['legalruleml']
        ident = record['id']
        key = mapping.get('statement_key')
        pilot_key = f'r-{name_id(ident)}'
        if mapping['status'] == 'retained':
            if pilot_key in self.pilot_keys:
                raise ProjectionError(f'{ident}: retained status conflicts with declared pilot citations')
            return
        if mapping['status'] != 'encoded' or key != pilot_key:
            raise ProjectionError(f'{ident}: expected an encoded record with key {pilot_key}')
        mode = native_mode(mapping)
        if mapping['tier'] == 'pilot_formalization':
            if key not in self.pilot_keys or mode not in OPERATORS or mapping['statement_keys'] != [key]:
                raise ProjectionError(f'{ident}: invalid pilot record')
            statement = self.pilot_keys[key]
            src_rule = statement.find('ruleml:Rule', NS)
            guard = src_rule.find('ruleml:if', NS)
            head = src_rule.find('ruleml:then', NS)
            # The pilot template contributes source references, strength, IDs and editorial text.
            # All normative operators, arguments, variables and formulae come from the model.
            guard.clear()
            head.clear()
            active = pilot_formula(guard, mapping['if'])
            modal = legal(head, mode)
            part = slot(modal, 'Bearer', mapping['bearer'])
            content = pilot_formula(modal, mapping['then'])
            self.annotate_fields(record, statement, modal, content, active, part)
            return
        if mapping['tier'] != 'structural_projection' or key in self.pilot_keys:
            raise ProjectionError(f'{ident}: invalid projection tier {mapping["tier"]!r}')
        if mode == 'Right':
            rights = CLAIM_RIGHTS.get(ident)
            if not rights:
                raise ProjectionError(f'{ident}: no declared right action and counterparty mapping')
            keys = [key if i == 0 else f'{key}-{item[0]}' for i, item in enumerate(rights)]
            projections = [self.structure_rule(record, k, mode, item) for k, item in zip(keys, rights)]
        else:
            keys = [key]
            projections = [self.structure_rule(record, key, mode)]
        if keys != mapping['statement_keys']:
            raise ProjectionError(f'{ident}: number or identity of output statements does not match mapping')
        for projection in projections:
            self.statements.append(projection[0])
            self.annotate_fields(record, *projection)

    def export(self):
        pilot_consistency.check_pilot_source(self.data)
        article47.validate_source(self.data)
        post_challenge.validate_source(self.data)
        self.root.find(f'{{{LRML}}}Comment').text = (
            '《中华人民共和国个人信息保护法》全法模型的 LegalRuleML Core 1.0 Compact 交换文件。'
            '第21、57条保留试点规则。其余输出适格记录的结构映射；中文原文片段和字段证据可经项目标识回到 HTML 查阅。'
            'urn:pipl:projection: 谓词需要另外提供词汇定义、法律解释与事实规则。'
        )
        for article in sorted(self.by_article):
            self.cite_anchor(article)
        for record in self.data['records']:
            self.update_record(record)
        encoded_ids = {item['legalruleml'].get('statement_key') for item in self.data['records']
                       if item['legalruleml']['status'] == 'encoded'}
        missing = set(self.pilot_keys) - encoded_ids
        if missing:
            raise ProjectionError(f'Missing declared records for pilot targets: {sorted(missing)}')
        declared = [(f"#r-{name_id(pair['over'])}", f"#r-{name_id(pair['under'])}")
                    for pair in self.data['interchange']['priorities']]
        actual = [(n.get('over'), n.get('under')) for n in self.root.iter(f'{{{LRML}}}Override')]
        if declared != actual:
            raise ProjectionError('Priority targets changed; supply the corresponding revised pilot template')
        pilot_consistency.check_pilot_projection(self.data, self.root)
        article47.validate_projection(self.data, self.root)
        post_challenge.validate_projection(self.data, self.root)
        return E.ElementTree(self.root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pilot', type=Path, default=Path(__file__).with_name('pilot-template.lrml'))
    args = parser.parse_args()
    data = read_json(args.model)
    doc = E.parse(str(args.pilot), E.XMLParser(no_network=True, resolve_entities=False, remove_blank_text=True))
    try:
        tree = Exporter(data, doc.getroot()).export()
    except (ValueError, ProjectionError) as error:
        parser.exit(2, f"Validation failed: {error}\n")
    tree.write(str(args.output), encoding='UTF-8', xml_declaration=True, pretty_print=True)


if __name__ == '__main__':
    main()
