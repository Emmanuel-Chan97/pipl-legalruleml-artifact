"""Post-challenge repairs for the recorded F09 and F10 misses, not part of the frozen evaluation."""
NS = {'lrml': 'http://docs.oasis-open.org/legalruleml/ns/v1.0/', 'ruleml': 'http://ruleml.org/spec'}
REMEDY_IRI = 'urn:pipl-pilot:predicate:take_immediate_remedial_measures'
PROJECTION = 'urn:pipl:projection:'


def _require(condition, path, message):
    if not condition:
        raise ValueError(f'{path}: {message}')


def _record(data, key):
    matches = [r for r in data['records'] if r['id'] == key]
    _require(len(matches) == 1, f'records[{key}]', 'expected one record')
    return matches[0]


def _role(record, role):
    values = [p['label'] for p in record['participants'] if p['role'] == role]
    _require(len(values) == 1, f"records[{record['id']}].participants[{role}]",
             'this role must identify one participant in this claim record')
    return values[0]


def _remedy(data):
    record = _record(data, '57.1a')
    path = 'records[57.1a].temporal'
    action = record.get('content_expr', {})
    _require(action.get('op') == 'action' and action.get('predicate') == '采取' and action.get('object') == '补救措施',
             'records[57.1a].content_expr', 'the explicit timing qualifies taking remedial measures')
    target = action['predicate'] + action['object']
    stated = [(i, t) for i, t in enumerate(record.get('temporal', []))
              if t.get('kind') == 'immediate' and t.get('resolution') == 'stated']
    _require(stated, path, 'preserve the express immediate-remedy qualification in Article 57(1)')
    for i, t in stated:
        _require(t.get('applies_to') in (target, action['object']), f'{path}[{i}].applies_to',
                 '原文的明确时间限定指向采取补救措施；其他通知时限的解读可另作 interpretive 标注')
    # Additional interpreted deadlines remain available as annotations and do not override the explicit qualification.
    mapping = record['legalruleml']
    head = mapping.get('then', {})
    _require(mapping.get('native_element') == 'lrml:Obligation' and head.get('op') == 'predicate'
             and head.get('iri') == REMEDY_IRI, 'records[57.1a].legalruleml.then',
             'the native obligation must express the immediate-remedy action')
    return record


def _explanation(data):
    record = _record(data, '24.3a')
    claimant = _role(record, 'claim_holder')
    counterparty = _role(record, 'duty_counterparty')
    _require(claimant in ('个人', '受自动化决定影响的个人', '受该决定影响的个人'),
             'records[24.3a].participants[claim_holder].label',
             '第24条第3款把请求说明的权利赋予个人')
    _require(counterparty == '个人信息处理者', 'records[24.3a].participants[duty_counterparty].label',
             'providing the explanation falls to the personal information processor')
    content = record.get('content_expr', {})
    _require(content.get('op') == 'action' and content.get('predicate') == '予以说明'
             and content.get('actor') == counterparty and content.get('recipient') in (claimant, '个人'),
             'records[24.3a].content_expr', 'the processor provides the explanation to the individual')
    _require(record['legalruleml'].get('native_element') == 'lrml:Right',
             'records[24.3a].legalruleml.native_element', 'the adopted projection is an individual Right')
    return record, claimant, counterparty


def validate_source(data):
    """Check the selected express timing and individual claim in the expanded source model."""
    _remedy(data)
    _explanation(data)


def _rule(root, record):
    path = f"records[{record['id']}].legalruleml.statement_key"
    rules = root.xpath('//lrml:PrescriptiveStatement[@key=$k]/ruleml:Rule', namespaces=NS,
                       k=record['legalruleml']['statement_key'])
    _require(len(rules) == 1, path, 'expected one XML prescriptive rule')
    return rules[0]


def validate_projection(data, xmlroot):
    """Verify that the formal immediate action and the two role bindings reach XML."""
    remedy = _remedy(data)
    rule = _rule(xmlroot, remedy)
    where = 'records[57.1a].legalruleml.then'
    heads = rule.xpath('ruleml:then/lrml:Obligation/ruleml:Atom', namespaces=NS)
    _require(len(heads) == 1 and heads[0].xpath('ruleml:Rel/@iri', namespaces=NS) == [REMEDY_IRI], where,
             'the XML action must preserve the explicit immediate remedy')
    expected_vars = [arg.get('var') for arg in remedy['legalruleml']['then']['args']]
    _require(heads[0].xpath('ruleml:Var/text()', namespaces=NS) == expected_vars, where,
             'XML immediate-remedy arguments disagree with the source mapping')

    claim, claimant, counterparty = _explanation(data)
    rule = _rule(xmlroot, claim)
    where = 'records[24.3a].participants / records[24.3a].legalruleml'
    roles = rule.xpath('ruleml:if//ruleml:Atom[ruleml:Rel/@iri=$iri]', namespaces=NS,
                       iri=PROJECTION+'claim_relationship_roles')
    rights = rule.xpath('ruleml:then/lrml:Right', namespaces=NS)
    _require(len(roles) == len(rights) == 1, where, 'missing XML right or its party-binding predicate')
    _require(roles[0].xpath('ruleml:Data/text()', namespaces=NS) == [claimant, counterparty],
             where, 'XML claim-role labels disagree with the claim holder and duty counterparty')
    variables = roles[0].xpath('ruleml:Var/text()', namespaces=NS)
    _require(len(variables) == len(set(variables)) == 2, where, 'two distinct party variables are required')
    for role, var in zip(('Bearer', 'AuxiliaryParty'), variables):
        _require(rights[0].xpath(f'ruleml:slot[lrml:{role}]/ruleml:Var/text()', namespaces=NS) == [var],
                 where, f'{role} binds the wrong party in the XML right')
    actions = rights[0].xpath('ruleml:Atom[ruleml:Rel/@iri=$iri]', namespaces=NS,
                              iri=PROJECTION+'exercise_right_text')
    _require(len(actions) == 1 and actions[0].xpath('ruleml:Var/text()', namespaces=NS) == variables
             and actions[0].xpath('ruleml:Data/text()', namespaces=NS)[:1] == ['请求说明'],
             'records[24.3a].content_expr / legalruleml', 'the XML right must be exercised to request the explanation')
