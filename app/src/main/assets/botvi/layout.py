"""مواقع المباني: تُعلَّم صورة صغيرة لكل مبنى مرة واحدة (من صفحة المعايرة)، ثم يبحث عنها البوت عند كل دخول
ويحدّث إحداثيات المهام (المبنى والزر السداسي) بدل الإحداثيات الثابتة. بايثون صرف بلا مكتبات."""
import os, json, time, heapq

BASE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(BASE, "layout.json")
Q = 4                                            # تصغير الصورة للبحث (شبكة 320x200)
TX0, TX1, TY0, TY1 = -44, 44, -32, 48             # صندوق صورة المبنى حول نقطة الضغط (إحداثيات 1280x800)
TW, TH = (TX1 - TX0) // Q, (TY1 - TY0) // Q       # 22 x 20 خلية
MASK_T, MASK_MIN = 22, 70                          # فرق الرمادي عن الخلفية لاعتبار البكسل من المبنى، وأقل عدد بكسلات لاستعمال القناع
SHIFT_TOL = 26                                   # أقصى فرق مسموح عن الإزاحة المشتركة (بكسل)
OK_SCORE = 18.0                                   # متوسط فرق الرمادي المقبول (أصغر = أدق)
MAP = {                                           # المهمة -> (ثابت المبنى، ثابت الزر السداسي) داخل وحدة المهمة
    "train": ("BUILD_XY", "HEX_XY"), "beast": ("BUILD_XY", "HEX_XY"), "border": ("BUILD_XY", "HEX_XY"),
    "dice": ("BUILD_XY", "HEX_XY"), "lunar": ("BUILD_XY", "HEX_XY"), "tower": ("BUILD_XY", "HEX_XY"),
    "workshop": ("BUILD_XY", "HEX_XY"), "heal": ("HOSP_XY", "HEX_XY"), "arena": ("ARENA_XY", "HEX_XY"),
    "lair": ("CAVE_XY", "HEX_XY"), "mana": ("MINE_XY", "HEX_XY"), "saga": ("STATUE_XY", "HEX_XY"),
}
ORIG = {}          # المهمة -> (مبنى، زر) الأصليان قبل أي تعديل
LOC = {}           # المهمة -> (x, y, نتيجة) آخر موقع مُحدَّد
T = [0.0]          # وقت آخر تحديث
SNAP = {"frame": None, "png": b"", "t": 0, "busy": ""}


def _load():
    try: return json.load(open(FILE, encoding="utf-8"))
    except Exception: return {}
DATA = _load()


