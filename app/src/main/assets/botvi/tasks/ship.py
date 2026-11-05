"""سفينة الشحن (آخر مهمة في القلعة قبل جمع الموارد).
v4.3: تحديد مكان السفينة بالرؤية بدل إحداثيات ثابتة بعد سحب ثابت:
  - السفينة تظهر بفقاعة تنبيه \"!\" برتقالية حمراء فوقها وتحتها ماء المرفأ الأزرق. المباني الأخرى لها الفقاعة نفسها لكن فوق عشب/أرض،
    فالماء تحت الفقاعة هو الفاصل (في لقطة الاختبار: 1205 بكسل ماء للسفينة مقابل 274 كحد أقصى لأي مبنى آخر؛ العتبة 600).
  - يفحص المشهد الحالي أولاً، ثم يسحب الشاشة خطوة خطوة (ship_steps) باتجاه ثم الاتجاه المعاكس، ويفحص بعد كل سحبة ويتوقف عند أول عثور.
  - يضغط على جسم السفينة (تحت الفقاعة)، ويتحقق من فتح شاشة الشحن، ثم يعيد القلعة إلى وضعها الأول بحسب صافي السحبات الفعلي.
  - لا فقاعة = لا تبادل متاح أو لم تصل بعد: تخطٍّ بهدوء (وتُحفظ debug_ship_search.png).
  - ship_xy في settings.json ما زال يعمل كاحتياط يدوي إن فشل الكشف.
تبادل: يضغط كل أزرار \"تبادل\" المتاحة (موارد مقابل موارد/تسريعات، لا جواهر). نافذة \"استخدام تلقائي\" يضغط فيها \"إلغاء\" دائماً."""
import os, time
from shizuku import frame, tapx, screencap, swipe, nap
from tasks.saga import has_x, CLOSE_X
from tasks.guard import city

RIBBON = lambda r, g, b: r > 150 and g < 90 and b < 90
WOOD = lambda r, g, b: 90 < r < 170 and 55 < g < 120 and 25 < b < 85 and r > g + 25
BTN = lambda r, g, b: 40 <= r <= 70 and 100 <= g <= 135 and 120 <= b <= 160
GOLD = lambda r, g, b: 150 < r < 255 and 90 < g < 190 and b < 90 and r > g + 40
BLUE = lambda r, g, b: r < 110 and 120 < g < 190 and b > 150
PARCH = lambda r, g, b: 190 < r < 245 and 160 < g < 215 and 100 < b < 170
BUBBLE = lambda r, g, b: r > 215 and 70 < g < 130 and 45 < b < 105             # وجه فقاعة التنبيه البرتقالية الحمراء
WATER = lambda r, g, b: r < 85 and 90 < g < 175 and b > 150 and b > r + 90      # ماء المرفأ الأزرق الساطع

DRAG, STEPS = 340, 3                                 # طول كل سحبة (بكسل بمقياس 1280) وعددها في كل اتجاه (ship_drag / ship_steps)
Y0 = 560                                             # خط السحب (عشب فارغ)
WATER_MIN = 600                                      # أقل عدد عيّنات ماء تحت الفقاعة (ship_water)
TAPS = [(0, 45), (0, 28), (-14, 62)]                 # مواضع الضغط على جسم السفينة بالنسبة لمركز الفقاعة
SEARCH_REGION = (120, 70, 1215, 700)                 # يتجاهل شريط الدردشة العلوي والشريط السفلي والأزرار الجانبية
CANDS = [(760, 390), (560, 390), (420, 390)]         # احتياط قديم: يُستعمل فقط إن ضُبط ship_xy يدوياً
SLOTS = [((812, 445, 970, 512), (890, 480)), ((240, 445, 466, 512), (355, 480)), ((240, 650, 466, 712), (355, 680)), ((812, 650, 970, 712), (890, 680))]
CANCEL_XY = (777, 695)                               # \"إلغاء\" في نافذة الاستخدام التلقائي — لا نضغط \"استخدام\" أبداً

def city_view(f): return city(f) and f.count((1135, 715, 1255, 785), PARCH) > 150      # المدينة لا الخريطة
def cargo(f): return has_x(f) and f.count((500, 120, 780, 165), RIBBON) > 1500 and f.count((90, 150, 300, 250), WOOD) > 1500
def auto_popup(f): return f.count((500, 120, 780, 165), RIBBON) < 200 and f.count((380, 655, 610, 735), GOLD) > 3000 and f.count((665, 655, 890, 735), BLUE) > 300
def sig(f): return [f.px(x, y) for x in range(300, 1000, 50) for y in range(250, 650, 50)]
def same(a, b): return sum(1 for p, q in zip(a, b) if sum(abs(i - j) for i, j in zip(p, q)) > 90) < len(a) * 0.25

def snap(name):
    try: open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug_%s.png" % name), "wb").write(screencap())
    except Exception: pass

