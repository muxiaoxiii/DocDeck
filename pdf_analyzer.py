"""
pdf_analyzer.py
- 集中式 PDF 分析模块（只负责“读取/检测/分析/报告”，不做任何写入/删除）
"""

from __future__ import annotations

import os
from typing import List, Dict, Any, Optional
import argparse
import json

# 轻量依赖：PyPDF2 读取基础信息
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

import logging
logger = logging.getLogger(__name__)


class PdfAnalyzer:
    """集中式 PDF 分析器"""

    # --- 基础信息 ---
    def get_pdf_page_count(self, path: str) -> int:
        try:
            reader = PdfReader(path)
            return len(reader.pages)
        except (FileNotFoundError, PdfReadError) as e:
            logger.warning(f"[Page Count] Cannot read {path}: {e}")
        except Exception as e:
            logger.exception(f"[Page Count] Unexpected error for {path}: {e}")
        return 0

    def get_pdf_file_size_mb(self, path: str) -> float:
        try:
            size_bytes = os.path.getsize(path)
            return round(size_bytes / (1024 * 1024), 2)
        except FileNotFoundError as e:
            logger.warning(f"[File Size] File not found: {path}: {e}")
        except Exception as e:
            logger.exception(f"[File Size] Error reading {path}: {e}")
        return 0.0

    def get_pdf_metadata(self, path: str) -> dict:
        try:
            reader = PdfReader(path)
            meta = reader.metadata
            return {
                "title": meta.title if meta else None,
                "author": meta.author if meta else None,
                "creator": meta.creator if meta else None,
                "producer": meta.producer if meta else None,
                "created": meta.get("/CreationDate", None) if meta else None,
            }
        except (FileNotFoundError, PdfReadError) as e:
            logger.warning(f"[Metadata] Cannot extract from {path}: {e}")
        except Exception as e:
            logger.exception(f"[Metadata] Unexpected error for {path}: {e}")
        return {}

    def get_pdf_fonts(self, path: str, pages: int = 1) -> dict:
        fonts: List[dict] = []
        try:
            reader = PdfReader(path)
            pages_to_check = min(pages, len(reader.pages))
            for i in range(pages_to_check):
                page = reader.pages[i]
                page_fonts: List[str] = []
                resources = page.get("/Resources", {})
                if "/Font" in resources:
                    font_dict = resources["/Font"]
                    if hasattr(font_dict, "keys"):
                        page_fonts = list(font_dict.keys())
                fonts.append({"page": i + 1, "fonts": page_fonts})
        except (FileNotFoundError, PdfReadError) as e:
            logger.warning(f"[Fonts] Failed to read {path}: {e}")
        except Exception as e:
            logger.exception(f"[Fonts] Unexpected error in {path}: {e}")
        return {"pages": fonts}

    # --- Artifact 提取 ---
    def extract_artifact_headers_footers(self, path: str, max_pages: int = 10) -> dict:
        import pikepdf
        from pikepdf import Name
        import re

        result = {"pages": []}
        try:
            with pikepdf.open(path) as pdf:
                pages_to_scan = min(max_pages, len(pdf))
                for i, page in enumerate(pdf.pages[:pages_to_scan]):
                    content_obj = page.obj.get(Name('/Contents'))
                    if content_obj is None:
                        result["pages"].append({"page": i + 1, "header": [], "footer": []})
                        continue
                    if isinstance(content_obj, pikepdf.Array):
                        content_bytes = b"".join([c.read_bytes() for c in content_obj])
                    elif isinstance(content_obj, pikepdf.Stream):
                        content_bytes = content_obj.read_bytes()
                    else:
                        content_bytes = b""
                    text = content_bytes.decode('latin-1', errors='ignore')

                    header_pattern = r"/Artifact\s*<<[^>]*?/Subtype\s*/Header[^>]*?>>\s*BDC([\s\S]*?)EMC"
                    footer_pattern = r"/Artifact\s*<<[^>]*?/Subtype\s*/Footer[^>]*?>>\s*BDC([\s\S]*?)EMC"
                    simple_header_pattern = r"BDC\s*<<[^>]*?/Subtype\s*/Header[^>]*?>>([\s\S]*?)EMC"
                    simple_footer_pattern = r"BDC\s*<<[^>]*?/Subtype\s*/Footer[^>]*?>>([\s\S]*?)EMC"

                    def _extract_strings(segment: str) -> List[str]:
                        raw = re.findall(r"\((.*?)(?<!\\)\)", segment, re.DOTALL)
                        out = [s.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\") for s in raw]
                        return [s.strip() for s in out if s.strip()]

                    headers: List[str] = []
                    footers: List[str] = []
                    for pattern in [header_pattern, simple_header_pattern]:
                        for seg in re.findall(pattern, text, re.DOTALL):
                            headers.extend(_extract_strings(seg))
                    for pattern in [footer_pattern, simple_footer_pattern]:
                        for seg in re.findall(pattern, text, re.DOTALL):
                            footers.extend(_extract_strings(seg))
                    headers = list(set(headers))
                    footers = list(set(footers))
                    result["pages"].append({"page": i + 1, "header": headers, "footer": footers})
            return result
        except Exception as e:
            logger.warning(f"[Artifact] Extraction failed for {path}: {e}")
            return result

    # --- 启发式检测 ---
    def detect_headers_footers_heuristic(self, path: str, max_pages: int = 10) -> dict:
        try:
            import fitz
            doc = fitz.open(path)
            results: Dict[str, Any] = {"pages": [], "header_candidates": [], "footer_candidates": []}
            pages_to_analyze = min(max_pages, len(doc))
            all_text_blocks: List[Dict[str, Any]] = []
            all_texts: List[str] = []
            for page_num in range(pages_to_analyze):
                page = doc[page_num]
                blocks = page.get_text("dict")
                for block in blocks.get("blocks", []):
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                txt = span.get("text", "").strip()
                                if not txt:
                                    continue
                                all_texts.append(txt)
                                all_text_blocks.append({
                                    "page": page_num + 1,
                                    "text": txt,
                                    "bbox": span.get("bbox"),
                                    "size": span.get("size", 0),
                                    "font": span.get("font", "")
                                })
            if not all_text_blocks:
                doc.close()
                return results

            pages_data: Dict[int, List[Dict[str, Any]]] = {}
            for b in all_text_blocks:
                pages_data.setdefault(b["page"], []).append(b)

            # 统计候选项所需的聚合容器
            from collections import Counter, defaultdict
            header_occurrences: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            footer_occurrences: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

            def _label_text(txt: str) -> List[str]:
                labels: List[str] = []
                # 页码模式（纯数字或形如 `10`/`1 / 10`）
                if txt.strip().isdigit():
                    labels.append("pageno")
                # 含有日期关键词
                if "日期" in txt or ":" in txt:
                    labels.append("date")
                return labels

            for page_num in sorted(pages_data.keys()):
                page_blocks = pages_data[page_num]
                page_height = doc[page_num - 1].rect.height
                page_width = doc[page_num - 1].rect.width
                header_zone = page_height * 0.10
                footer_zone = page_height * 0.90
                headers: List[str] = []
                footers: List[str] = []
                for b in page_blocks:
                    y0 = b["bbox"][1] if b.get("bbox") else 0
                    text = b["text"]
                    if len(text) < 2:
                        continue
                    if y0 < header_zone:
                        if self._is_likely_header_footer(text, b.get("size", 0), b.get("font", ""), all_texts):
                            headers.append(text)
                            # 记录候选的详细位置信息
                            header_occurrences[text].append({
                                "page": page_num,
                                "bbox": b.get("bbox"),
                                "width": page_width,
                                "height": page_height,
                            })
                    elif y0 > footer_zone:
                        if self._is_likely_header_footer(text, b.get("size", 0), b.get("font", ""), all_texts):
                            footers.append(text)
                            footer_occurrences[text].append({
                                "page": page_num,
                                "bbox": b.get("bbox"),
                                "width": page_width,
                                "height": page_height,
                            })
                headers = list(set(headers))
                footers = list(set(footers))
                results["pages"].append({"page": page_num, "headers": headers, "footers": footers})

            # 构建候选列表（text + 代表性 bbox + repeating + labels + count）
            def _first_occ(occ_list: List[Dict[str, Any]]) -> Dict[str, Any]:
                return occ_list[0] if occ_list else {"page": 1, "bbox": [0, 0, 0, 0], "width": 0, "height": 0}

            for txt, occ_list in header_occurrences.items():
                pages_set = {o["page"] for o in occ_list}
                rep = len(pages_set) >= 2
                occ0 = _first_occ(occ_list)
                results["header_candidates"].append({
                    "text": txt,
                    "count": len(occ_list),
                    "repeating": rep,
                    "labels": _label_text(txt),
                    "bbox": {
                        "x0": occ0["bbox"][0] if occ0.get("bbox") else 0,
                        "y0": occ0["bbox"][1] if occ0.get("bbox") else 0,
                        "x1": occ0["bbox"][2] if occ0.get("bbox") else 0,
                        "y1": occ0["bbox"][3] if occ0.get("bbox") else 0,
                        "page": occ0.get("page", 1),
                        "width": occ0.get("width", 0),
                        "height": occ0.get("height", 0),
                    }
                })

            for txt, occ_list in footer_occurrences.items():
                pages_set = {o["page"] for o in occ_list}
                rep = len(pages_set) >= 2
                occ0 = _first_occ(occ_list)
                results["footer_candidates"].append({
                    "text": txt,
                    "count": len(occ_list),
                    "repeating": rep,
                    "labels": _label_text(txt),
                    "bbox": {
                        "x0": occ0["bbox"][0] if occ0.get("bbox") else 0,
                        "y0": occ0["bbox"][1] if occ0.get("bbox") else 0,
                        "x1": occ0["bbox"][2] if occ0.get("bbox") else 0,
                        "y1": occ0["bbox"][3] if occ0.get("bbox") else 0,
                        "page": occ0.get("page", 1),
                        "width": occ0.get("width", 0),
                        "height": occ0.get("height", 0),
                    }
                })
            doc.close()
            return results
        except Exception as e:
            logger.warning(f"Heuristic header/footer detection failed: {e}")
            return {"pages": []}

    def _is_likely_header_footer(self, text: str, font_size: float, font_name: str, all_texts: List[str]) -> bool:
        if not text or len(text.strip()) < 2:
            return False
        if text.isdigit() and len(text) <= 3:
            return False
        if len(text) > 100:
            return False
        content_indicators = ['。', '，', '！', '？', '；', '：', '（', '）', '【', '】', '、']
        if any(ch in text for ch in content_indicators):
            return False
        if all_texts.count(text) < 2:
            return False
        keywords = ['page', '第', '页', 'of', '证据', '日期', 'confidential', 'draft', 'final', 'version']
        text_lower = text.lower()
        if any(k in text_lower for k in keywords):
            return True
        if 0 < font_size < 16:
            return True
        common_fonts = ['arial', 'helvetica', 'times', 'simsun', 'simhei']
        if any(f in font_name.lower() for f in common_fonts):
            return True
        return False

    # --- 融合输出 ---
    def extract_all_headers_footers(self, path: str, max_pages: int = 10) -> dict:
        artifact_result = self.extract_artifact_headers_footers(path, max_pages)
        heuristic_result = self.detect_headers_footers_heuristic(path, max_pages)
        merged_result = {"pages": []}
        art_pages = {p["page"]: p for p in artifact_result.get("pages", [])}
        heu_pages = {p["page"]: p for p in heuristic_result.get("pages", [])}
        all_pages = set(art_pages.keys()) | set(heu_pages.keys())
        for pn in sorted(all_pages):
            headers: List[str] = []
            footers: List[str] = []
            if pn in art_pages:
                headers.extend(art_pages[pn].get("header", []))
                footers.extend(art_pages[pn].get("footer", []))
            if pn in heu_pages:
                headers.extend(heu_pages[pn].get("headers", []))
                footers.extend(heu_pages[pn].get("footers", []))
            headers = self._clean_text_list(headers)
            footers = self._clean_text_list(footers)
            merged_result["pages"].append({"page": pn, "header": headers, "footer": footers})
        return merged_result

    def _clean_text_list(self, items: List[str]) -> List[str]:
        out: List[str] = []
        seen = set()
        for t in items:
            if not t or len(t.strip()) < 2:
                continue
            if t.strip().isdigit() and len(t.strip()) <= 3:
                continue
            if len(t.strip()) > 100:
                continue
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    # --- 汇总报告 ---
    def analyze(self, path: str, max_pages: int = 10) -> dict:
        report: Dict[str, Any] = {
            "path": path,
            "size_mb": self.get_pdf_file_size_mb(path),
            "metadata": self.get_pdf_metadata(path),
            "page_count": self.get_pdf_page_count(path),
        }
        report["artifacts"] = self.extract_artifact_headers_footers(path, max_pages)
        report["heuristic"] = self.detect_headers_footers_heuristic(path, max_pages)
        report["fonts"] = self.get_pdf_fonts(path, pages=1)
        # 建议（示例）
        suggestions: List[str] = []
        has_structured_header = any(p.get("header") for p in report["artifacts"].get("pages", []))
        has_structured_footer = any(p.get("footer") for p in report["artifacts"].get("pages", []))
        report["has_structured_header"] = bool(has_structured_header)
        report["has_structured_footer"] = bool(has_structured_footer)
        if has_structured_header or has_structured_footer:
            suggestions.append("检测到 Artifact 页眉/页脚：可直接采用结构化方案进行可替换编辑。")
        if not report["fonts"].get("pages", [{}])[0].get("fonts"):
            suggestions.append("未发现 Type0 字体：若需中文一致性输出，建议写入 Type0/CID + ToUnicode。")
        report["suggestions"] = suggestions
        # 直接在顶层透出候选列表，便于处理模块消费
        report["header_candidates"] = report["heuristic"].get("header_candidates", [])
        report["footer_candidates"] = report["heuristic"].get("footer_candidates", [])
        return report


def _cli_main():
    parser = argparse.ArgumentParser(description="Analyze PDF headers/footers and fonts")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to analyze (default: 10)")
    parser.add_argument("--json", dest="json_out", help="Write JSON report to file")
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"[ERROR] File not found: {args.pdf}")
        raise SystemExit(1)

    analyzer = PdfAnalyzer()
    report = analyzer.analyze(args.pdf, max_pages=args.max_pages)

    # 简要控制台输出
    print("\n=== PDF Analysis Report ===")
    print(f"Path:        {report['path']}")
    print(f"Size (MB):   {report['size_mb']}")
    print(f"Pages:       {report['page_count']}")
    print(f"Metadata:    {report['metadata']}")
    print(f"Artifact H/F: H={report.get('has_structured_header')} F={report.get('has_structured_footer')}")
    print("Header candidates (top):")
    for c in report.get("header_candidates", [])[:5]:
        print(f"  - {c.get('text')}  (count={c.get('count')}, repeating={c.get('repeating')}, labels={c.get('labels')})")
    print("Footer candidates (bottom):")
    for c in report.get("footer_candidates", [])[:5]:
        print(f"  - {c.get('text')}  (count={c.get('count')}, repeating={c.get('repeating')}, labels={c.get('labels')})")
    print("Suggestions:")
    for s in report.get("suggestions", []):
        print(f"  - {s}")

    if args.json_out:
        try:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\nJSON report written to: {args.json_out}")
        except Exception as e:
            print(f"[WARN] Failed to write JSON: {e}")


if __name__ == "__main__":
    _cli_main()