def _save():
    try: json.dump(DATA, open(FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception: pass


def _gray(f):
    w, h = 1280 // Q, 800 // Q
    raw, off, s, fw = f.raw, f.off, f.s, f.w
    g = [0] * (w * h); k = 0
    for j in range(h):
        row = off + int((j * Q + 2) * s) * fw * 4
        for i in range(w):
            p = row + int((i * Q + 2) * s) * 4
            g[k] = (raw[p] * 3 + raw[p + 1] * 6 + raw[p + 2]) // 10; k += 1
    return g, w, h


def _crop(g, w, h, cx, cy):
    c0, r0 = (cx + TX0) // Q, (cy + TY0) // Q
    t = []
    for j in range(TH):
        r = min(h - 1, max(0, r0 + j))
        for i in range(TW):
            t.append(g[r * w + min(w - 1, max(0, c0 + i))])
    return t


def _find(g, w, h, tpl, cx, cy, rad):
    c0, r0 = (cx + TX0) // Q, (cy + TY0) // Q
    rem_x, rem_y = (cx + TX0) - c0 * Q, (cy + TY0) - r0 * Q
    cmin, cmax = max(0, c0 - rad // Q), min(w - TW, c0 + rad // Q)
    rmin, rmax = max(0, r0 - rad // Q), min(h - TH, r0 + rad // Q)
    sparse = [(i, j, tpl[j * TW + i]) for j in range(0, TH, 2) for i in range(0, TW, 2)]
    full = [(i, j, tpl[j * TW + i]) for j in range(TH) for i in range(TW)]
    med = sorted(tpl)[len(tpl) // 2]                                   # رمادي الخلفية السائد (عشب غالباً)
    mask = [(i, j, tpl[j * TW + i]) for j in range(TH) for i in range(TW) if abs(tpl[j * TW + i] - med) > MASK_T]
    if len(mask) >= MASK_MIN: full = mask; sparse = mask[::2]          # قارن جسم المبنى فقط: العشب الفارغ لم يعد يطابق صورة معظمها عشب

    def score(c, r, pts, keep):
        d = sorted([abs(g[(r + j) * w + c + i] - v) for i, j, v in pts])
        return sum(d[:keep]) / float(keep)

    ks, kf = int(len(sparse) * 0.75), int(len(full) * 0.75)
    cands = []
    for r in range(r0 - 2 * ((r0 - rmin) // 2), rmax + 1, 2):          # الشبكة تمر بالموضع الأصلي نفسه
        for c in range(c0 - 2 * ((c0 - cmin) // 2), cmax + 1, 2):
            cands.append((score(c, r, sparse, ks), c, r))
    cands = heapq.nsmallest(8, cands)                                  # أفضل 8 مرشحين ثم تدقيق كل منها بالصورة الكاملة
    best = (1e9, c0, r0); seen = set()
    for _, bc, br in cands:
        for r in range(max(rmin, br - 2), min(rmax, br + 2) + 1):
            for c in range(max(cmin, bc - 2), min(cmax, bc + 2) + 1):
                if (c, r) in seen: continue
                seen.add((c, r)); sc = score(c, r, full, kf)
                if sc < best[0]: best = (sc, c, r)
    sc, c, r = best
    return sc, c * Q - TX0 + rem_x, r * Q - TY0 + rem_y


def learn(key, f, x, y):
    g, w, h = _gray(f)
    tpl = _crop(g, w, h, int(x), int(y))
    mean = sum(tpl) / float(len(tpl)); var = sum((v - mean) ** 2 for v in tpl) / len(tpl)
    DATA[key] = {"x": int(x), "y": int(y), "t": tpl, "ref": [int(x), int(y)], "std": round(var ** 0.5, 1)}
    LOC[key] = (int(x), int(y), 0.0); T[0] = 0.0
    _save()
    return DATA[key]["std"]


def clear(key):
    DATA.pop(key, None); LOC.pop(key, None); _save()


def refresh(log, f=None):
    """يبحث عن كل مبنى مُعلَّم في اللقطة الحالية ويحدّث مواقعه."""
    import shizuku
    f = f or shizuku.frame()
    g, w, h = _gray(f)
    t0 = time.time(); ok = bad = 0; found = {}
    for key, d in list(DATA.items()):
        try:
            sc, x, y = _find(g, w, h, d["t"], d["x"], d["y"], 300)
            if sc > OK_SCORE: sc, x, y = _find(g, w, h, d["t"], d["x"], d["y"], 700)       # لم يوجد قريباً: ابحث في كل الشاشة
        except Exception as e:
            log("المباني: خطأ في البحث عن %s: %s" % (key, e)); bad += 1; continue
        x, y = int(round(x)), int(round(y))
        if sc <= OK_SCORE:
            found[key] = (x, y, sc)
        else:
            bad += 1; found[key] = None
            log("المباني: لم أجد %s بثقة (أفضل نتيجة %.1f)" % (_n(key), sc))
    # القلعة كلها تنزاح معاً: الإزاحة الوسيطة عن موقع التعليم تصحّح الشواذ وتعوّض ما لم يُوجد
    rel = [(v[0] - DATA[k]["ref"][0], v[1] - DATA[k]["ref"][1]) for k, v in found.items() if v]
    mx = my = None
    if len(rel) >= 3:
        mx = sorted(r[0] for r in rel)[len(rel) // 2]; my = sorted(r[1] for r in rel)[len(rel) // 2]
        log("المباني: إزاحة القلعة عن مكان التعليم (%+d,%+d) من %d مبنى" % (mx, my, len(rel)))
    for key, v in found.items():
        d = DATA[key]; px, py = (d["ref"][0] + mx, d["ref"][1] + my) if mx is not None else (d["x"], d["y"])
        if v and (mx is None or (abs(v[0] - px) <= SHIFT_TOL and abs(v[1] - py) <= SHIFT_TOL)):
            x, y, sc = v; dx, dy = x - d["x"], y - d["y"]
            LOC[key] = (x, y, round(sc, 1)); d["x"], d["y"] = x, y; ok += 1
            log("المباني: %s عند (%d,%d) تحرّك (%+d,%+d) نتيجة=%.1f" % (_n(key), x, y, dx, dy, sc))
        else:
            if v: bad += 1; log("المباني: %s وُجد بعيداً عن الإزاحة المشتركة (%d,%d)؛ صُحّح" % (_n(key), v[0], v[1]))
            LOC[key] = (px, py, 99.0); d["x"], d["y"] = px, py
    T[0] = time.time(); _save()
    try: _status(log, f)
    except Exception as e: log("المباني: تعذّر قراءة الحالة: %s" % e)
    log("المباني: حُدّد %d من %d في %.1f ث" % (ok, ok + bad, time.time() - t0))
    return ok, bad


NAMES = {}                                         # يضبطها panel.py: مفتاح المهمة -> اسمها
STATE = {}                                         # المبنى -> "alert" (فقاعة ! أو أيقونة جاهزة) | "idle" (zZ خامل) | "none"
def _n(key): return NAMES.get(key, key)
ALERT = lambda r, g, b: (r > 215 and 70 < g < 130 and 45 < b < 105) or (r > 200 and g < 100 and 40 < b < 140)
PALE = lambda r, g, b: 170 < r < 240 and 170 < g < 240 and 165 < b < 240 and max(r, g, b) - min(r, g, b) < 34      # جسم فقاعة zZ الشفاف الباهت
GLYPH = lambda r, g, b: r > 225 and 140 < g < 215 and b < 140                                                    # حرف zZ البرتقالي
def status(f, x, y):
    """الفقاعة تقع فوق نقطة الضغط بنحو 20-50 بكسلاً وإلى يمينها 0-18."""
    box = (x - 14, y - 85, x + 40, y - 12)
    if f.count(box, ALERT, 2) >= 25: return "alert"
    if f.count(box, PALE, 2) >= 70 and f.count(box, GLYPH, 2) >= 6: return "idle"
    return "none"
def _status(log, f):
    names = {"alert": [], "idle": [], "none": []}
    for key, (x, y, _) in LOC.items():
        STATE[key] = status(f, x, y); names[STATE[key]].append(_n(key))
    log("المباني: تحتاج إجراء ● %s | خاملة zZ ● %s | بلا فقاعة ● %s" % ("، ".join(names["alert"]) or "-", "، ".join(names["idle"]) or "-", "، ".join(names["none"]) or "-"))

def apply(key, mod):
    """يضع موقع المبنى المحدَّث (والزر السداسي بنفس الإزاحة الأصلية) في ثوابت وحدة المهمة."""
    if key not in MAP or key not in LOC: return
    b, hx = MAP[key]
    if key not in ORIG:
        try: ORIG[key] = (tuple(getattr(mod, b)), tuple(getattr(mod, hx)))
        except Exception: return
    ob, oh = ORIG[key]; x, y, _ = LOC[key]
    setattr(mod, b, (x, y))
    setattr(mod, hx, (x + oh[0] - ob[0], y + oh[1] - ob[1]))
