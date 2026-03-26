"""
诊断 PPT/PPTX 在「转 PDF → PaddleOCR-VL → normalize」链路中失败原因。

与线上一致：先 ppt_to_pdf（WPS/PowerPoint COM），再 run_parse_pipeline，再 pages_from_paddle_jsonl_lines。

用法（在 fanya-ai-backend 目录下）:
  python scripts/test_ppt_parse_pipeline.py "D:\\path\\to\\课件.ppt"
  python scripts/test_ppt_parse_pipeline.py "D:\\file.pptx"
  python scripts/test_ppt_parse_pipeline.py --pdf "D:\\already.pdf"   # 只测 Paddle + 归一化

环境变量（与线上一致，可从 .env 加载）:
  PADDLE_OCR_TOKEN  未设置时使用 --skip-paddle 仅测转 PDF

  pip install python-dotenv  # 可选，用于自动加载 .env
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import traceback

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))
except ImportError:
    pass


def _section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _print_safe(line: str) -> None:
    """Windows 控制台常见 GBK，避免预览里的 ☑ 等字符触发 UnicodeEncodeError。"""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode(enc, errors="replace").decode(enc, errors="replace"))


def _pdf_page_count(pdf_path: str) -> int | None:
    try:
        from PyPDF2 import PdfReader

        r = PdfReader(pdf_path)
        return len(r.pages)
    except Exception as e:
        print(f"  [PyPDF2] 无法读取页数: {e}")
        return None


def _try_python_pptx(path: str) -> None:
    """python-pptx 仅支持 pptx；对 .ppt 会失败，用于提示。"""
    ext = os.path.splitext(path)[1].lower()
    if ext != ".pptx":
        print(f"  python-pptx 不支持 {ext}，跳过（线上主链路也不用它解析 .ppt）")
        return
    try:
        from pptx import Presentation

        prs = Presentation(path)
        n = len(prs.slides)
        print(f"  python-pptx 可读: 共 {n} 页幻灯片")
    except Exception as e:
        print(f"  python-pptx 打开失败: {e}")


def _summarize_paddle_record(record: dict, idx: int) -> None:
    print(f"  --- JSONL 第 {idx + 1} 条 ---")
    if not isinstance(record, dict):
        print(f"    类型非 dict: {type(record)}")
        return
    print(f"    顶层键: {list(record.keys())[:20]}")
    result = record.get("result")
    if not isinstance(result, dict):
        print(f"    result 缺失或非 dict → normalize 会跳过本条（无法出页）")
        return
    print(f"    result 键: {list(result.keys())[:30]}")
    lprs = result.get("layoutParsingResults")
    if not isinstance(lprs, list):
        print(f"    layoutParsingResults 缺失或非 list → 本条不产生页面")
        return
    print(f"    layoutParsingResults 长度: {len(lprs)}")
    for j, res in enumerate(lprs[:2]):
        if not isinstance(res, dict):
            print(f"      [{j}] 非 dict")
            continue
        keys = list(res.keys())
        md = res.get("markdown")
        md_ok = isinstance(md, str) and md.strip()
        pr = res.get("prunedResult")
        pr_ok = isinstance(pr, dict)
        pr_list_len = len(pr.get("parsing_res_list") or []) if pr_ok else 0
        print(f"      [{j}] keys(前15)={keys[:15]}")
        print(f"          markdown 有正文: {md_ok}  |  prunedResult.parsing_res_list 条数: {pr_list_len}")


def _count_paddle_logical_pages(lines: list[dict]) -> int:
    n = 0
    for record in lines:
        if not isinstance(record, dict):
            continue
        result = record.get("result")
        if not isinstance(result, dict):
            continue
        lprs = result.get("layoutParsingResults")
        if isinstance(lprs, list):
            n += len(lprs)
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="诊断 PPT 解析链路")
    parser.add_argument(
        "path",
        nargs="?",
        help="待测的 .ppt 或 .pptx 路径",
    )
    parser.add_argument(
        "--pdf",
        metavar="PDF",
        help="跳过转 PDF，直接对该 PDF 跑 Paddle + normalize",
    )
    parser.add_argument(
        "--skip-paddle",
        action="store_true",
        help="不调用 Paddle 云端（无需 PADDLE_OCR_TOKEN）",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="保留临时目录并打印路径（默认测完删除）",
    )
    args = parser.parse_args()

    if args.pdf:
        pdf_path = os.path.abspath(args.pdf)
        if not os.path.isfile(pdf_path):
            print(f"文件不存在: {pdf_path}")
            return 1
        work_dir = None
        src_label = pdf_path
    else:
        if not args.path:
            parser.error("请传入 .ppt/.pptx 路径，或使用 --pdf")
        src = os.path.abspath(args.path)
        if not os.path.isfile(src):
            print(f"文件不存在: {src}")
            return 1
        ext = os.path.splitext(src)[1].lower()
        if ext not in (".ppt", ".pptx"):
            print(f"扩展名应为 .ppt 或 .pptx，当前: {ext}")
            return 1
        work_dir = tempfile.mkdtemp(prefix="ppt_parse_probe_")
        staged = os.path.join(work_dir, f"probe{ext}")
        shutil.copy2(src, staged)
        src_label = staged
        pdf_path = os.path.join(work_dir, f"probe.pdf")

    token = os.environ.get("PADDLE_OCR_TOKEN", "").strip()
    if not args.skip_paddle and not token:
        print("警告: 未设置 PADDLE_OCR_TOKEN，将跳过 Paddle 步骤。可设置环境变量或改用 --skip-paddle 明确仅测转 PDF。")
        args.skip_paddle = True

    _section("0) 输入")
    if args.pdf:
        print(f"  源 PDF: {pdf_path}")
    else:
        print(f"  源: {src_label}")
        print(f"  扩展名: {os.path.splitext(src_label)[1]}")
        _try_python_pptx(src_label)

    from utils.file_utils import ppt_to_pdf

    if args.pdf:
        _section("1) 转 PDF")
        print("  已跳过（--pdf）")
    else:
        _section("1) 转 PDF（与线上 ppt_to_pdf 相同：WPS COM → PowerPoint COM）")
        try:
            t0 = __import__("time").time()
            out = ppt_to_pdf(src_label)
            dt = __import__("time").time() - t0
            print(f"  耗时: {dt:.2f}s")
            if not out or not os.path.isfile(out):
                print("  失败: ppt_to_pdf 返回空或文件不存在（线上会报「PPT/PPTX 转 PDF 失败」）")
                if args.keep_temp and work_dir:
                    print(f"  临时目录: {work_dir}")
                return 2
            pdf_path = os.path.abspath(out)
            sz = os.path.getsize(pdf_path)
            print(f"  成功: {pdf_path}")
            print(f"  PDF 大小: {sz} bytes")
            pc = _pdf_page_count(pdf_path)
            if pc is not None:
                print(f"  PyPDF2 页数: {pc}")
        except Exception as e:
            print(f"  异常: {e}")
            traceback.print_exc()
            if args.keep_temp and work_dir:
                print(f"  临时目录: {work_dir}")
            return 2

    if args.skip_paddle:
        _section("2) PaddleOCR-VL")
        print("  已跳过")
        _section("3) 结论")
        print("  若线上仍「解析失败」，请去掉 --skip-paddle 并配置 PADDLE_OCR_TOKEN 再跑完整链路。")
        if args.keep_temp and work_dir:
            print(f"  临时目录: {work_dir}")
        return 0

    from utils.paddle_client import run_parse_pipeline
    from utils.normalize import content_list_from_paddle_doc, pages_from_paddle_jsonl_lines

    _section("2) PaddleOCR-VL（submit → poll → 下载 JSONL）")
    try:
        t0 = __import__("time").time()
        raw_text, lines = run_parse_pipeline(pdf_path)
        dt = __import__("time").time() - t0
        print(f"  耗时: {dt:.2f}s")
        print(f"  JSONL 行数（非空行）: {len(lines)}")
        logical_pages = _count_paddle_logical_pages(lines)
        print(f"  layoutParsingResults 累计页块数（估算）: {logical_pages}")
    except Exception as e:
        print(f"  失败: {e}")
        traceback.print_exc()
        print("  线上会报: PaddleOCR-VL 解析失败: ...")
        if args.keep_temp and work_dir:
            print(f"  临时目录: {work_dir}")
        return 3

    _section("2.1) JSONL 结构抽样（空页/字段不匹配时常在这里）")
    for i in range(min(3, len(lines))):
        _summarize_paddle_record(lines[i], i)
    if not lines:
        print("  JSONL 无有效行 → 线上会得到空 content_list")

    _section("3) normalize（与 lesson_controller 相同）")
    try:
        doc = pages_from_paddle_jsonl_lines(lines)
        pages = doc.get("pages") or []
        content_list = content_list_from_paddle_doc(doc)
        nonempty = sum(1 for s in content_list if (s or "").strip())
        print(f"  pages 条数: {len(pages)}")
        print(f"  content_list 长度: {len(content_list)}")
        print(f"  非空文本页数: {nonempty}")
        for i, text in enumerate(content_list[:3]):
            preview = (text or "")[:180].replace("\n", " ")
            tail = "..." if len(text or "") > 180 else ""
            _print_safe(f"    第{i+1}页预览: {preview!r}{tail}")
    except Exception as e:
        print(f"  异常: {e}")
        traceback.print_exc()
        return 4

    _section("4) 与线上失败条件对照")
    if not content_list or not any((s or "").strip() for s in content_list):
        print("  >>> 会触发: 「PaddleOCR-VL 未识别到有效页面内容」")
        print("  常见原因: 返回 JSONL 里 layoutParsingResults 为空，或每页无 markdown/无 parsing_res_list 文本；")
        print("           多见于「整页栅格化」的 PDF（老 .ppt 经 WPS 导出）。")
    else:
        print("  >>> 转 PDF + Paddle + normalize 均正常；若线上仍失败，请核对是否同一文件、同一环境变量与同一工作目录。")

    dump_path = None
    if work_dir and len(lines) <= 50:
        try:
            dump_path = os.path.join(work_dir, "paddle_first_records.json")
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(lines[:5], f, ensure_ascii=False, indent=2)
            print(f"  前 5 条原始记录已写入: {dump_path}")
        except OSError:
            pass

    if work_dir and not args.keep_temp:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
    elif work_dir:
        print(f"  临时目录(保留): {work_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
