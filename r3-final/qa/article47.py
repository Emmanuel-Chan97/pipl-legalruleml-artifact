"""Independent, text-based expectations for the Chinese PIPL Article 47 profile.

Authority: 2021-08-20 PIPL, art. 47, https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm
These judgments concern Article 47 under its stated conditions. They are not
general permissions for other purposes, and do not determine when a particular
real-world technology makes deletion difficult.
"""
# Five alternative grounds are written in art. 47(1)(1)-(5).
GROUNDS = (
    'purpose_achieved_impossible_or_no_longer_necessary',
    'service_ended_or_period_expired',
    'consent_withdrawn',
    'processing_in_breach_of_law_regulation_or_agreement',
    'other_legally_specified_ground',
)
# An identified deletion ground suffices to trigger the proactive duty under
# paragraph 1, without first exercising the request right. For these scenarios
# paragraph 2's obstacles are absent. Exercising the right differs from holding it.
# field, active ground(s), has individual requested already?, not yet deleted?, expected
PROACTIVE_CASES = (
    [(f'ground_{i+1}_without_request', {ground}, False, True, True)
     for i, ground in enumerate(GROUNDS)]
    + [('no_ground', set(), False, True, False),
       ('request_alone', set(), True, True, False),
       ('ground_with_request', {GROUNDS[2]}, True, True, True)]
)
CLAIM_CASES = (
    ('due_but_not_deleted', {GROUNDS[2]}, False, True, True),
    ('due_and_already_deleted', {GROUNDS[2]}, False, False, False),
    ('no_ground_and_not_deleted', set(), False, True, False),
)
# Test the duty to stop other processing with a deletion ground established.
# statutory period still running, technical difficulty, targeted action, must stop?
RESTRICTION_CASES = (
    (True, False, 'other_processing', True),
    (False, True, 'other_processing', True),
    (True, True, 'other_processing', True),
    (False, False, 'other_processing', False),
    (True, False, 'storage', False),
    (False, True, 'necessary_security', False),
    (True, False, 'nonessential_security', True),
)

# Adapter for this corpus's controlled Chinese leaves. A proposition belongs
# to a statutory group even when this profile represents several facts in one
# Chinese predicate. Different textual formulations need an explicit mapping.
GROUP_MEMBERS = {
    GROUNDS[0]: ('purpose_achieved', 'purpose_impossible', 'purpose_unnecessary'),
    GROUNDS[1]: ('service_ended', 'period_expired'),
    GROUNDS[2]: ('consent_withdrawn',),
    GROUNDS[3]: ('breach_of_law', 'breach_of_regulation', 'breach_of_agreement'),
    GROUNDS[4]: ('other_statutory_ground',),
}
LEAVES = {
    '处理目的已实现': ('purpose_achieved',),
    '处理目的无法实现': ('purpose_impossible',),
    '为实现目的已不再必要': ('purpose_unnecessary',),
    '处理者停止提供产品或者服务': ('service_ended',),
    '保存期限已届满': ('period_expired',),
    '个人撤回同意': ('consent_withdrawn',),
    '处理违反法律、行政法规': ('breach_of_law', 'breach_of_regulation'),
    '处理违反约定': ('breach_of_agreement',),
    '法律、行政法规规定其他删除情形': ('other_statutory_ground',),
    '处理者尚未删除': ('not_yet_deleted',),
    '法定保存期限未届满': ('statutory_period_running',),
    '从技术上难以删除': ('technical_difficulty',),
    '个人提出请求': ('request',),
    '个人提出删除请求': ('request',),
    '个人请求删除': ('request',),
}
OPERATORS = {'47.1a': 'Obligation', '47.1b': 'Right', '47.2': 'Prohibition'}
EXPECTED_ROLES = {
    '47.1a': {'obligor': '个人信息处理者'},
    '47.1b': {'claim_holder': '个人', 'duty_counterparty': '个人信息处理者'},
    '47.2': {'obligor': '个人信息处理者'},
}
NS = {'r': 'http://ruleml.org/spec', 'l': 'http://docs.oasis-open.org/legalruleml/ns/v1.0/'}
VOCAB = 'urn:pipl:projection:'


def require(ok, path, problem):
    if not ok:
        raise ValueError(f'{path}: {problem}')


