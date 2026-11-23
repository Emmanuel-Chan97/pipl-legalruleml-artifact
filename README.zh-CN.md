# 《个人信息保护法》规范作用范围核验实验

这是六作者论文《从可编辑记录到 LegalRuleML：法律规范作用范围的核验》的配套实验材料。英文首页的 [论文证据索引](EVIDENCE.md) 将各项数据逐一对应到表1、表2、图1和图2。

**如果只想看懂一个案例，先看[第57条的实验 F02](examples/article57-waiver/README.md)。** 其中列出了修改前后的真实 JSON 记录以及直接修改 XML 时的差异。把“可以不通知个人”改指“通知部门”后，早期程序为什么仍然通过检查，可以用这两份材料分别核实。

| 想核查的问题 | 从这里开始 |
|---|---|
| 74条法条如何标注，哪些判断实际导出？ | [最终版可编辑模型](r3-final/PIPL-model.json)、[导出的 LegalRuleML](r3-final/PIPL-role-label.lrml)、[统计清单](supplement/replication/inventory.json)。下载后可双击打开 [view.html](r3-final/view.html)，选择同目录的 JSON 阅读。 |
| 标注者如何定位第57条的具体中文？ | [第57条 AKN 文件](supplement/anchor-example/art57.akn.xml)、[对应规则](supplement/anchor-example/art57.lrml)、[引文和字段的对应关系](supplement/anchor-example/source-and-fields.json)。AKN 样例覆盖第57条。 |
| 首次检出的 8/10 和复测的 10/10 分别对应哪些案例？ | [首次评估原始 CSV](supplement/round3/first_assessment.csv)、[修复后回归结果](supplement/round3/post_repair_regression.csv)、[修改每一项输入的代码](r3-final/experiments/paired_experiment.py)。每份 CSV 有26行数据，即同一组13项修改分别通过两个版本的程序。 |
| 第47条的18个情景是哪18个？ | [逐项情景表](examples/article47-scenarios.csv)、[对应检查代码](r3-final/qa/article47.py)。八个检验主动删除义务，三个检验个人的删除请求权，七个检验第二款处理限制。后七个在模型里检验；XML 端核对该项未导出。 |

## 在自己的电脑上复跑

解压后，在包含 `reproduce.py` 的目录中打开终端。macOS 或 Linux 使用以下命令：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reproduce.py --output replay
```

测试环境为 Python 3.12.4 和 lxml 6.1.3。Windows 可先运行 `py -3.12 -m venv .venv`，再将后两条命令开头的 `.venv/bin/python` 换为 `.venv\Scripts\python.exe`。安装依赖后，实验可以离线运行。

打开新生成的 `replay/verification.log` 即可查看核验记录。复跑程序在临时目录分别展开 R2、首次评估的 R3 和修复后的 R3，使用各自的输入运行。R2、首次评估的 R3、修复后的 R3 分别检出 0、8、10 项错误，均接受了三项保留原意的修改。10/10 是已知问题修复后对同一组案例的复测。表格中的预期结果来自作者的法条解读。

[r3-final/](r3-final/) 便于在线逐文件阅读，内容取自最终版本归档。根目录的复跑程序始终读取[三个冻结版本](supplement/round3/README.md)。如要在此基础上修改模型，可用 [r3-final 的说明](r3-final/README.md) 单独导出和检验新模型。
