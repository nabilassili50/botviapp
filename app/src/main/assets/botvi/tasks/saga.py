"""الملحمة البطولية: فتحها من أزرار التمثال، استلام المكافآت، ثم تعيين الأبطال تلقائياً لكل موقع حر.
v4.3.1 (إصلاح \"لا تفتح/لا تعيّن صح\"، بعد فحص 16 لقطة من حساب المستوى 5):
  - المواقع لم تعد 4 إحداثيات ثابتة (2x2): في المستوى 5 هي 5 مواقع (3 فوق + 2 تحت). تُكتشف الآن من شرائط الأسماء الملوّنة
    (رمادي/بنفسجي/أخضر، والبرتقالي = جاهز للاستلام)، فتعمل بأي عدد وأي ترتيب.
  - الموقع الحر = فوقه مؤقّت أخضر ساطع (ساعة رملية). الموقع المقفل (قفل رمادي) أو بعد بلوغ الحد اليومي بلا مؤقّت فيُتخطّى.
  - فحص \"محدَّد\" كان يقرأ علامة ✓ لأول بطل فقط فيفشل (لقطة 5/5 ظهر فيها selected=False) فيضغط \"تحديد تلقائي\" فيُلغي التحديد!
    الآن يعدّ علامات ✓ الصفراء على كل شبكة الأبطال (217-258 عند التحديد مقابل 7-53 بدونه؛ العتبة 190).
  - بعد \"تعيين\" يتحقق من إغلاق اللوحة (نجاح) وإلا يغلقها ويكمل بدل أن يترك لوحة مفتوحة تبتلع الضغطات التالية.
  - الدخول: أزرار التمثال السداسية تُكتشف بلونها (كانت تُضغط عند y=410 بينما هي عند y≈342-355)، وإن لم تظهر يضغط التمثال أولاً
    (STATUE_XY، يمكن معايرته من /layout فيُحدَّث عند كل دخول مع HEX_XY).
  - saga_entry في settings.json ما زال يتجاوز كل ذلك يدوياً."""
import time
from shizuku import frame, tapx, nap, back

ORANGE = lambda r, g, b: r > 220 and 130 < g < 200 and b < 90
YELLOW = lambda r, g, b: r > 230 and g > 190 and b < 80
CHECK = lambda r, g, b: r > 235 and g > 200 and b < 90                     # علامة ✓ على بطاقة البطل
TEAL = lambda r, g, b: r < 80 and 100 < g < 155 and 135 < b < 190 and b > g + 18      # جسم الزر السداسي (الماء b-g>45 فلا يختلط)
LIME = lambda r, g, b: r < 120 and g > 200 and b < 120 and g > r + 90      # أرقام المؤقّت الأخضر فوق الموقع الحر

STATUE_XY, HEX_XY = (480, 250), (407, 342)          # تمثال البطل في المدينة، وأول زر سداسي (compass) — يُحدَّثان بمعايرة /layout
HEX_OFFS = [(0, 0), (60, 13), (120, 13)]            # الأزرار الثلاثة بالنسبة لأولها (احتياط إن فشل الكشف اللوني)
ASSIGN_BOX, ASSIGN_XY, AUTO_XY = (80, 665, 320, 735), (200, 700), (200, 620)
GRID = (30, 170, 385, 580)                          # شبكة بطاقات الأبطال في اللوحة اليسرى
SEL_MIN = 190                                       # أقل عدد بكسلات ✓ لاعتبار الأبطال الخمسة محدَّدين
SITE_REGION = (100, 330, 1180, 690)                 # منطقة شرائط أسماء المواقع
TAP_DY = -35                                        # الضغط فوق الشريط قليلاً (على قاعدة الجزيرة)
CLOSE_X = (45, 45)

def has_x(f):
    r, g, b = f.px(*CLOSE_X); return r > 230 and 150 < g < 220 and b < 100
