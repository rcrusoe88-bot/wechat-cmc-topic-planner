# 跨报告 DOI 唯一性

本规则保证论文型候选在历次选题报告中的 DOI 不重复。主题、读者角色、工艺环节或失效模式可以相同；DOI 是硬性身份键。

## 硬门槛

- 同行评审论文、综述、预印本和会议论文如果有 DOI，进入评分前必须通过 DOI 唯一性检查。
- 规范化 DOI 已出现在历史决策卡或本次候选批次中时，标记 `重复禁发`，不得进入关联度评分和最终选题池。
- 文献型候选缺少 DOI，且无法从论文页面、期刊页面或 Crossref 等可核验来源补齐时，只能作为背景，不得进入正式决策卡。
- 同一主题但 DOI 不同，允许进入评分；排重状态写为 `同主题新文献` 或 `可续写`，并说明新增证据或适用场景。主题命中本身不是禁发理由。
- 法规政策和专利不使用 DOI 检查，改用政策编号、专利公开号或其他稳定标识做排重，并在报告的数据范围中单独说明。

同一研究如果同时存在预印本 DOI 和正式发表 DOI，优先使用已核验的正式发表 DOI。若两个 DOI 指向同一版本或同一研究且被同时召回，编辑上只保留一个更可靠的来源；这不是基于主题的禁发。

## 台账

台账文件：

`reports/topics/doi-ledger.tsv`

台账由选题报告自动生成，不要手工维护。默认从所有选题报告的决策卡“来源信息”行提取 DOI，并记录首次出现的报告、日期和原始标题。

典型记录：

```text
doi	first_seen_report	first_seen_date	original_title
10.1021/acs.molpharmaceut.5c01450	2026-09-16-关联度筛选.md	2026-09-16	The Stealth Hazard...
```

## 每次选题的操作

开始扫描前：

```bash
python scripts/manage_doi_ledger.py sync --project-root <项目根目录>
```

候选进入完整评分前，对单个或批量 DOI 检查：

```bash
python scripts/manage_doi_ledger.py check --project-root <项目根目录> --doi "10.xxxx/yyyy"
python scripts/manage_doi_ledger.py check --project-root <项目根目录> --input-file candidate-dois.txt
```

检查结果中，只有 `allowed` 内的 DOI 可以继续评分。`blocked` 中的 DOI 必须在报告里明确列为历史重复并淘汰。

准备把候选写入决策卡前，对最终 DOI 列表再运行一次 `check --fail-on-duplicate`。任何 `blocked` DOI 都必须先从正式选题池删除；不得通过关联分、综合分或改写标题保留。

报告保存后再次运行：

```bash
python scripts/manage_doi_ledger.py sync --project-root <项目根目录>
```

这样本次决策卡中的新 DOI 会成为后续运行的排除项。迁移旧报告时如发现格式不统一，可使用 `sync --scope all` 从全部 Markdown 文本兜底提取 DOI；日常运行仍默认使用决策卡的“来源信息”行。

## 规范化

比较前统一执行：

- 去除 `https://doi.org/`、`http://dx.doi.org/` 和 `doi:` 前缀；
- 转为小写；
- 去除 Markdown 链接尾部和句末标点；
- 当 DOI 出现在 Markdown 链接中时，只保留 DOI 本身。

例如以下写法应视为同一 DOI：

```text
https://doi.org/10.1000/ABC.123
DOI: 10.1000/abc.123
[论文](https://doi.org/10.1000/abc.123)
```

## 置信与异常

- DOI 元数据与论文标题或日期明显冲突时，先回查论文页面，不凭标题猜测 DOI。
- 台账未命中只能说明“当前台账中没有该 DOI”，不能替代来源真实性、期刊状态或撤稿状态核验。
- 同一主题不同 DOI 不代表内容一定值得写；仍需通过决策句、关联度和综合选题分。
