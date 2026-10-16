# Prompt 迭代记录（面试铁证文档）

> 每次调 prompt 前后各存一版 + 改了什么 + 效果变化。从 D2 开始记。
> 面试话术：这是 prompt 工程的迭代日志，每次修改都有对应的输出变化证据。

## Agent 1 · 解析器

### v1 · 2026-10-16（D2 初版）

**背景**：D1 骨架的 prompt 只给了 JSON 骨架，没有分段规则。

**Prompt 要点**：
- 给出四段结构：education / experience / skills / projects
- 未约束 null vs 空数组，未约束量化数字保留

**已知问题**（待 D2 真机验证后迭代）：
1. 家教类经历 company 字段写什么不明确（"一对一辅导（科目）"格式是 v1 就定的）
2. 无 "只输出 JSON，不要 markdown 代码块" 约束时，DeepSeek 偶尔包 ```json 围栏导致解析失败
3. 双栏简历的段落顺序错乱（pdfplumber 按 x 坐标逐行提取，左右栏交错）——已加双栏检测警告，解析 prompt 层面的修复待验证

### v2 · 2026-10-16（D2 做实版）

**改动**：
1. 明确 "一个对象，不要数组包裹"
2. 明确 "简历中找不到的字段给空数组，不要输出 null"
3. 明确 "保留原文数字（分数、课时、年限），不得编造"
4. 明确归属规则：家教/实习/工作都归入 experience
5. 加 "只输出 JSON，不要任何解释或 markdown 代码块"

**机制**（非 prompt，但同属解析可靠性）：
- Pydantic `ResumeStructured` 校验，失败把 ValidationError 喂回 LLM 自纠，最多重试 2 次
- `chat_json` 层面：JSON 解析失败自动重试 1 次（D1 已有）

**效果**：待 DEEPSEEK_API_KEY 配置后，用 `tests/fixtures/my_resume.pdf` 实测记录。
