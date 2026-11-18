"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q
"""
from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed_set = set(reviewed)
    hold_thresh = cfg["gate"]["warn_ratio_hold"]

    valid_issues = [i for i in issues if i.image in stems]

    n_errors = sum(1 for i in valid_issues if i.severity == ERROR)
    warn_images = {i.image for i in valid_issues if i.severity == WARN and i.image not in reviewed_set}

    n_warn_images = len(warn_images)
    n_images = len(stems)
    warn_ratio = round(n_warn_images / n_images, 4) if n_images > 0 else 0.0

    reasons = []
    if n_errors >= 1:
        decision = "Rework"
        reasons.append(f"Còn {n_errors} lỗi bắt buộc (ERROR) cần xử lý.")
        if warn_ratio >= hold_thresh:
            reasons.append(f"Tỉ lệ ảnh cảnh báo {warn_ratio:.4f} ({n_warn_images}/{n_images}) >= ngưỡng {hold_thresh}.")
    elif warn_ratio >= hold_thresh:
        decision = "Hold"
        reasons.append(f"Tỉ lệ ảnh cảnh báo {warn_ratio:.4f} ({n_warn_images}/{n_images}) >= ngưỡng {hold_thresh}.")
    else:
        decision = "Release"
        reasons.append(f"Không còn lỗi bắt buộc; tỉ lệ ảnh cảnh báo {warn_ratio:.4f} ({n_warn_images}/{n_images}) < ngưỡng {hold_thresh}.")

    return {
        "decision": decision,
        "n_errors": n_errors,
        "n_warn_images": n_warn_images,
        "n_images": n_images,
        "warn_ratio": warn_ratio,
        "reasons": reasons,
    }