import io, os, yaml, math
import numpy as np
import pandas as pd
import fitz  # PyMuPDF
import cv2
from PIL import Image
import pytesseract

# If Tesseract is not on PATH (Windows), set like:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def render_pdf_page(pdf_path: str, page_index: int, dpi: int = 220):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def relative_crop(img: Image.Image, left: float, top: float, right: float, bottom: float) -> Image.Image:
    w, h = img.size
    box = (int(left*w), int(top*h), int(right*w), int(bottom*h))
    return img.crop(box), box

def to_cv(img: Image.Image):
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def to_pil(arr):
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

def mask_hsv(img_bgr, h_min, h_max, s_min, s_max, v_min, v_max):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([h_min, s_min, v_min], dtype=np.uint8)
    upper = np.array([h_max, s_max, v_max], dtype=np.uint8)
    m = cv2.inRange(hsv, lower, upper)
    return m

def detect_baseline(plot_bgr):
    # Detect the dominant horizontal axis line (near center)
    gray = cv2.cvtColor(plot_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=120, minLineLength=int(plot_bgr.shape[1]*0.5), maxLineGap=10)
    y_candidates = []
    if lines is not None:
        for x1,y1,x2,y2 in lines[:,0]:
            if abs(y1-y2) <= 2:  # horizontal
                y_candidates.append(y1)
    if not y_candidates:
        # fallback: assume baseline is middle
        return plot_bgr.shape[0]//2
    # choose the line closest to the horizontal mid (often x-axis)
    mid = plot_bgr.shape[0]//2
    y = min(y_candidates, key=lambda yy: abs(yy-mid))
    return int(y)

def bars_from_mask(mask, baseline_y, x_smooth=5):
    # Collapse mask vertically to find bar clusters across x
    cols = mask.shape[1]
    col_sum = (mask>0).sum(axis=0)
    # Smooth to merge thin gaps
    kernel = np.ones(x_smooth, dtype=np.float32)/x_smooth
    smooth = np.convolve(col_sum, kernel, mode="same")
    thr = np.percentile(smooth, 75) * 0.3
    is_bar = smooth > thr
    # Identify contiguous segments
    bars = []
    in_seg = False
    start = 0
    for i, val in enumerate(is_bar):
        if val and not in_seg:
            in_seg = True; start = i
        elif not val and in_seg:
            in_seg = False; bars.append((start, i-1))
    if in_seg: bars.append((start, cols-1))
    # For each segment, compute signed height vs baseline
    heights = []
    for (x1,x2) in bars:
        seg = mask[:, x1:x2+1]
        ys = np.where(seg>0)[0]
        if ys.size == 0:
            heights.append((x1,x2,0.0)); continue
        y_top = ys.min()
        y_bot = ys.max()
        if y_top < baseline_y:  # positive (above baseline)
            h_pos = baseline_y - y_top
        else:
            h_pos = 0
        if y_bot > baseline_y:  # negative part
            h_neg = y_bot - baseline_y
        else:
            h_neg = 0
        # prefer net height: positive minus negative (handle both sides)
        net = h_pos - h_neg
        heights.append((x1,x2, float(net)))
    return heights

def scale_heights_to_values(heights, px_per_unit):
    # px_per_unit: pixels per 1 unit (e.g., $1bn)
    values = []
    for (x1,x2,h) in heights:
        values.append(((x1+x2)//2, h/px_per_unit))
    return values

def estimate_px_per_unit(plot_bgr, y_min, y_max, baseline_y):
    # Derive px_per_unit from total pixel span between min and max reference.
    # Here we approximate: positive span = distance from baseline to top edge; negative to bottom edge.
    # If both positive and negative ranges exist, choose the larger absolute span.
    h = plot_bgr.shape[0]
    pos_span_px = baseline_y - 0
    neg_span_px = h - baseline_y
    pos_units = max(0.0001, y_max if y_max>0 else 0.0001)
    neg_units = abs(y_min) if y_min<0 else 0.0001
    # choose weighted average if both sides exist
    px_per_unit_pos = pos_span_px / pos_units
    px_per_unit_neg = neg_span_px / neg_units
    # prefer pos if most charts are positive range dominated; blend if both non-trivial
    if y_min < 0 and y_max > 0:
        return (px_per_unit_pos + px_per_unit_neg) / 2.0
    return px_per_unit_pos

def extract_bars_series(plot_img: Image.Image, hsv_thresh: dict, y_min: float, y_max: float):
    bgr = to_cv(plot_img)
    base_y = detect_baseline(bgr)
    mask = mask_hsv(bgr, **hsv_thresh)
    # Morph to fill gaps
    mask = cv2.medianBlur(mask, 5)
    heights = bars_from_mask(mask, base_y)
    px_per_unit = estimate_px_per_unit(bgr, y_min, y_max, base_y)
    data = scale_heights_to_values(heights, px_per_unit)
    # sort by x
    data = sorted(data, key=lambda t: t[0])
    values = [v for _, v in data]
    return values, base_y, mask

def extract_line_series(plot_img: Image.Image, hsv_thresh: dict, y_min: float, y_max: float):
    # For line charts: for each x find the y with strongest mask presence
    bgr = to_cv(plot_img)
    h,w = bgr.shape[:2]
    mask = mask_hsv(bgr, **hsv_thresh)
    # thin to single-pixel-ish
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    ys = []
    for x in range(w):
        col = np.where(mask[:,x]>0)[0]
        if col.size==0:
            ys.append(np.nan)
        else:
            ys.append(float(np.median(col)))
    ys = np.array(ys)
    # infer baseline as center if unknown
    baseline_y = detect_baseline(bgr)
    px_per_unit = estimate_px_per_unit(bgr, y_min, y_max, baseline_y)
    # convert y pixel to value: y above baseline positive, below negative
    vals = []
    for y in ys:
        if np.isnan(y):
            vals.append(np.nan)
        else:
            diff = baseline_y - y
            vals.append(diff/px_per_unit)
    return vals, baseline_y, mask

def save_template(path:str, template:dict):
    with open(path, "w") as f:
        yaml.safe_dump(template, f)

def load_template(path:str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)