def in_saga(f):
    r, g, b = f.px(880, 133)      # شريط "الملحمة البطولية" الأزرق
    return has_x(f) and r < 50 and b > 110 and b > g + 40
def panel_open(f): return f.count(ASSIGN_BOX, ORANGE) > 1500
def selected(f): return f.count(GRID, CHECK) >= SEL_MIN

_ok = []

def _blobs(cells, C, wr, hr, minc):
    """يجمع الخلايا المتجاورة إلى كتل ويرجع [(x0, y0, x1, y1, عدد)] لما يطابق حجم العنصر المطلوب."""
    cells = {k: v for k, v in cells.items() if v >= 2}
    seen = set(); out = []
    for k in list(cells):
        if k in seen: continue
        st = [k]; seen.add(k); pts = []
        while st:
            a = st.pop(); pts.append(a)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    n = (a[0] + dx, a[1] + dy)
                    if n in cells and n not in seen: seen.add(n); st.append(n)
        xs = [p[0] * C for p in pts]; ys = [p[1] * C for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs) + C, min(ys), max(ys) + C
        w, h = x1 - x0, y1 - y0; cnt = sum(cells[p] for p in pts)
        if wr[0] <= w <= wr[1] and hr[0] <= h <= hr[1] and cnt >= minc: out.append((x0, y0, x1, y1, cnt))
    return out

