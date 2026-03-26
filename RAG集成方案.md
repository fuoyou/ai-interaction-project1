# RAG 方案A 集成说明
> 最后更新：2026-03-07
## 整体架构
```
上传文档
  │
  ▼
文档解析 (file_utils.py)
  ├── PyPDF2 快速提取（优先）
  │     └── 文本量 ≥ 100 字符 → 直接返回，跳过 Docling
  └── Docling OCR 精准解析（兜底）
        ├── 版面分析（Layout Heron 模型）
        ├── 表格识别（TableFormer 模型）
        └── 文字识别（RapidOCR / PaddleOCR）
  │
  ▼
RAG 索引构建 (rag_utils.py)
  ├── SentenceSplitter：中英文混合 chunk 切分
  └── BM25 索引序列化，存入 DB（biz_lesson.rag_chunks）
  │
  ▼
讲稿生成 (lesson_controller.py)
  └── 多线程并行：ThreadPoolExecutor(max_workers=3)
  │
  ▼
音频生成 (lesson_controller.py)
  └── 多线程并行：ThreadPoolExecutor(max_workers=4)
  │
  ▼
学生提问 → qa_controller.py
  ├── BM25 检索最相关 chunk（~0.01s）
  ├── 注入上下文 Prompt
  └── 智谱 API 生成回答（~1-3s）
```
---
## 一、文档解析
### 解析策略（双轨制）
| 策略 | 触发条件 | 耗时 | 适用场景 |
|------|----------|------|----------|
| **PyPDF2 快速提取**（优先） | 提取文本 ≥ 100 字符 | ~0.1-1s | 普通电子 PDF、Word 导出 PDF |
| **Docling OCR 精准解析**（兜底） | PyPDF2 文本不足 | ~5-60s | 扫描版 PDF、PPTX、含复杂表格/公式 |
> 对于绝大多数普通 PDF，PyPDF2 快速路径可直接返回，**完全跳过深度学习 OCR**，解析时间从几十秒降至不到 1 秒。
### Docling 深度学习模型位置
| 模型 | 路径 | 大小 | 用途 |
|------|------|------|------|
| TableFormer (accurate) | `C:\Users\Leander\.cache\huggingface\hub\models--docling-project--docling-models\snapshots\...\tableformer_accurate.safetensors` | 203 MB | 高精度表格识别 |
| TableFormer (fast) | 同目录 `tableformer_fast.safetensors` | 139 MB | 快速表格识别 |
| Layout Heron | `C:\Users\Leander\.cache\huggingface\hub\models--docling-project--docling-layout-heron\snapshots\...\model.safetensors` | 164 MB | 版面区域分析 |
| RapidOCR (检测) | `fanya/Lib/site-packages/rapidocr/models/ch_PP-OCRv4_det_infer.onnx` | 4.5 MB | 文字区域检测 |
| RapidOCR (识别) | `fanya/Lib/site-packages/rapidocr/models/ch_PP-OCRv4_rec_infer.onnx` | 10.4 MB | 文字内容识别 |
> Docling 冷启动需将约 **500 MB** 模型权重加载入内存，这是首次解析慢的根本原因。
### 解析失败回退链
```
Docling 解析
  └── 失败 → PyPDF2（PDF）/ python-pptx（PPTX）
```
---
## 二、RAG 检索
### 组件说明
- **`utils/rag_utils.py`**
  - `SentenceSplitter`：中英文混合 chunk 切分（按句号/换行分段，最大 chunk_size=500 字符）
  - `RAGRetriever`：基于 BM25 的关键词检索
  - `get_rag_context()`：按问题检索最相关的 Top-K chunk，拼接为 Prompt 上下文