def compile_guard(expr, path):
    """Interpret supported predicates and Boolean connectives; fail on unknown wording."""
    op = expr.get('op') if isinstance(expr, dict) else None
    if op == 'predicate':
        text = expr.get('text')
        require(text in LEAVES, path, f'未识别的第47条事实谓词 {text!r}，无法核验该条件')
        options = set(LEAVES[text])
        return lambda facts: not options.isdisjoint(facts)
    require(op in ('all', 'any', 'not') and expr.get('args'), path,
            'expected a nonempty Boolean condition or a known fact')
    children = [compile_guard(child, path) for child in expr['args']]
    if op == 'not':
        require(len(children) == 1, path, 'negation must have one operand')
        return lambda facts: not children[0](facts)
    combine = all if op == 'all' else any
    return lambda facts: combine(child(facts) for child in children)


def must_stop_scope(predicate, obj, path):
    """Read the restricted action vocabulary of 47.2; only scope under that norm."""
    require(predicate == '继续处理' and isinstance(obj, str), path,
            'expected a prohibition on continuing processing')
    if obj in ('全部个人信息处理活动', '所有个人信息处理活动', '所有处理活动', '全部处理活动'):
        return lambda action: True
    prefix = obj.removeprefix('除')
    suffix = next((s for s in ('之外的个人信息处理活动', '以外的个人信息处理活动') if prefix.endswith(s)), None)
    require(suffix is not None, path, f'无法核验停止处理的范围 {obj!r}；须能识别存储和必要安全保护措施')
    names = {'存储': 'storage', '采取必要安全保护措施': 'necessary_security',
             '采取必要的安全保护措施': 'necessary_security',
             '采取安全保护措施': 'all_security'}
    exceptions = prefix[:-len(suffix)].split('和')
    require(all(label in names for label in exceptions), path,
            f'未识别的处理排除项 {exceptions!r}，须复核保护范围')
    exempt = {names[label] for label in exceptions}
    if 'all_security' in exempt:
        exempt.update(('necessary_security', 'nonessential_security'))
    return lambda action: action not in exempt


def test_activation(record_id, guard, path):
    if record_id == '47.2':
        return
    checks = PROACTIVE_CASES if record_id == '47.1a' else CLAIM_CASES
    for name, groups, requested, unfulfilled, expected in checks:
        facts = {GROUP_MEMBERS[group][0] for group in groups}
        if requested:
            facts.add('request')
        if unfulfilled:
            facts.add('not_yet_deleted')
        require(guard(facts) == expected, path, f'Article 47 scenario {name}: expected {expected}')
    for alternatives in GROUP_MEMBERS.values():
        for fact in alternatives:
            facts = {fact} if record_id == '47.1a' else {fact, 'not_yet_deleted'}
            require(guard(facts), path, f'Article 47 single-ground scenario {fact} failed')


def test_restriction(guard, in_scope, base, path_suffix_1, path_suffix_2):
    # Limited to the project's art.47(1) deletion-ground background.
    for running, difficult, action, expected in RESTRICTION_CASES:
        facts = {'consent_withdrawn'}
        if running:
            facts.add('statutory_period_running')
        if difficult:
            facts.add('technical_difficulty')
        require(guard(facts) == (running or difficult), base + path_suffix_1,
                f'restriction trigger mismatch: statutory period running={running}, technical difficulty={difficult}')
        require((guard(facts) and in_scope(action)) == expected, base + path_suffix_2,
                f'Article 47(2) scope mismatch for {action}: must stop={expected}')


def validate_source(data):
    """Check structured values/roles, not paraphrases, cited text, hashes or XML output."""
    by_id = {r['id']: r for r in data['records']}
    for ident, operator in OPERATORS.items():
        require(ident in by_id, ident, 'missing Article 47 record')
        record = by_id[ident]
        require(record['legalruleml'].get('native_element') == 'lrml:' + operator,
                ident + '.legalruleml.native_element', f'expected {operator}')
        for role, who in EXPECTED_ROLES[ident].items():
            require(any(p.get('role') == role and p.get('label') == who for p in record['participants']),
                    ident + '.participants', f'expected {role} for {who}')
        guard = compile_guard(record.get('activation'), ident + '.activation')
        content = record['content_expr']
        require(content.get('op') == 'action', ident + '.content_expr', 'expected one action')
        if ident == '47.2':
            stop = must_stop_scope(content.get('predicate'), content.get('object'), '47.2.content_expr')
            test_restriction(guard, stop, ident, '.activation', '.content_expr')
        else:
            predicate = '主动删除' if ident == '47.1a' else '请求删除'
            require(content.get('predicate') == predicate, ident + '.content_expr', f'expected {predicate}')
            test_activation(ident, guard, ident + '.activation')
    exception = next((e for e in data['exceptions'] if e['id'] == 'E47-DELETION-LIMIT'), None)
    require(exception is not None and exception.get('target_ids') == ['47.1a'],
            'E47-DELETION-LIMIT.target_ids', 'limitation must address the ordinary deletion requirement')
    obstacle = compile_guard(exception['condition'], 'E47-DELETION-LIMIT.condition')
    for facts, expected in ((set(), False), ({'statutory_period_running'}, True),
                            ({'technical_difficulty'}, True),
                            ({'statutory_period_running', 'technical_difficulty'}, True)):
        require(obstacle(facts) == expected, 'E47-DELETION-LIMIT.condition',
                f'wrong obstacle condition for {sorted(facts)}')


