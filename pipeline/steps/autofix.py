"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line

DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMAGE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def fix(ds, issues, cfg):
    fixes = []
    err_issues = [i for i in issues if i.severity == ERROR]

    # 1. Sửa tên lớp trong data.yaml (BAD_CLASS_NAME)
    if any(i.code == "BAD_CLASS_NAME" for i in err_issues):
        new_names = list(cfg["classes"])
        expected_map = {idx: name for idx, name in enumerate(new_names)}
        if ds.yaml_names() != expected_map:
            d = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) if ds.yaml_path.exists() else {}
            if not isinstance(d, dict):
                d = {}
            old_names = d.get("names")
            d["names"] = new_names
            if "nc" in d:
                d["nc"] = len(new_names)
            ds.yaml_path.parent.mkdir(parents=True, exist_ok=True)
            ds.yaml_path.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
            fixes.append({
                "image": "data.yaml",
                "line": None,
                "action": "rename_classes",
                "before": str(old_names),
                "after": str(new_names),
            })

    # 2. Xóa ảnh + nhãn với các lỗi không thể cứu ở cửa vào
    removed_stems = set()
    for iss in err_issues:
        if iss.code in REMOVE_IMAGE_CODES or iss.code.startswith("DUP_IMAGE_"):
            stem = iss.image
            if stem in removed_stems:
                continue
            removed_stems.add(stem)
            img_p = ds.image_path(stem)
            lbl_p = ds.label_path(stem)
            if (img_p and img_p.exists()) or lbl_p.exists():
                before_name = img_p.name if (img_p and img_p.exists()) else lbl_p.name
                if img_p and img_p.exists():
                    img_p.unlink()
                if lbl_p.exists():
                    lbl_p.unlink()
                fixes.append({
                    "image": stem,
                    "line": None,
                    "action": "remove_image",
                    "before": before_name,
                    "after": "(đã xoá)",
                })

    # 3. Ghi nhận ảnh thiếu file nhãn (không tạo file rỗng)
    needs_label_stems = set()
    for iss in err_issues:
        if iss.code == "MISSING_LABEL_FILE":
            stem = iss.image
            if stem in removed_stems or stem in needs_label_stems:
                continue
            if not ds.label_path(stem).exists():
                needs_label_stems.add(stem)
                fixes.append({
                    "image": stem,
                    "line": None,
                    "action": "needs_label",
                    "before": "(không có file)",
                    "after": "chuyển người gán",
                })

    # 4. Gom lỗi theo từng file nhãn và xử lý theo số dòng gốc
    line_issues_by_stem = defaultdict(lambda: defaultdict(set))
    for iss in err_issues:
        if iss.image in removed_stems or iss.line is None:
            continue
        if iss.code in DROP_CODES or iss.code == "BOX_OUT_OF_IMAGE":
            line_issues_by_stem[iss.image][iss.line].add(iss.code)

    for stem, lines_map in line_issues_by_stem.items():
        lbl_p = ds.label_path(stem)
        if not lbl_p.exists():
            continue

        raw_lines = lbl_p.read_text(encoding="utf-8", errors="replace").splitlines()
        new_lines = list(raw_lines)
        file_changed = False

        for line_no in sorted(lines_map.keys()):
            if not (1 <= line_no <= len(raw_lines)):
                continue
            orig = raw_lines[line_no - 1]
            if not orig.strip():
                continue

            codes = lines_map[line_no]
            if codes & DROP_CODES:
                new_lines[line_no - 1] = None
                file_changed = True
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "drop_line",
                    "before": orig.strip(),
                    "after": "(xoá dòng)",
                })
            elif "BOX_OUT_OF_IMAGE" in codes:
                try:
                    cls, cx, cy, w, h = parse_yolo_line(orig)
                except ValueError:
                    new_lines[line_no - 1] = None
                    file_changed = True
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": orig.strip(),
                        "after": "(xoá dòng)",
                    })
                    continue

                x1, y1 = cx - w / 2.0, cy - h / 2.0
                x2, y2 = cx + w / 2.0, cy + h / 2.0
                if 0.0 <= x1 and 0.0 <= y1 and x2 <= 1.0 and y2 <= 1.0:
                    continue

                cx1 = max(0.0, min(1.0, x1))
                cy1 = max(0.0, min(1.0, y1))
                cx2 = max(0.0, min(1.0, x2))
                cy2 = max(0.0, min(1.0, y2))
                nw, nh = cx2 - cx1, cy2 - cy1

                if nw <= 1e-9 or nh <= 1e-9:
                    new_lines[line_no - 1] = None
                    file_changed = True
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": orig.strip(),
                        "after": "(xoá dòng)",
                    })
                else:
                    ncx, ncy = (cx1 + cx2) / 2.0, (cy1 + cy2) / 2.0
                    clipped_str = f"{cls} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"
                    new_lines[line_no - 1] = clipped_str
                    file_changed = True
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "clip_box",
                        "before": orig.strip(),
                        "after": clipped_str,
                    })

        if file_changed:
            kept = [ln for ln in new_lines if ln is not None]
            lbl_p.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

    return fixes