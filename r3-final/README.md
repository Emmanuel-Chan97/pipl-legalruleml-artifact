# 《个人信息保护法》可复核标注模型 · 第三轮

编辑 `PIPL-model.json`。双击 `view.html`，选择同目录的 JSON，可以查看205条记录的原文、判定依据、角色、规范算子和中文展示分类。原生 LegalRuleML 交换文件为 `PIPL-role-label.lrml`。使用 Python 3 与 lxml 即可在本机导出、核验和复现实验。

## 三项改变

1. 导出器先检查可编辑的法律判断和试点公式，再核对实际生成的 XML。对第21条，它检查“返还或者删除”的连结词、动作参与者和独立的留存禁止。对第57条，它区分部门通知与个人通知、只针对个人通知的豁免，以及部门已经有效提出要求这一触发条件。输入错误时，诊断给出记录号和字段位置，保留上一次有效输出。
2. `rule_function` 记载规范的法律功能，`legalruleml.native_element` 记载所选原生构造，`legalruleml.status` 另记是否实际导出。中文展示类别集中在 `display_categories`。180条按本法的编辑规则生成，25条保留明确标签，其中20条是权能记录、5条是法定职责中的监管处置。原有九类均可逐条还原。第61条的履职义务和第66条的监管处置可以同时具有义务算子，又采用不同展示分类。
3. 第47条单独按中文法条设计测试预期。8个情境检查主动删除义务，3个检查应删除而尚未删除时个人的请求权，7个检查法定保存期或技术障碍下的其他处理限制。另有各分支和操作对象的检查。三条记录在 JSON 中受检，前两项另有 XML 投影，`47.2` 继续仅在项目数据中表示。解释适用的是本项目明确列出的事实和中文谓词，没有进行专家盲评。

## 导出和验证

```shell
python3 exporter/export_native.py PIPL-model.json current.lrml
python3 verify.py
python3 migrate.py to-r2 PIPL-model.json round2.json
python3 migrate.py to-r1 PIPL-model.json round1.json
python3 migrate.py expand PIPL-model.json expanded.json
```

输入可以是本版、第一轮、第二轮或旧版完整模型。完整脚本核对旧数据、来源锚点、XML 字节和 OASIS Compact XSD，并在临时文件中注入错误后调用正常导出入口。`verify.py` 的快照指纹针对本次发布。若有意修改某条法律判断，须分别讨论来源依据、改变的规则条件和是否要修订对应检查。既有试点接受已绑定词汇和指定结构，不等同于任意中文释义的自动验证器。

## 首次结果与事后修复

预先列定13项探针，含10项改变法律含义的编辑和3项有效对照修改。每个输入均在新副本上编辑，再调用对应版本的正常导出器，记录接受或拒绝、XML 是否与原来相同，以及实际生成的 XML 能否通过结构与试点检查。

| 版本与时点 | 10项错误中拦截 | 3项有效修改中接受 |
|---|---:|---:|
| 第二轮 | 0 | 3 |
| 第三轮首次测试 | 8 | 3 |
| 两处漏检修复后的同组回归 | 10 | 3 |

首次漏检为 F09（把第57条“立即”从补救移到仅通知部门）和 F10（把第24条请求说明的权利人从个人改成处理者）。前者在第二轮及第三轮首次导出时 XML 完全未动，后者改变了 XML，但 XML 侧的原有检查仍通过。为成品补充的 `qa/post_challenge.py` 在可编辑数据与投影两端检查这两种情况。最后一行记录已知问题修复结果。13项均为目的性选取的挑战样本，不代表整部法律的语义准确率。

`experiments/first_assessment.csv` 和 `experiments/post_repair_regression.csv` 保存两次逐项配对结果，`experiments/snapshots/` 保存当时使用的两个归档版本。解压两个快照至空目录后，可复现两次实验。

```shell
python3 -m zipfile -e experiments/snapshots/R2.zip /tmp/pipl-test-r2
python3 -m zipfile -e experiments/snapshots/R3-first-assessment.zip /tmp/pipl-test-r3-frozen
python3 experiments/paired_experiment.py --r2-root /tmp/pipl-test-r2 --r3-root /tmp/pipl-test-r3-frozen --output first.csv
python3 experiments/paired_experiment.py --r2-root /tmp/pipl-test-r2 --r3-root . --output after.csv
```

研究方法区分编辑模型与 XML 结果、来源片段与字段判断、检查复现性与法律解释正当性。122条记录生成124条原生规范语句，其余83条留在项目数据层。第66条的八条记录均留在项目数据层。

[《中华人民共和国个人信息保护法》](https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm) · [OASIS LegalRuleML Core Specification 1.0](https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/legalruleml-core-spec-v1.0-os.html)
