# wechat-cmc-topic-planner

面向“信使引擎”公众号的 mRNA CMC 选题策划 Skill。它从论文、专利和监管政策中发现候选选题，按 mRNA CMC 与 LNP 递送双轴评分，并维护跨报告的文献 DOI 台账。

核心规则：

- 论文型候选的 DOI 必须跨报告唯一；已出现过的 DOI 直接淘汰。
- 主题、读者角色、工艺环节和失效模式允许重复。
- 同一主题只有换用不同 DOI 的新文献时，才进入新的选题评估。
- 法规政策和专利使用政策编号、专利公开号等稳定标识排重。

## 安装

在 Codex 中调用 `$skill-installer`，并提供以下 GitHub 目录：

```text
https://github.com/rcrusoe88-bot/wechat-cmc-topic-planner/tree/main/skills/wechat-cmc-topic-planner
```

例如：

```text
$skill-installer 请从 https://github.com/rcrusoe88-bot/wechat-cmc-topic-planner/tree/main/skills/wechat-cmc-topic-planner 安装这个技能
```

也可以手动把 `skills/wechat-cmc-topic-planner/` 复制到 `$CODEX_HOME/skills/`，未设置 `CODEX_HOME` 时默认目录为 `~/.codex/skills/`。

## 使用

该 Skill 默认关闭隐式调用，需要显式调用：

```text
$wechat-cmc-topic-planner 帮我扫描最近的 mRNA CMC 选题，按规则执行跨报告 DOI 去重。
```

首次在目标项目使用时，Skill 会从项目根目录的 `reports/topics/` 读取历史选题报告，并生成或更新：

```text
reports/topics/doi-ledger.tsv
```

台账属于项目数据，不随 Skill 仓库发布。请在每个实际使用该 Skill 的内容项目中保留自己的 `reports/topics/` 和 DOI 台账。

## 工具

目录内脚本仅使用 Python 标准库，需要 Python 3.10 或更高版本。

```text
scripts/manage_doi_ledger.py    同步和检查跨报告 DOI 台账
scripts/calculate_relevance.py  计算双轴关联分和默认动作
```

## 内容结构

```text
skills/wechat-cmc-topic-planner/
|-- SKILL.md
|-- agents/
|   `-- openai.yaml
|-- references/
|   |-- account-profile.md
|   |-- calibration-cases.md
|   |-- content-baseline.md
|   |-- doi-dedup.md
|   |-- relevance-scoring.md
|   `-- topic-scoring.md
`-- scripts/
    |-- calculate_relevance.py
    `-- manage_doi_ledger.py
```

## 许可证

MIT License
