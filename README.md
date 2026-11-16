# academic_core 2.0: 解耦型通用学术文献数字化与全格式出版引擎

`academic_core` 是一个高内聚、零强耦合、高拓展性的通用学术文献与板书数字化处理框架。
其核心架构严格遵循“**输入格式归一化 -> 视觉/文本提取 -> 学术大模型推理 -> LaTeX 语法自愈 -> 多格式出版级交付 -> 专著合订**”的标准六阶流水线，彻底将物理输入格式、视觉引擎与大模型后端解耦。

---

## 🏗️ 七大解耦子系统架构图

```mermaid
flowchart TD
    subgraph IN[输入介质归一化 (Converters)]
        A1[".one 笔记"] --> N[NormalizedDocument]
        A2[".docx 文档"] --> N
        A3[".pptx 课件"] --> N
        A4[".pdf 扫描/数字"] --> N
        A5[".tex / .md / .txt"] --> N
        A6["黑板拍照包 / 手机连拍"] --> N
        A7[".zip / .tar 压缩包"] --> N
    end

    subgraph ENG[提取与视觉 OCR 矩阵 (Vision OCR)]
        N -->|纯文本/原生数字| TEXT[零开销纯文本直通]
        N -->|图像/手写扫描| OCR[视觉与 OCR 引擎矩阵]
        OCR --> QWEN[Qwen-VL-OCR]
        OCR --> OAI[OpenAI / GPT-4o / vLLM]
        OCR --> GEM[Google Gemini Vision]
        OCR --> MOCK[Mock 零 Token 本地测试]
    end

    subgraph LLM[学术语义自愈中枢 (LLM Reasoning)]
        TEXT --> L_ENG[学术推理引擎]
        QWEN --> L_ENG
        OAI --> L_ENG
        GEM --> L_ENG
        MOCK --> L_ENG
        L_ENG --> TASK1[note 板书讲义自愈]
        L_ENG --> TASK2[textbook 教材精译]
        L_ENG --> TASK3[paper 论文翻译与双语]
    end

    subgraph MATH[数学公式语法自愈 (Math Enhancer)]
        TASK1 --> L_FIX[LatexCleaner 语法自愈]
        TASK2 --> L_FIX
        TASK3 --> L_FIX
        L_FIX -.->|标点外移/环境修复/未闭合补全| HEALED[纯净学术 Markdown]
    end

    subgraph OUT[多格式出版级交付 (Exporters)]
        HEALED --> EXP_PDF["出版级矢量 A4 PDF (Chrome/动态页码)"]
        HEALED --> EXP_HTML["自包含独立 HTML (KaTeX/响应式)"]
        HEALED --> EXP_MD["规范化 Markdown (YAML Frontmatter)"]
        EXP_PDF --> BIND["专著大合订本 (MonographBinder 全局大目录)"]
    end
```

---

## 🌟 核心特性亮点

1. **输入介质全景覆盖 (Universal Converters)**：
   - 彻底摆脱对单一工具的依赖，原生支持 `.one`, `.docx`, `.pptx`, `.pdf`, `.md`, `.tex`, `.txt`, `.html`, 手机拍照连拍包及 `.zip`/`.tar` 压缩包。
   - `.docx` 与 `.pptx` 具备标准库（ZIP + XML）解析引擎，无第三方库依赖亦可毫秒级提取。
   - PDF 具备 **Dual-Mode 双模式**：数字 PDF 零开销直提纯文本；扫描件与板书高精度矢量切片（200-300 DPI）。
   - 手机拍照支持 **EXIF 重力自适应正立** 与粉笔/浅铅笔**弱字迹对比度自适应增强**。

2. **可插拔视觉 OCR 矩阵 (Vision Engine Matrix)**：
   - 支持 `qwen-vl-ocr` / `qwen-vl-max`（中文板书推导天花板）。
   - 支持 `gpt-4o` / `gpt-4o-mini` 及兼容 OpenAI 规范的本地私有化模型（vLLM / Ollama）。
   - 支持 `gemini-1.5-pro` / `gemini-1.5-flash`。
   - 内置 `mock` 引擎，实现毫秒级、零 Token 消耗的本地自动化回归测试。
   - 内置图像 MD5 页面级磁盘缓存，二次运行 **0 消耗**。