def pan(s, d, n):
    for _ in range(n):
        swipe(int((640 - d / 2) * s), int(Y0 * s), int((640 + d / 2) * s), int(Y0 * s), 600); nap(1.3)

def find_ship(f, water_min=WATER_MIN, region=SEARCH_REGION):
    """يرجع [(x, y, ماء)] لنقاط فقاعات التنبيه التي تحتها ماء كثير (السفن)، الأكثر ماءً أولاً. فارغة إن لم توجد."""
    C = 6; cells = {}; x0, y0, x1, y1 = region
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            if BUBBLE(*f.px(x, y)):
                k = (x // C, y // C); cells[k] = cells.get(k, 0) + 1
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
        bx0, bx1, by0, by1 = min(xs), max(xs) + C, min(ys), max(ys) + C
        w, h = bx1 - bx0, by1 - by0; cnt = sum(cells[p] for p in pts)
        if not (18 <= w <= 56 and 18 <= h <= 56 and cnt >= 30): continue          # حجم فقاعة لا بقعة لونية
        cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
        water = f.count((cx - 90, cy + 20, cx + 90, cy + 120), WATER, 3)
        if water >= water_min: out.append((cx, cy, water))
    return sorted(out, key=lambda t: -t[2])

def close_all(n=3):
    for _ in range(n):
        f = frame()
        if not has_x(f): return
        tapx(*CLOSE_X, f.s); nap(1.2)

def exchange(log, s):
    n = 0
    for box, xy in SLOTS:
        f = frame()
        if auto_popup(f): tapx(*CANCEL_XY, s); nap(1.2); f = frame()
        if not cargo(f): break
        if f.count(box, BTN) < 800: continue                     # تم التبادل أو مقفل
        tapx(*xy, s); nap(2.5); f = frame()
        if auto_popup(f): tapx(*CANCEL_XY, s); log("السفينة: نقص مورد؛ أُلغي الاستخدام التلقائي"); nap(1.2); continue
        n += 1
    return n

def locate(log, s, d, k, net, wmin):
    """يبحث عن السفينة في المشهد الحالي ثم بالسحب: k خطوات باتجاه، عودة للوضع الأول، k خطوات بالاتجاه المعاكس.
    net[0] = صافي السحبات (موجب = نحو اليمين) ليعيد run() القلعة لوسطها مهما حدث. يرجع (x, y) لمركز الفقاعة أو None."""
    def look():
        f = frame()
        if f.w < f.h: return None
        r = find_ship(f, wmin)
        if r: log("السفينة: وُجدت عند (%d,%d) (ماء=%d، إزاحة=%+d)" % (r[0][0], r[0][1], r[0][2], net[0])); return r[0][:2]
    p = look()
    if p: return p
    plan = [(1, True)] * k + [(-1, False)] * k + [(-1, True)] * k      # (اتجاه السحبة، هل نفحص بعدها؟)
    for sign, check in plan:
        pan(s, sign * d, 1); net[0] += sign
        if check:
            p = look()
            if p: return p
    return None

def run(log, cfg):
    f = frame()
    if f.w < f.h: return log("الشاشة عمودية؛ يلزم الوضع الأفقي")
    if not city_view(f): return log("السفينة: لسنا في المدينة؛ تخطّي")
    s = f.s; base = sig(f); d = int(cfg.get("ship_drag") or DRAG); k = int(cfg.get("ship_steps") or STEPS)
    wmin = int(cfg.get("ship_water") or WATER_MIN); net = [0]
    try:
        opened = False
        p = locate(log, s, d, k, net, wmin)
        if p:
            for ox, oy in TAPS:
                tapx(p[0] + ox, p[1] + oy, s); nap(2.2); f = frame()
                if cargo(f): opened = True; break
                if has_x(f): tapx(*CLOSE_X, f.s); nap(1.2)       # شاشة فُتحت بالخطأ
        elif cfg.get("ship_xy"):                                  # احتياط يدوي صريح فقط
            pan(s, d, k); net[0] += k
            for xy in [tuple(c) for c in cfg.get("ship_xy")]:
                tapx(*xy, s); nap(2.2); f = frame()
                if cargo(f): opened = True; break
                if has_x(f): tapx(*CLOSE_X, f.s); nap(1.2)
        if not opened:
            snap("ship_search")
            return log("السفينة: لم تُفتح شاشة الشحن (حُفظت debug_ship_search.png)" if p else "السفينة: لا فقاعة تنبيه على الماء (لا تبادل متاح أو لم تصل بعد)؛ تخطّي")
        n = exchange(log, s)
        log("السفينة: %d عملية تبادل" % n if n else "السفينة: لا تبادل متاح الآن")
        close_all()
    finally:
        if net[0] > 0: pan(s, -d, net[0])
        elif net[0] < 0: pan(s, d, -net[0])
        net[0] = 0; f = frame()
        if not same(base, sig(f)): snap("ship_home"); log("السفينة: قد لا نكون عدنا لوسط القلعة تماماً (حُفظت debug_ship_home.png)")