def xml_guard(node, path):
    from lxml import etree
    tag = etree.QName(node)
    require(tag.namespace == NS['r'], path, 'expected RuleML condition')
    if tag.localname == 'Atom':
        require(node.xpath('./r:Rel/@iri', namespaces=NS) == [VOCAB + 'condition_text'],
                path, 'unexpected condition predicate')
        values = node.xpath('./r:Data/text()', namespaces=NS)
        require(len(values) == 1, path, 'expected one fact argument')
        return {'op': 'predicate', 'text': values[0]}
    kinds = {'And': 'all', 'Or': 'any', 'Neg': 'not'}
    require(tag.localname in kinds, path, f'unknown condition type {tag.localname}')
    return {'op': kinds[tag.localname], 'args': [xml_guard(child, path) for child in node]}


def validate_projection(data, root):
    """Verify what is actually projected. A retained 47.2 has no XML restriction claim."""
    records = {r['id']: r for r in data['records']}
    for ident, mode in OPERATORS.items():
        key = 'r-' + ident.replace('.', '-')
        path = 'XML ' + ident
        nodes = root.xpath('//l:PrescriptiveStatement[@key=$key]', key=key, namespaces=NS)
        if ident == '47.2' and records[ident]['legalruleml'].get('status') == 'retained':
            require(not nodes, path, 'local-only restriction unexpectedly emitted')
            continue
        require(len(nodes) == 1, path, 'missing or duplicate prescription')
        s = nodes[0]
        heads = s.xpath('./r:Rule/r:then/*', namespaces=NS)
        require(len(heads) == 1 and heads[0].tag == '{'+NS['l']+'}'+mode,
                path + '.operator', f'expected {mode}')
        branches = s.xpath('./r:Rule/r:if/r:And/*', namespaces=NS)
        activation_key = ':' + key + '-activation'
        active = [branch for branch in branches if branch.get('key') == activation_key]
        require(len(active) == 1, path + '.activation', 'missing primary source condition')
        auxiliary = [b for b in branches if b.get('key') != activation_key]
        guards = []
        for atom in auxiliary:
            iris = atom.xpath('./r:Rel/@iri', namespaces=NS)
            require(len(iris) == 1 and iris[0].startswith(VOCAB), path + '.activation', 'unexpected extra guard')
            guards.append((iris[0][len(VOCAB):], atom.xpath('./r:Data/text()', namespaces=NS)))
        expected = {'scope_text', 'claim_relationship_roles' if ident == '47.1b' else 'has_bearer_role'}
        if ident == '47.1a':
            expected.add('exception_does_not_apply')
            require(('exception_does_not_apply', ['E47-DELETION-LIMIT', ident]) in guards,
                    path + '.activation', 'missing matching deletion limitation guard')
        require(len(guards) == len(expected) and {name for name, _ in guards} == expected,
                path + '.activation', 'missing or additional legal prerequisite')
        guard = compile_guard(xml_guard(active[0], path + '.activation'), path + '.activation')
        values = heads[0].xpath('./r:Atom/r:Data/text()', namespaces=NS)
        if ident == '47.2':
            require(len(values) == 2, path + '.content_expr', 'expected scope and action')
            stop = must_stop_scope(*values, path + '.content_expr')
            test_restriction(guard, stop, path, '.activation', '.content_expr')
        else:
            predicate = '主动删除' if ident == '47.1a' else '请求删除'
            require(len(values) == 2 and values[0] == predicate, path + '.content_expr', f'expected {predicate}')
            test_activation(ident, guard, path + '.activation')
