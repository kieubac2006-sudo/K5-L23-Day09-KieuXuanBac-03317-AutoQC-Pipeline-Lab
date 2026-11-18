"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★

Test:  pytest tests/test_second_opinion.py -q
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    c = cfg["second_opinion"]
    issues = []

    for img_path in ds.image_files():
        stem = img_path.stem
        if stem not in preds or not ds.label_path(stem).exists():
            continue

        sz = ds.image_size(stem)
        if sz is None:
            continue
        img_w, img_h = sz

        # Đọc nhãn hợp lệ kèm giữ nguyên số dòng gốc
        labeled_boxes = []
        for line_no, text in ds.read_label_lines(stem) or []:
            try:
                b = parse_yolo_line(text)
            except ValueError:
                continue
            if 0 <= b[0] < len(ds.classes):
                labeled_boxes.append((line_no, b[0], (b[1], b[2], b[3], b[4])))

        raw_preds = preds[stem]

        # 1. Chiều dự đoán -> nhãn gốc
        for r in raw_preds:
            p_cls, p_conf, px, py, pw, ph = int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])
            area_px = (pw * img_w) * (ph * img_h)
            if p_conf < c["conf"] or area_px < c["min_area_px"]:
                continue

            p_box = (px, py, pw, ph)
            cands = []
            for _, gt_cls, gt_box in labeled_boxes:
                iou = iou_xywh(p_box, gt_box)
                if iou >= c["iou_missing"]:
                    cands.append((iou, gt_cls))

            if not cands:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_MISSING",
                        stem,
                        f"model phát hiện lớp {p_cls} (conf={p_conf:.2f}) nhưng không có nhãn",
                        extra={"conf": round(p_conf, 4)},
                    )
                )
                continue

            same_ious = [iou for iou, gt_cls in cands if gt_cls == p_cls]
            if same_ious:
                best_same = max(same_ious)
                if best_same < c["iou_loose"]:
                    issues.append(
                        Issue(
                            "second_opinion",
                            WARN,
                            "POSSIBLE_LOOSE_BOX",
                            stem,
                            f"box lớp {p_cls} lỏng/lệch (IoU={best_same:.2f})",
                            extra={"conf": round(p_conf, 4), "iou": round(best_same, 4)},
                        )
                    )
            else:
                best_diff = max(iou for iou, _ in cands)
                if best_diff >= c["iou_match"]:
                    issues.append(
                        Issue(
                            "second_opinion",
                            WARN,
                            "POSSIBLE_WRONG_CLASS",
                            stem,
                            f"nghi nhầm lớp: model dự đoán lớp {p_cls} (IoU={best_diff:.2f})",
                            extra={"conf": round(p_conf, 4), "iou": round(best_diff, 4)},
                        )
                    )

        # 2. Chiều nhãn gốc -> dự đoán (tìm box thừa)
        fp_preds = [r for r in raw_preds if float(r[1]) >= c["fp_conf"]]
        for line_no, gt_cls, gt_box in labeled_boxes:
            max_iou = max(
                (iou_xywh(gt_box, (float(r[2]), float(r[3]), float(r[4]), float(r[5]))) for r in fp_preds),
                default=0.0,
            )
            if max_iou < c["iou_missing"]:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_FALSE_POS",
                        stem,
                        f"nhãn lớp {gt_cls} không khớp dự đoán nào (max IoU={max_iou:.2f})",
                        line=line_no,
                        extra={"iou": round(max_iou, 4)},
                    )
                )

    return issues