- **存储**：RAG chunk 列表 JSON 序列化后存入 `biz_lesson.rag_chunks` 字段
- **按需重建**：若历史课件的 `rag_chunks` 为空，`qa_controller` 在首次问答时会自动从原文件重新构建并写回数据库
### 耗时
| 阶段 | 耗时 |
|------|------|
| chunk 切分 + BM25 构建 | ~0.5s |
| BM25 检索（单次问答） | ~0.01s |
---
## 三、加速策略汇总
### 3.1 DocumentConverter 单例 + 后台预热
**位置**：`utils/file_utils.py`
**问题**：每次解析文档都重新初始化 `DocumentConverter`，导致 OCR 神经网络模型反复加载（每次 ~60-90s）。
**方案**：
```python
_converter = None
_converter_lock = threading.Lock()
_converter_ready = threading.Event()
def _init_converter():
    global _converter
    _converter = DocumentConverter()   # 仅执行一次
    _converter_ready.set()
# Flask 启动时立即在后台线程加载模型
threading.Thread(target=_init_converter, daemon=True, name="docling-warmup").start()
```
**效果**：
| | 优化前 | 优化后 |
|--|--------|--------|
| 首次文档解析（冷启动） | ~60-90s（模型加载） | ~60-90s（后台预热，不阻塞上传） |
| 后续文档解析（热启动） | ~60-90s（每次重新加载） | **~0.1s**（复用已加载模型） |
---
### 3.2 PyPDF2 优先策略（快速路径）
**位置**：`utils/file_utils.py` → `extract_text_from_pdf()`
**方案**：先用 PyPDF2 尝试提取，文本量充足则直接返回，跳过 Docling。
```python
def extract_text_from_pdf(file_path):
    fast_result = _extract_pdf_pypdf2(file_path)
    total_chars = sum(len(p.strip()) for p in fast_result)
    if total_chars >= 100:
        print(f"[PDF] PyPDF2 快速提取成功（{total_chars} 字符），跳过 Docling OCR")
        return fast_result
    # 文本不足（扫描版/图片 PDF）→ 回退 Docling
    return _docling_extract(file_path)
```
**效果**：普通电子 PDF 解析时间从 ~10-60s 降至 **< 1s**。
---
### 3.3 讲稿生成并行化
**位置**：`controllers/lesson_controller.py`
**方案**：每页讲稿独立提交到线程池，并行调用智谱 API。
```python
with ThreadPoolExecutor(max_workers=3, thread_name_prefix='script') as pool:
    futures = {pool.submit(_gen_page_script, (i, text)): i
               for i, text in enumerate(content_list)}
    for future in as_completed(futures):
        # 结果回来即存库，无需等全部完成
        ...
```
**效果**：N 页讲稿生成时间从 `N × 单页耗时` 降至约 `N/3 × 单页耗时`。
---
### 3.4 TTS 音频生成并行化
**位置**：`controllers/lesson_controller.py`
**方案**：每段音频独立提交到线程池，并行调用 `edge-tts`。
```python
with ThreadPoolExecutor(max_workers=4, thread_name_prefix='tts') as pool:
    futures = [pool.submit(_gen_page_audio, section) for section in script_sections]
    for future in as_completed(futures):
        ...
```
**效果**：N 段音频生成时间从串行 `N × 单段耗时` 降至约 `N/4 × 单段耗时`。
---
### 3.5 ZhipuAI 客户端单例
**位置**：`utils/ai_utils.py`
**方案**：复用同一个 `ZhipuAI` 客户端实例，避免每次 AI 调用都重新建立 HTTP 连接。
```python
_zhipu_client = None
_zhipu_client_key = None
def _get_zhipu_client(api_key: str):
    global _zhipu_client, _zhipu_client_key
    if _zhipu_client is None or _zhipu_client_key != api_key:
        _zhipu_client = ZhipuAI(api_key=api_key)
        _zhipu_client_key = api_key
    return _zhipu_client
```
**效果**：减少每次 AI 调用的 TCP 握手开销，高并发场景下效果明显。
---
## 四、整体耗时预估（优化后）
| 阶段 | 普通电子 PDF | 扫描版 / PPTX |
|------|-------------|--------------|
| 文档解析 | **< 1s**（PyPDF2 快速路径） | ~5-60s（Docling OCR） |
| RAG 索引构建 | ~0.5s | ~0.5s |
| 讲稿生成（10页） | ~10-20s（并行 3 线程） | ~10-20s |
| 音频生成（10段） | ~10-15s（并行 4 线程） | ~10-15s |
| **单次问答** | **~0.01s（检索）+ ~1-3s（AI）** | 同左 |
---
## 五、依赖
```
jieba
rank-bm25
docling
python-pptx
PyPDF2
edge-tts
```
---
## 六、数据库
若使用已有数据库，需手动添加列（重启应用也会自动尝试迁移）：
```sql
ALTER TABLE biz_lesson ADD COLUMN rag_chunks TEXT;
```
---
## 七、调试工具
| 工具 | 说明 |
|------|------|
| `python scripts/test_rag_timing.py` | 测试各阶段耗时 |
| `python scripts/rebuild_rag_for_lessons.py` | 重建历史课件的 RAG 索引 |
| 控制台 `[计时]` / `[PDF]` 日志 | 实时观察解析与检索耗时 |
