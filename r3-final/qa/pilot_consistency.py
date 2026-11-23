"""Cross-check the source fields and exchange formulas for the Article 21/57 pilots."""
from lxml import etree


LRML = 'http://docs.oasis-open.org/legalruleml/ns/v1.0/'
RULEML = 'http://ruleml.org/spec'
NS = {'lrml': LRML, 'ruleml': RULEML}
PRED = 'urn:pipl-pilot:predicate:'
WAIVER = 'E57-PERSON-WAIVER'


def require(test, path, message):
    if not test:
        raise ValueError(f'{path}: {message}')


def atom(predicate, *variables):
    return ('predicate', PRED + predicate, tuple(variables))


def branch(op, operands):
    # And/Or commute, but duplicating, omitting and negating an operand matter here.
    return (op, tuple(sorted(operands)) if op in ('all', 'any') else tuple(operands))


def json_formula(expr, path):
    require(isinstance(expr, dict), path, 'expected a formula')
    op = expr.get('op')
    args = expr.get('args')
    require(isinstance(args, list), path, 'expected a list of operands')
    if op == 'predicate':
        require(isinstance(expr.get('iri'), str) and all(isinstance(v, dict) and
                isinstance(v.get('var'), str) for v in args), path, 'expected a named pilot predicate and variables')
        return (op, expr['iri'], tuple(v['var'] for v in args))
    require(op in ('all', 'any', 'not') and args and (op != 'not' or len(args) == 1),
            path, 'unsupported Boolean connective or arity')
    return branch(op, [json_formula(child, path) for child in args])


def _lookup(rows, path):
    table = {}
    for item in rows:
        key = item.get('id')
        require(key and key not in table, path, f'missing or duplicate id {key}')
        table[key] = item
    return table


def _head(record, native, expected):
    path = f"records[{record['id']}].legalruleml"
    mapping = record.get('legalruleml', {})
    require(mapping.get('native_element') == 'lrml:' + native,
            path + '.native_element', f'expected lrml:{native}')
    require(json_formula(mapping.get('then'), path + '.then') == expected, path + '.then',
            'predicate, binding or connective contradicts the normative content in the pilot')


def _retention(records):
    record = records['21.2c']
    expr = record.get('content_expr', {})
    path = 'records[21.2c].content_expr'
    require(expr.get('op') == 'any', path + '.op', '返还与删除是择一义务，预期 any')
    operations = {'返还': atom('return_personal_information', 'Entrusted', 'Controller', 'Data'),
                  '删除': atom('delete_personal_information', 'Entrusted', 'Data')}
    args = expr.get('args', [])
    require(len(args) == 2 and {arg.get('predicate') for arg in args} == set(operations),
            path + '.args', 'expected one return action and one deletion action')
    for index, arg in enumerate(args):
        edge = f'{path}.args[{index}]'
        require(arg.get('op') == 'action' and arg.get('actor') == '受托人' and
                arg.get('object') == '受托处理的个人信息', edge,
                'the entrusted party disposes of the entrusted personal information')
        if arg['predicate'] == '返还':
            require(arg.get('recipient') == '委托处理者', edge + '.recipient',
                    'the return is directed to the entrusting controller')
    _head(record, 'Obligation', branch(expr['op'], [operations[arg['predicate']] for arg in args]))
    keep = records['21.2d']
    require(keep['content_expr'].get('op') == 'action' and keep['content_expr'].get('predicate') == '保留',
            'records[21.2d].content_expr', 'the separate prohibition concerns retention')
    _head(keep, 'Prohibition', atom('retain_personal_information', 'Entrusted', 'Data'))


def _effect(record, kind):
    path = f"records[{record['id']}].effects"
    found = [(index, effect) for index, effect in enumerate(record['effects']) if effect.get('type') == kind]
    require(len(found) == 1, path, f'expected one effect typed {kind}')
    index, effect = found[0]
    return f'{path}[{index}]', effect


