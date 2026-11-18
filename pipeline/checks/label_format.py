"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    c = cfg["label_format"]
    issues = []

    for lbl_path in ds.label_files():
        stem = lbl_path.stem
        seen = []
        sz = ds.image_size(stem)

        for line_no, text in ds.read_label_lines(stem) or []:
            # 1. Lỗi cấu trúc: gặp lỗi thì báo và bỏ qua kiểm tra hình học dòng này
            try:
                cls, cx, cy, w, h = parse_yolo_line(text)
            except ValueError as e:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, str(e), line=line_no))
                continue

            if not (0 <= cls < len(ds.classes)):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"id lớp ngoài phạm vi: {cls}", line=line_no))
                continue

            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, f"kích thước box <= 0 (w={w}, h={h})", line=line_no))
                continue

            # 2. Lỗi hình học & cảnh báo
            box = (cx, cy, w, h)
            overflow = max(-(cx - w / 2), -(cy - h / 2), (cx + w / 2) - 1.0, (cy + h / 2) - 1.0)
            if overflow > c["overflow_tol"]:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn mép ảnh {overflow:.4f}",
                        line=line_no,
                        extra={"overflow": round(overflow, 6)},
                    )
                )

            for prev_cls, prev_box in seen:
                if prev_cls == cls and iou_xywh(box, prev_box) > c["dup_box_iou"]:
                    issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, f"trùng box với dòng trước (lớp {cls})", line=line_no))
                    break
            seen.append((cls, box))

            if sz is not None:
                min_side = min(w * sz[0], h * sz[1])
                if min_side < c["min_box_px"]:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem, f"box quá nhỏ ({min_side:.1f}px)", line=line_no))

            if w * h > c["max_box_frac"]:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem, f"box quá lớn ({w * h:.2f} diện tích ảnh)", line=line_no))

    return issues