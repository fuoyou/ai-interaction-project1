"""
检测本机 PPTX→PDF 的三种方式是否可用，并输出耗时。

用法（在 fanya-ai-backend 目录下）:
  conda activate fanya-backend
  cd fanya-ai-backend
  python scripts/test_pptx_to_pdf_methods.py "D:\\path\\to\\1. 绪论(1).pptx"

未传参数时，尝试当前目录下的: 1. 绪论(1).pptx
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time

# 保证能 import utils
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from utils.file_utils import (  # noqa: E402
    _ppt_to_pdf_libreoffice,
    _ppt_to_pdf_powerpoint_com,
)


def _try_wps_com(pptx_path: str, pdf_path: str) -> tuple[bool, str]:
    """金山 WPS 演示 COM（与 file_utils.ppt_to_pdf 中 WPS 段一致）。"""
    try:
        import comtypes.client
        import pythoncom
    except ImportError as e:
        return False, f"未安装 comtypes: {e}"

    def _kill_wps():
        for proc in ["wps.exe", "wpp.exe", "et.exe"]:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", proc],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass

    pythoncom.CoInitialize()
    abs_in = os.path.abspath(pptx_path)
    abs_pdf = os.path.abspath(pdf_path)
    wps_com_names = [
        "KWPP.Application",
        "WPP.Application",
        "Kwpp.Application",
        "wpp.Application",
    ]
    last_err = "未尝试"
    try:
        _kill_wps()
        time.sleep(0.3)
        for com_name in wps_com_names:
            app = None
            presentation = None
            try:
                app = comtypes.client.CreateObject(com_name)
                app.Visible = 1
                presentation = app.Presentations.Open(abs_in)
                presentation.ExportAsFixedFormat(abs_pdf, 2)
                presentation.Close()
                app.Quit()
                if os.path.exists(abs_pdf) and os.path.getsize(abs_pdf) > 0:
                    return True, com_name
            except Exception as e:
                last_err = f"{com_name}: {e}"
                if presentation:
                    try:
                        presentation.Close()
                    except Exception:
                        pass
                if app:
                    try:
                        app.Quit()
                    except Exception:
                        pass
            finally:
                _kill_wps()
                time.sleep(0.2)
        return False, last_err
    finally:
        try:
            import pythoncom

            pythoncom.CoUninitialize()
        except Exception:
            pass
        _kill_wps()


def _fmt_sec(t: float) -> str:
    return f"{t:.2f}s"


def main() -> int:
    default_name = "1. 绪论(1).pptx"
    if len(sys.argv) >= 2:
        src = os.path.abspath(sys.argv[1])
    else:
        src = os.path.abspath(os.path.join(os.getcwd(), default_name))

    if not os.path.isfile(src):
        print(f"[错误] 找不到测试文件: {src}")
        print("用法: python scripts/test_pptx_to_pdf_methods.py <pptx完整路径>")
        return 1

    print(f"测试文件: {src}")
    print(f"大小: {os.path.getsize(src) / 1024 / 1024:.2f} MB")
    print("-" * 72)

    tmp = tempfile.mkdtemp(prefix="pptx_pdf_probe_")
    try:
        # 三份拷贝，避免输出 PDF 互相覆盖
        w_px = os.path.join(tmp, "w_input.pptx")
        m_px = os.path.join(tmp, "m_input.pptx")
        l_px = os.path.join(tmp, "l_input.pptx")
        shutil.copy2(src, w_px)
        shutil.copy2(src, m_px)
        shutil.copy2(src, l_px)

        w_pdf = os.path.join(tmp, "w_input.pdf")
        m_pdf = os.path.join(tmp, "m_input.pdf")
        l_pdf = os.path.join(tmp, "l_input.pdf")

        results: list[tuple[str, bool, float, str, int]] = []

        # 1) WPS
        t0 = time.perf_counter()
        ok, msg = _try_wps_com(w_px, w_pdf)
        dt = time.perf_counter() - t0
        sz = os.path.getsize(w_pdf) if ok and os.path.isfile(w_pdf) else 0
        results.append(("WPS 演示 COM", ok, dt, msg, sz))

        # 2) Microsoft PowerPoint
        t0 = time.perf_counter()
        out = _ppt_to_pdf_powerpoint_com(m_px, m_pdf)
        dt = time.perf_counter() - t0
        ok = bool(out and os.path.isfile(m_pdf) and os.path.getsize(m_pdf) > 0)
        sz = os.path.getsize(m_pdf) if ok else 0
        results.append(
            (
                "Microsoft PowerPoint COM",
                ok,
                dt,
                "成功" if ok else "失败（见上方日志）",
                sz,
            )
        )

        # 3) LibreOffice
        t0 = time.perf_counter()
        out = _ppt_to_pdf_libreoffice(l_px, l_pdf)
        dt = time.perf_counter() - t0
        ok = bool(out and os.path.isfile(l_pdf) and os.path.getsize(l_pdf) > 0)
        sz = os.path.getsize(l_pdf) if ok else 0
        results.append(
            (
                "LibreOffice (soffice)",
                ok,
                dt,
                "成功" if ok else "失败（见上方日志）",
                sz,
            )
        )

        # 汇总表
        print(f"{'方式':<28} {'结果':<8} {'耗时':<10} {'PDF大小':<12} {'说明'}")
        print("-" * 72)
        for name, ok, dt, note, sz in results:
            status = "可行" if ok else "不可行"
            size_s = f"{sz / 1024:.1f} KB" if sz else "-"
            note_short = (note[:40] + "…") if len(str(note)) > 42 else str(note)
            print(f"{name:<28} {status:<8} {_fmt_sec(dt):<10} {size_s:<12} {note_short}")

        print("-" * 72)
        ok_methods = [r[0] for r in results if r[1]]
        if ok_methods:
            print("本机当前可行:", "、".join(ok_methods))
            print(f"临时输出目录（可手动删除）: {tmp}")
        else:
            print("三种方式均失败：请安装 WPS 演示 / Microsoft Office / LibreOffice 之一，并安装 comtypes（WPS/PPT）。")
            shutil.rmtree(tmp, ignore_errors=True)
            return 2

        return 0
    except Exception as e:
        print(f"[异常] {e}")
        import traceback

        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