def find_hexes(f):
    """الأزرار السداسية تحت تمثال البطل (compass، خوذة، خوذة ثانية، ثم i): مراكز [(x, y)] مرتبة من اليسار، أول ثلاثة فقط."""
    C = 6; cells = {}
    for y in range(120, 720, 2):
        for x in range(40, 1240, 2):
            if TEAL(*f.px(x, y)):
                k = (x // C, y // C); cells[k] = cells.get(k, 0) + 1
    hx = sorted([((b[0] + b[2]) // 2, (b[1] + b[3]) // 2) for b in _blobs(cells, C, (44, 80), (40, 80), 120)])
    best = []                                          # أطول سلسلة أزرار متجاورة بخطوة أفقية 45-80 وفرق ارتفاع ≤ 24
    for i in range(len(hx)):
        ch = [hx[i]]
        for p in hx[i + 1:]:
            if 45 <= p[0] - ch[-1][0] <= 80 and abs(p[1] - ch[-1][1]) <= 24: ch.append(p)
        if len(ch) > len(best): best = ch
    return best[:3] if len(best) >= 3 else []

def find_sites(f):
    """مواقع الملحمة من شرائط الأسماء: [{x, y, claim, free}] بترتيب الصفوف ثم من اليسار."""
    C = 6; cells = {1: {}, 2: {}, 3: {}, 4: {}}; x0, y0, x1, y1 = SITE_REGION
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            r, g, b = f.px(x, y); k = 0
            if abs(r - g) < 12 and abs(g - b) < 12 and 175 < r < 235: k = 1               # رمادي
            elif 120 < r < 170 and 85 < g < 130 and 200 < b < 250: k = 2                   # بنفسجي
            elif r < 85 and 155 < g < 205 and 80 < b < 125 and g > r + 90: k = 3           # أخضر
            elif r > 220 and 130 < g < 200 and b < 90: k = 4                               # برتقالي = جاهز للاستلام
            if k: c = (x // C, y // C); cells[k][c] = cells[k].get(c, 0) + 1
    out = []
    for k in (1, 2, 3, 4):
        for b in _blobs(cells[k], C, (110, 300), (22, 70), 250):
            cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
            free = f.count((cx - 75, cy - 112, cx + 45, cy - 70), LIME, 2) > 25
            out.append({"x": cx, "y": cy, "claim": k == 4, "free": free})
    out.sort(key=lambda s: (round(s["y"] / 80.0), s["x"]))
    return out

def _hex_candidates(cfg, f):
    if cfg.get("saga_entry"): return [tuple(c) for c in cfg["saga_entry"]]
    hx = find_hexes(f)
    if len(hx) == 3: return hx
    return [(HEX_XY[0] + dx, HEX_XY[1] + dy) for dx, dy in HEX_OFFS]

def open_saga(log, cfg, f):
    """يفتح شاشة الملحمة: يكشف الأزرار السداسية (يضغط التمثال أولاً إن لم تظهر) ويجرّبها حتى تُفتح. يرجع اللقطة الأخيرة أو None."""
    for attempt in range(2):
        if attempt == 1 or not find_hexes(f):
            tapx(*STATUE_XY, f.s); nap(1.4); f = frame()
            if in_saga(f): return f
        cands = _hex_candidates(cfg, f)
        order = ([_ok[0]] if _ok and _ok[0] < len(cands) else []) + [i for i in range(len(cands)) if not _ok or i != _ok[0]]
        for i in order:
            tapx(*cands[i], f.s); nap(2); f = frame()
            if in_saga(f): _ok[:] = [i]; log("الملحمة: الزر %d فتحها" % (i + 1)); return f
            if has_x(f): tapx(*CLOSE_X, f.s); nap(1.2); f = frame()          # أغلق ما فُتح بالخطأ
            if len(find_hexes(f)) < 3: break                                  # اختفت الأزرار: اضغط التمثال من جديد
    return None

def close_panel(f):
    """يغلق لوحة الموقع إن بقيت مفتوحة (رجوع واحد). يرجع اللقطة بعد الإغلاق."""
    if panel_open(f): back(); nap(1.2); f = frame()
    return f

def run(log, cfg):
    f = frame()
    if f.w < f.h: return log("الشاشة عمودية؛ يلزم الوضع الأفقي")
    if not in_saga(f):
        f = open_saga(log, cfg, f)
        if f is None: return log("الملحمة: لم يفتحها أي زر؛ ارجع إلى المدينة وأرسل لقطة")
    s = f.s
    # 1) استلام المكافآت (الشريط البرتقالي)
    for _ in range(8):
        f = frame(); todo = [t for t in find_sites(f) if t["claim"]]
        if not todo: break
        t = todo[0]; tapx(t["x"], t["y"], s); log("استلام موقع (%d,%d)" % (t["x"], t["y"])); nap(1.5)
        tapx(640, 760, s); nap(1); tapx(640, 760, s); nap(1)
    # 2) تعيين الأبطال لكل موقع حر (فوقه مؤقّت أخضر)
    f = frame(); sites = find_sites(f); free = [t for t in sites if t["free"] and not t["claim"]]
    log("الملحمة: %d موقع، منها %d حر" % (len(sites), len(free)))
    done = 0; fails = 0
    for i, t in enumerate(free):
        f = frame()
        if not in_saga(f): log("خرجنا من شاشة الملحمة"); break
        tapx(t["x"], t["y"] + TAP_DY, s); nap(1.2); f = frame()
        if not panel_open(f): log("الموقع %d مشغول/مغلق" % (i + 1)); continue
        if not selected(f): tapx(*AUTO_XY, s); nap(1); f = frame()          # لا نضغط إن كان محدَّداً (الضغطة الثانية \"إزالة التحديد\")
        if not selected(f):
            log("موقع %d: فشل التحديد التلقائي" % (i + 1)); close_panel(f); continue
        tapx(*ASSIGN_XY, s); nap(1.5); f = frame()
        if panel_open(f):
            log("موقع %d: لم يُغلق بعد التعيين (حد يومي أو نقص)" % (i + 1)); f = close_panel(f); fails += 1
            if not in_saga(f): break
            if fails >= 2: log("الملحمة: فشلان متتاليان؛ غالباً بلغنا الحد اليومي، أتوقف"); break
            continue
        done += 1; fails = 0; log("تعيين موقع %d" % (i + 1))
    log("الملحمة: عُيّن %d موقع" % done)
    f = frame()
    if in_saga(f): tapx(*CLOSE_X, s)