3. **数学排版语法自愈引擎 (Math & LaTeX Enhancer)**：
   - 自动识别并剥离行内公式首尾的中文标点（如 `$f(x)，$` 自动自愈为 `$f(x)$，`）。
   - 自动转换顶级 `\begin{align}` 为 KaTeX 规范的 `\begin{aligned}`。
   - 自动消除中文字符与 LaTeX 命令的粘连（如 `\alpha与\beta` -> `\alpha` 与 `\beta`）。
   - 自动缝合 OCR 产生的脱节上下标（如 `a_ 1` -> `a_1`, `x^ 2` -> `x^2`）。
   - 自动扫描并平衡闭合未闭合的 `\left( ... )`。

4. **全格式出版级交付 (Multi-Format Exporters)**：
   - **矢量 PDF**：Chrome 无头引擎精准分页，彻底消除滚动条与公式溢出，内置 `<span class="pageNumber"></span> / <span class="totalPages"></span>` 真实页码。
   - **独立 HTML**：自包含单文件，内置 KaTeX 公式渲染与打印排版。
   - **规范 Markdown**：携带标准 YAML Frontmatter 元数据，无缝对接 Obsidian / Typora / VitePress。

5. **断点续传与持久化 (TaskTracker Checkpoint)**：
   - 大规模处理 50+ 讲义或数百页专著时，秒级记录进度至 `.checkpoint.json`。若遇网络抖动或中断，重启时秒级跳过已完成项，绝不重复计费。

---

## 🚀 命令行快速上手 (CLI)

```bash
# 1. 基础手写板书数字化并一键生成专著合订本
python -m academic_core.cli --input "./raw_onenote/*.one" --task note --merge --title "高等代数讲义全书"

# 2. 学术前沿论文全格式直出 (PDF + HTML + Markdown 并行生成)
python -m academic_core.cli --input "./papers/*.pdf" --task paper --export all --bilingual

# 3. 外文经典教材精译 (调用 DeepSeek-V3 并注入专业术语强制规范表)
python -m academic_core.cli --input "./textbook.docx" --task textbook --provider deepseek --llm deepseek-v3 --glossary '{"manifold": "流形", "quotient space": "商空间"}'

# 4. 零 Token 消耗极速离线测试 (Mock 模式)
python -m academic_core.cli --input "./slides/*.pptx" --task textbook --ocr mock --provider mock --export all
```

---

## 🐍 Python SDK 调用示例

```python
from academic_core import (
    AcademicPipeline,
    convert_to_normalized,
    get_vision_engine,
    AcademicLLMEngine,
    LatexCleaner,
    get_exporter
)

# 方式一：统一流水线开箱即用
pipeline = AcademicPipeline(
    llm_provider="dashscope",
    llm_model="qwen-plus",
    vision_engine_name="qwen-vl-ocr",
    task="note"
)
outputs = pipeline.process_one(
    "lecture.pptx",
    output_dir="./dist",
    export_formats=["pdf", "html", "md"],
    glossary={"eigenvalue": "特征值"}
)
print("交付物:", outputs["pdf"], outputs["html"], outputs["md"])

# 方式二：积木式原子组件调用
norm_doc = convert_to_normalized("scan.zip")          # 1. 任意格式归一化
raw_latex = norm_doc.pages[0].text                   # 2. 提取或送入视觉引擎
cleaned_latex = LatexCleaner.clean(raw_latex)        # 3. 数学语法自愈
pdf_printer = get_exporter("pdf")                    # 4. 出版级导出
pdf_printer.print_markdown(cleaned_latex, "out.pdf", title="数学讲义")
```

---

## 🧪 全自动化测试

运行 7 大模块全量自动化综合质检：
```bash
python tests/test_academic_core_suite.py
```
全部 7 大核心模块质检通过，0 缺陷！
