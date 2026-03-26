"""Paddle JSONL → pages/blocks（与 workspace-main 一致）。"""
from __future__ import annotations

from typing import Any


def _as_bbox(v: Any) -> list[float] | None:
    if v is None:
        return None
    if isinstance(v, (list, tuple)) and len(v) == 4:
        try:
            return [float(x) for x in v]
        except (TypeError, ValueError):
            return None
    if isinstance(v, dict):
        for k in ("bbox", "box", "coordinate"):
            if k in v:
                return _as_bbox(v[k])
    return None


def _caption_for_empty_block(label: str) -> str:
    low = label.lower()
    if "image" in low or "figure" in low or "chart" in low:
        return "（图片区域，解析结果中无文字层；可对整页或邻近段落提问）"
    if "table" in low:
        return "（表格区域）"
    return f"（{label}）"


def _collect_bbox_text_pairs(obj: Any, out: list[tuple[list[float], str, str]]) -> None:
    if isinstance(obj, dict):
        label = str(obj.get("block_label") or obj.get("label") or obj.get("type") or "block")
        raw = obj.get("block_content") or obj.get("text") or obj.get("content") or obj.get("transcription")
        text = str(raw).strip() if raw is not None else ""
        bbox = _as_bbox(obj.get("block_bbox") or obj.get("bbox") or obj.get("box"))

        if bbox:
            if not text:
                text = _caption_for_empty_block(label)
            out.append((bbox, text, label))

        for v in obj.values():
            _collect_bbox_text_pairs(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_bbox_text_pairs(item, out)


def _extract_markdown_text(res: dict[str, Any]) -> str | None:
    """
    Paddle 对「扫描件 / PPT 转 PDF 整页图」等，常见把 markdown 放在：
    - 字符串 res['markdown']
    - 或 dict res['markdown']['text']
    旧逻辑只认 dict，会把字符串整页内容丢掉，导致 blocks 为空、pages 为空。
    """
    m = res.get("markdown")
    if isinstance(m, str) and m.strip():
        return m.strip()
    if isinstance(m, dict):
        t = m.get("text")
        if isinstance(t, str) and t.strip():
            return t.strip()
    return None


def _pairs_from_parsing_res_list(res: dict[str, Any]) -> list[tuple[list[float], str, str]]:
    pairs: list[tuple[list[float], str, str]] = []
    pr = res.get("prunedResult")
    if not isinstance(pr, dict):
        return pairs
    lst = pr.get("parsing_res_list")
    if not isinstance(lst, list) or not lst:
        return pairs
    for item in lst:
        if not isinstance(item, dict):
            continue
        label = str(item.get("block_label") or item.get("label") or "block")
        raw = item.get("block_content") or item.get("text") or item.get("content")
        text = str(raw).strip() if raw is not None else ""
        bbox = _as_bbox(item.get("block_bbox") or item.get("bbox"))
        if not bbox:
            # PPT 导出 PDF 常见：有文字块但无 bbox，旧逻辑全部丢弃 → 整页无块
            if text:
                pairs.append(([0.0, 0.0, 0.0, 0.0], text, label))
            continue
        if not text:
            text = _caption_for_empty_block(label)
        pairs.append((bbox, text, label))
    return pairs


def blocks_from_layout_result(res: dict[str, Any], page_index: int) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    md_text = _extract_markdown_text(res)
    pairs = _pairs_from_parsing_res_list(res)
    if not pairs:
        _collect_bbox_text_pairs(res, pairs)

    if isinstance(md_text, str) and md_text.strip():
        if not pairs:
            blocks.append(
                {
                    "id": f"p{page_index + 1}_b0",
                    "page_num": page_index + 1,
                    "bbox": None,
                    "text": md_text.strip(),
                    "type": "document",
                    "markdown": md_text.strip(),
                }
            )
            return blocks

    for i, (bbox, text, label) in enumerate(pairs):
        blocks.append(
            {
                "id": f"p{page_index + 1}_b{i}",
                "page_num": page_index + 1,
                "bbox": bbox,
                "text": text,
                "type": _normalize_type(label),
                "markdown": None,
            }
        )

    if not blocks and md_text:
        blocks.append(
            {
                "id": f"p{page_index + 1}_b0",
                "page_num": page_index + 1,
                "bbox": None,
                "text": md_text,
                "type": "document",
                "markdown": md_text,
            }
        )

    return blocks


def _page_dimensions_from_res(res: dict[str, Any]) -> tuple[float | None, float | None]:
    pr = res.get("prunedResult")
    if isinstance(pr, dict):
        w, h = pr.get("width"), pr.get("height")
        if w is not None and h is not None:
            try:
                return float(w), float(h)
            except (TypeError, ValueError):
                pass
    return None, None


def _normalize_type(label: str) -> str:
    s = label.lower()
    if "title" in s or "header" in s:
        return "title"
    if "table" in s:
        return "table"
    if "figure" in s or "image" in s or "chart" in s:
        return "figure"
    if "list" in s:
        return "list"
    return "paragraph"


def pages_from_paddle_jsonl_lines(lines: list[dict[str, Any]]) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    global_page = 0

    for record in lines:
        result = record.get("result") if isinstance(record, dict) else None
        if not isinstance(result, dict):
            continue
        lprs = result.get("layoutParsingResults")
        if not isinstance(lprs, list):
            continue
        for res in lprs:
            if not isinstance(res, dict):
                continue
            blocks = blocks_from_layout_result(res, global_page)
            page_md = _extract_markdown_text(res)
            if not blocks and page_md:
                blocks = [
                    {
                        "id": f"p{global_page + 1}_b0",
                        "page_num": global_page + 1,
                        "bbox": None,
                        "text": page_md,
                        "type": "document",
                        "markdown": page_md,
                    }
                ]
            if blocks:
                page_entry: dict[str, Any] = {"page_num": global_page + 1, "blocks": blocks}
                if page_md:
                    page_entry["markdown"] = page_md
                pw, ph = _page_dimensions_from_res(res)
                if pw is not None and ph is not None:
                    page_entry["page_width"] = pw
                    page_entry["page_height"] = ph
                pages.append(page_entry)
            global_page += 1

    return {"pages": pages}


def content_list_from_paddle_doc(doc: dict[str, Any]) -> list[str]:
    """按页生成用于讲稿/RAG 的纯文本列表（与 PDF 页码对齐）。"""
    pages = doc.get("pages") or []
    out: list[str] = []
    for p in pages:
        md = p.get("markdown")
        if isinstance(md, str) and md.strip():
            out.append(md.strip())
            continue
        parts: list[str] = []
        for b in p.get("blocks") or []:
            t = (b.get("text") or "").strip()
            if t:
                parts.append(t)
        out.append("\n".join(parts) if parts else "")
    return out
