# F02 / 第57条的通知豁免

第57条第2款的原文是“可以不通知个人”。在本文采用的解释中，措施能够有效避免危害时，处理者可以不通知个人；通知履行个人信息保护职责的部门仍是独立义务。F02 只把豁免指向的义务从通知个人（`57.1c`）改成了通知部门（`57.1b`），保留许可中写明的通知对象。可以对照[第57条原文的 AKN 标注](../../supplement/anchor-example/art57.akn.xml)。

## 查看实际修改

- [source-records.json](source-records.json) 摘取 R2 模型 `exceptions` 中的一条完整记录，并列出修改前后两个版本。运行归档实验的 `edit_source(..., "F02")` 后，唯一变化的字段是 `target_ids`。这些记录是实验输入的节选。
- [xml-target.diff](xml-target.diff) 展示另一次操作：在原本正确的 XML 文件中，直接修改 `Override` 的 `under` 属性。这里只摘录改动的元素。R2 从错误记录实际导出的文件保留了正确的 `#r-57-1c`。

| 修改位置 | 早期导出程序 R2 | 首次评估的 R3 | 修复后复测的 R3 |
| --- | --- | --- | --- |
| 修改可编辑记录 | 接受。导出文件与原文件逐字节相同，XSD、标识符和试点断言全部通过 | 拒绝，无 XML 输出 | 拒绝，无 XML 输出 |
| 直接修改正确的 XML | XSD 通过，标识符通过，试点断言检出错误 | 同左 | 同左 |

R2 从单独保存的试点声明读取优先关系。两种版本的 R3 都会在写文件前核对目标。每次比较所用的正确 XML 文件的 SHA-256 均为 `1c3389f64e8f0a9b20f79776e21ef056a20da7cf45eb8c268c279c9cfac42e8d`。R2 在修改可编辑记录后输出的文件也有这一指纹。

核对数值可在[首次评估结果](../../supplement/round3/first_assessment.csv)和[修复后结果](../../supplement/round3/post_repair_regression.csv)中筛选 `case=F02`。其中 `xsd`、`xml_refs` 和 `xml_pilot` 对应从可编辑记录导出的文件；`direct_xml_*` 对应直接改动的 XML。完整生成方法见[配对实验复现说明](../../supplement/round3/README.md)。
