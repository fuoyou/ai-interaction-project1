# 文档解析与 RAG 集成方案说明

## 1. 目标与范围

本文说明当前系统在 `ai-interaction-project1` 中的文档处理链路，包括：

- RAG 集成之前的文档解析与渲染思路（历史基线）。
- 当前（已集成 RAG）的文档解析、存储、检索、问答链路。
- RAG 集成后的业务作用与性能/准确性影响。
- 近期针对页码对应关系、预览渲染的专项修复说明。

---

## 2. RAG 集成之前：文档解析与渲染思路

## 2.1 解析思路（无检索索引）

在未集成 RAG 之前，核心流程是"上传 -> 提取文本 -> 直接用于讲稿生成/问答"：

1. 上传课件（`pdf/ppt/pptx`）。
2. 后端提取文本：
   - `pdf`：优先 `PyPDF2`，必要时 OCR 兜底。
   - `ppt/pptx`：`python-pptx` 文本提取；部分场景尝试先转 PDF。
3. 生成讲稿 `script_content` 与音频 `audio_sections`。
4. 互动问答主要依赖"当前页讲稿 + 历史对话"构造 Prompt。

该阶段的关键特点：

- 没有持久化检索索引（无 `rag_chunks`）。
- 问答阶段不做细粒度原文召回，模型更容易偏向泛化回答。

## 2.2 渲染思路（以可预览优先）

- `PDF`：前端通过 `vue-pdf-embed` 本地渲染。
- `PPT/PPTX`：
  - 若已成功转 PDF，则按 PDF 渲染。
  - 若仍是 `ppt/pptx`，前端尝试 Office Online iframe 预览。

已知限制（历史问题）：

- 本地开发环境 `localhost` 文件地址无法被 Office Online 访问，可能出现预览错误页。
- `ppt -> pdf` 依赖本机 COM/WPS/Office 环境，存在环境差异与失败风险。

---

## 3. 当前方案：文档解析 + RAG 集成

## 3.1 端到端链路

1. 课件上传（`/api/v1/lesson/parse`）。
2. 后端解析文本（`file_utils.py`）：
   - PDF 多级策略：`PyPDF2` → `pypdfium2` → `Docling（按页）` → `RapidOCR` 兜底。
   - PPT/PPTX：先尝试 WPS COM 转 PDF；失败则回退纯 Python（reportlab）转换；最终失败则直接文本提取。
3. 构建 RAG 切片并入库（`biz_lesson.rag_chunks`，LONGTEXT）：
   - `SentenceSplitter` 切分。
   - 限制切片数量与总字符量，防止超长。
4. 并行生成讲稿与音频：
   - 讲稿线程池 3 并发。
   - 音频线程池 4 并发。
5. 问答阶段（`/api/v1/qa/interact` 与 `/api/v1/qa/interact/stream`）：
   - 读取当前页讲稿上下文。
   - 用 BM25 在 `rag_chunks` 中召回相关原文片段。
   - 拼装上下文后调用模型回答（支持流式输出）。

## 3.2 RAG 组件设计

- 切片：`utils/rag_utils.py::SentenceSplitter`
  - 中英文混合分句与合并，默认 `chunk_size=500`。
- 检索：`RAGRetriever(BM25Okapi)`
  - 中文用 `jieba` 分词，英文用正则 token。
- 存储：`Lesson.rag_chunks`
  - JSON 序列化后入库，字段已升级为 `LONGTEXT`。
- 检索缓存：
  - 问答阶段引入 `RAGRetriever` LRU 缓存（按 `lesson_id + chunks_hash` 复用）。

## 3.3 问答上下文构造（当前行为）

问答 Prompt 的上下文由三层组成：

1. 当前页讲稿（`context_text`）。
2. RAG 召回原文片段（`rag_context_text`）。
3. 当前页可见内容（`currentPageContent`，由前端传入）。

同时加入约束语义："优先依据当前页内容回答；证据不足时明确说明，不要编造。"

## 3.4 流式问答能力