def _notification(data, records):
    exceptions = _lookup(data['exceptions'], 'exceptions')
    require(WAIVER in exceptions, 'exceptions', f'missing {WAIVER}')
    waiver = exceptions[WAIVER]
    ep = f'exceptions[{WAIVER}]'
    require(waiver.get('target_ids') == ['57.1c'], ep + '.target_ids',
            '个人通知豁免只作用于 57.1c；部门通知义务与补救义务独立')
    require(waiver.get('permission_record_id') == '57.2a', ep + '.permission_record_id',
            'the personal-notification waiver belongs to 57.2a')
    scope = records['57.2a']
    why, effect = _effect(scope, 'exempts')
    require(effect.get('target_ids') == waiver['target_ids'], why + '.target_ids',
            f'must agree with {ep}.target_ids')
    require(effect.get('condition') == waiver.get('condition') == scope.get('activation'),
            f'{why}.condition / {ep}.condition / records[57.2a].activation',
            'the same harm-prevention condition must govern the waiver and its effect')
    notify = atom('notify_person', 'Controller', 'Person', 'Event')
    require(scope['content_expr'].get('recipient') == records['57.1c']['content_expr'].get('recipient')
            == '受影响的个人', 'records[57.2a].content_expr.recipient / records[57.1c].content_expr.recipient',
            'the omitted act is notification of the affected person')
    for key, action in (('57.1b', '通知'), ('57.1c', '通知'), ('57.2a', '省略通知'),
                        ('57.2c', '按有效要求通知')):
        record = records[key]
        expression = record['content_expr']
        require(expression.get('op') == 'action' and expression.get('predicate') == action,
                f'records[{key}].content_expr.predicate', 'the declared notification action or its polarity differs')
        place = '履行个人信息保护职责的部门' if key == '57.1b' else '受影响的个人'
        require(expression.get('recipient') == place, f'records[{key}].content_expr.recipient',
                'notification recipient differs from the pilot predicate binding')
        recipients = [p['label'] for p in record['participants'] if p['role'] == 'recipient']
        if key != '57.2a' or recipients:
            require(recipients == [place], f'records[{key}].participants[role=recipient]',
                    'declared recipient disagrees with the affected person or competent department')
    _head(records['57.1b'], 'Obligation', atom('notify_department', 'Controller', 'Department', 'Event'))
    _head(records['57.1c'], 'Obligation', notify)
    _head(scope, 'Permission', branch('not', [notify]))

    power, duty = records['57.2b'], records['57.2c']
    require(power.get('rule_function') == 'competence', 'records[57.2b].rule_function',
            'this record grants the power to order notification')
    effect_path, exercise = _effect(power, 'requires_valid_exercise')
    require(exercise.get('target_ids') == [duty['id']], effect_path + '.target_ids',
            'exercise of the power activates the separate 57.2c duty')
    # These are the controlled descriptions used by this pilot, not a classifier for Chinese prose.
    exercise_descriptions = {'履职部门依法有效要求通知个人', '履职部门已有效要求处理者通知个人'}
    for predicate, path in ((exercise.get('condition'), effect_path + '.condition'),
                            (duty.get('activation'), 'records[57.2c].activation')):
        require(isinstance(predicate, dict) and predicate.get('op') == 'predicate' and
                predicate.get('text') in exercise_descriptions, path,
                'expected the pilot predicate for a validly issued notice order; having the power alone is insufficient')
    require(duty['content_expr'].get('recipient') == scope['content_expr'].get('recipient'),
            'records[57.2c].content_expr.recipient', 'the valid order directs notice to the affected person')
    _head(duty, 'Obligation', notify)
    guard_path = 'records[57.2c].legalruleml.if'
    guard = json_formula(duty['legalruleml'].get('if'), guard_path)
    valid_order = atom('valid_notice_order', 'Department', 'Controller', 'Person', 'Event')
    require(guard[0] == 'all' and valid_order in guard[1], guard_path,
            'valid_notice_order with the correct parties must be a required conjunct of the triggered duty')

    priorities = data['interchange']['priorities']
    priority_targets = {rule: [item['under'] for item in priorities if item['over'] == rule]
                        for rule in ('57.2a', '57.2c')}
    require(priority_targets[scope['id']] == waiver['target_ids'], 'interchange.priorities[over=57.2a].under',
            f'expected the ordinary personal-notification target from {ep}.target_ids')
    require(priority_targets[duty['id']] == [scope['id']], 'interchange.priorities[over=57.2c].under',
            'this pilot gives the valid-order duty priority over the waiver')


def check_pilot_source(data):
    """Validate the expanded input before export. Report model paths instead of file digests."""
    records = _lookup(data['records'], 'records')
    for key in ('21.2c', '21.2d', '57.1b', '57.1c', '57.2a', '57.2b', '57.2c'):
        require(key in records, f'records[{key}]', 'required Article 21/57 pilot statement is missing')
    _retention(records)
    _notification(data, records)


def _xml_formula(element, path):
    tag = etree.QName(element)
    require(tag.namespace == RULEML, path, 'expected RuleML formula')
    if tag.localname == 'Atom':
        relation = element.find('ruleml:Rel', NS)
        require(relation is not None and relation.get('iri'), path, 'expected a named predicate')
        variables = [child.text for child in element if child is not relation]
        require(all(child.tag == f'{{{RULEML}}}Var' for child in element if child is not relation),
                path, 'expected pilot variables')
        return ('predicate', relation.get('iri'), tuple(variables))
    ops = {'And': 'all', 'Or': 'any', 'Neg': 'not'}
    require(tag.localname in ops, path, f'unrecognized formula {tag.localname}')
    return branch(ops[tag.localname], [_xml_formula(child, path) for child in element])


def check_pilot_projection(data, xmlroot):
    """Compare the six exported pilot heads, their guards, and the two scoped priorities."""
    records = _lookup(data['records'], 'records')
    for key in ('21.2c', '21.2d', '57.1b', '57.1c', '57.2a', '57.2c'):
        mapping = records[key]['legalruleml']
        path = f'records[{key}].legalruleml'
        rules = xmlroot.xpath('//lrml:PrescriptiveStatement[@key=$key]/ruleml:Rule',
                              key=mapping['statement_key'], namespaces=NS)
        require(len(rules) == 1, path + '.statement_key', 'missing or duplicate exported rule')
        guard = rules[0].xpath('ruleml:if/*', namespaces=NS)
        head = rules[0].xpath('ruleml:then/*', namespaces=NS)
        native = mapping['native_element'].split(':', 1)[1]
        require(len(head) == 1 and head[0].tag == f'{{{LRML}}}{native}',
                path + '.native_element', 'XML deontic operator differs')
        content = [child for child in head[0] if child.tag != f'{{{RULEML}}}slot']
        for field, nodes in (('if', guard), ('then', content)):
            where = f'{path}.{field}'
            require(len(nodes) == 1 and _xml_formula(nodes[0], where) == json_formula(mapping[field], where),
                    where, 'XML formula differs from the source expression')
    for over in ('57.2a', '57.2c'):
        expected = [records[p['under']]['legalruleml']['statement_key'] for p in data['interchange']['priorities']
                    if p['over'] == over]
        actual = xmlroot.xpath('//lrml:Override[@over=$key]/@under',
                               key='#' + records[over]['legalruleml']['statement_key'], namespaces=NS)
        require(actual == ['#' + key for key in expected], f'interchange.priorities[over={over}].under',
                'exported priority has a different target')