- 新增 SSE 接口：`POST /api/v1/qa/interact/stream`。
- 事件类型：`meta`、`delta`、`done`、`error`。
- 前端在互动答疑中边接收边渲染，降低首字等待。
- 流式链路中默认不执行重型重建（如 OCR 重建），优先保证首包速度。

---

## 4. RAG 集成的作用

## 4.1 对回答质量的作用

- 从"只看讲稿摘要"升级为"讲稿 + 原文片段证据"。
- 面对细节问题（术语、数字、定义）时可召回更贴近原文的内容。
- 降低模型脱离课件主题的概率。

## 4.2 对可维护性的作用

- `rag_chunks` 持久化到课件维度，后续问答可复用，不必每次重新切分全文。
- 历史课件若无索引可按需补建，兼容老数据。

## 4.3 对性能的作用

- 通过缓存复用 BM25 检索器，减少重复建索引开销。
- 通过重建限频避免"每次未命中都触发 OCR/重构"。
- 文本问答默认不阻塞 TTS，优先返回文字结果。

---

## 5. 当前方案与"集成前"的差异总结

## 5.1 核心差异

- 集成前：问答主要基于当前页讲稿文本，缺少原文证据召回。
- 集成后：问答增加 BM25 检索层，能将原文片段注入模型上下文。

## 5.2 体验差异

- 集成前：回答速度受模型影响，且可能"快但泛"。
- 集成后：回答更有依据；配合流式后首字体验更好，但首帧仍受网络与模型时延影响。

## 5.3 数据结构差异

- 集成前：`Lesson` 仅有结构化讲稿/音频等字段。
- 集成后：新增 `rag_chunks`（LONGTEXT）用于检索索引持久化。

---

## 6. 专项修复记录

本节记录近期针对课件解析、预览与讲稿同步的关键修复，供后续维护参考。

## 6.1 页码错位修复（核心）

**问题根因：** 原 `_extract_pdf_pypdf2` 遇到无可提取文本的页面（纯图片/图表页）时会直接跳过，导致 `content_list[i]` 不对应 PDF 第 `i+1` 页。后续讲稿以 `{"page": i+1, ...}` 编号入库，但学生端按 PDF 页码查找讲稿时命中错误内容，出现"伴随讲解与当前页内容不符"现象。

**修复位置：** `fanya-ai-backend/utils/file_utils.py`

**修复内容：**

1. **`_extract_pdf_pypdf2`**：移除 `if page_text:` 过滤，所有页均写入列表（空页以 `""` 占位），保证 `content_list[i]` 始终对应 PDF 第 `i+1` 页。

2. **新增 `_extract_pdf_pypdfium2`**：使用 `pypdfium2` 原生文本层逐页提取，作为 PyPDF2 质量不足时的次选方案，同样保留空页占位。

3. **`_extract_pdf_docling` 重写**：尝试通过 Docling 文档对象的 `pages` 属性按页获取文本；若无法按页返回则返回 `[]`（放弃使用），避免原先按段落切分导致的页码与内容错位。

4. **`_extract_pdf_rapidocr` 修复**：无 OCR 结果的页面改为追加 `""` 占位，而非跳过，确保该路径也满足页码对应关系。

5. **`extract_text_from_pdf` 更新回退链路**：
   ```
   PyPDF2（含空页）→ pypdfium2（含空页）→ Docling（仅按页）→ RapidOCR（含空页）
   ```
   核心设计原则：**返回列表的第 i 项必须对应 PDF 第 i+1 页，绝不跳过空页。**

**影响范围：** 新上传课件立即生效。存量已解析课件的 `aiScript` 仍为旧数据（页码可能偏移），需要教师重新上传触发重新解析才能修正。

## 6.2 教师端课件状态展示修复

**问题：** 课件 `status === 9`（解析失败）但已有生成内容时，界面显示"文件解析失败，请重新上传"，导致已保存的讲稿内容无法展示。

**修复位置：** `fanya-ai-frontend/src/views/TeacherWorkbench/index.vue`

**修复内容：** 在 `selectCourse` 中，当 `status === 9` 且 `aiScript` 非空时，直接调用 `parseData()` 静默加载已有内容，不再弹出错误提示；仅在 `aiScript` 为空时才提示重新上传。

## 6.3 教师端 PPT/PDF 预览布局修复

**问题：** PPT 预览区域四周黑边过多；PDF 上下留白不均；工具栏与预览内容存在位置叠压。

**修复位置：** `fanya-ai-frontend/src/views/TeacherWorkbench/components/Editor.vue`

**修复内容：**
- 工具栏从 `position: absolute` 改为流式布局（新增 `.stage-toolbar`），消除 `padding-top: 100px` 占位。
- 引入 `pdfViewRef`、`pdfRenderWidth`、`pdfAspectRatio`，根据容器实际尺寸动态计算渲染宽度（`min(maxByWidth, maxByHeight)`），实现"适配页面"效果。
- `.editor-container` 高度从 `100vh` 改为 `100%`，确保容器高度测量正确。

## 6.4 学生端课件预览重构

**问题：** 学生端 PDF 查看器采用纵向滚动翻页，翻页体验与教师端不一致；PDF 文档左右留白过多；PPT/PPTX 幻灯片顶部内容被遮挡。

**修复位置：** `fanya-ai-frontend/src/views/StudentClassroom/components/PdfViewer.vue`

**修复内容：**
- 完全重构为与教师端一致的单页翻页模式（上一页/下一页按钮，底部工具栏）。
- 通过检测第一页宽高比区分"幻灯片类（横向）PDF"与"文档类（纵向）PDF"：
  - **横向 PDF**（PPT 转换而来）：全铺显示，无内边距，`align-items: flex-start` 顶部对齐，避免居中加 overflow 导致顶部截断。
  - **纵向 PDF**（普通文档）：铺满宽度，保留少量边距，纵向可滚动。
- 引入 `recalcPdfWidth`，监听窗口尺寸变化自动重算渲染宽度。

## 6.5 学生端 .ppt 文件处理

**问题：** 原始 `.ppt` 文件在学生端直接展示"无法预览"错误页，体验差；且不会在后端转换完成后自动刷新。

**修复位置：** `fanya-ai-frontend/src/views/StudentClassroom/index.vue` 与 `PdfViewer.vue`

**修复内容：**
- 新增 `isPreviewableUrl` 工具函数，区分 `.pdf`/`.pptx`（可直接预览）与 `.ppt`（需等待后端转换）。
- `.ppt` 文件在转换期间展示"正在转换为可预览格式，请稍候…"友好提示。
- 轮询机制增强：当 `fileUrl` 由不可预览格式更新为可预览格式时，自动更新 `pdfSource` 并展示预览，无需用户手动刷新。

---

## 7. 已知边界与建议

## 7.1 PPT 预览边界

- Office Online 预览依赖"公网可访问 URL"。
- 本地 `localhost` 链接无法被 Office Online 拉取。
- 当前前端已对本地场景做降级提示（不再直接显示错误页）。

## 7.2 PPT 转 PDF 边界

- COM/WPS/Office 依赖与系统环境强相关。
- 建议长期采用"稳定转换链路"（如 LibreOffice headless）作为首选。

## 7.3 RAG 准确性边界

- 召回质量依赖文本提取质量；扫描件/OCR 质量差时会影响问答证据。
- 建议持续监控：
  - OCR 命中率
  - RAG 命中率
  - 流式首包时延与总时延

## 7.4 存量数据页码偏移

- 在 **6.1 页码错位修复** 部署前已解析的课件，其 `aiScript` 中的页码与 PDF 页码可能不对应。
- 受影响课件需由教师重新上传，触发重新解析，才能获得正确的讲稿-页面同步。

---

## 8. 结论

当前系统已从"解析后直接问答"升级为"解析 + 索引 + 检索增强问答"架构。  
RAG 的核心价值在于：为回答提供可追溯的课件原文证据，提高"贴课件内容回答"的稳定性。  
近期专项修复进一步确保了讲稿与 PDF 页码的严格对应关系，以及教师端与学生端的预览一致性。  
后续优化重点应放在：PPT 稳定转换链路（LibreOffice）、OCR 质量提升、流式首包时延和检索可观测性。
