"""تكرير المانا (منجم المانا) — v4.3.4.
المسار (من لقطاتك): المدينة ← ضغط المنجم ← الزر السداسي الأول (مكعب المانا) ← شاشة المنجم ← صندوق "تكرير المانا" ← شاشة التكرير ← زر "تكرير" (5 مرات يومياً).
  - نافذة "استخدام تلقائي" (تلبية متطلبات المشروع): يضغط "استخدام" (mana_autouse=false ليضغط "إلغاء" بدلاً منه).
  - نافذة "ملاحظة: ليس لديك موارد كافية": يضغط "تأكيد" ويحسبها فشلاً (يتوقف بعد فشلين).
  - عبارة "تم الوصول إلى حد التكرير اليومي" الحمراء: يتوقف ويرجع "limit" (تنتظر الجدولة 10 ساعات).
  - الأزرار السداسية تُكتشف بلونها، ويجرّب عدة نقاط ضغط حول المنجم إن لم تظهر (لا يعتمد على إحداثية واحدة دقيقة).
  - mana_count في settings.json يغيّر عدد التكريرات (الافتراضي 5)."""
import time
from shizuku import frame, tapx, nap
from tasks.saga import has_x, CLOSE_X, TEAL, _blobs
from tasks.guard import city

RIBBON = lambda r, g, b: r > 150 and g < 90 and b < 90
GOLD = lambda r, g, b: 150 < r < 255 and 90 < g < 190 and b < 90 and r > g + 40
BLUE = lambda r, g, b: r < 110 and 120 < g < 190 and b > 150
REDTXT = lambda r, g, b: r > 200 and g < 125 and b < 125 and r > g + 90        # عبارة حد التكرير اليومي الحمراء
XOR = lambda r, g, b: r > 230 and 140 < g < 220 and b < 110                     # علامة X البرتقالية

MINE_XY, HEX_XY = (685, 310), (607, 393)         # المنجم وأول زر سداسي (مكعب المانا) — يُحدَّثان بمعايرة /layout
MINE_TAPS = [(0, 0), (30, -18), (45, -28), (-20, 10), (15, -5)]   # نقاط ضغط احتياطية حول المنجم
REFINE_BOX = (412, 400)                          # صندوق "تكرير المانا" في شاشة المنجم
REFINE_BTN = (436, 700)                          # زر "تكرير"
USE_XY, CANCEL_XY = (493, 722), (778, 722)       # "استخدام" و"إلغاء" في نافذة الاستخدام التلقائي
CONFIRM_XY = (638, 383)                          # "تأكيد" في نافذة نقص الموارد
GOLD_UPG, GOLD_REF = (95, 628, 272, 738), (320, 662, 555, 735)
LIMIT_BOX = (320, 626, 555, 654)


def find_hexes(f):
    """الأزرار السداسية الثلاثة (مكعب المانا، سهم الترقية، i) مرتبة من اليسار. أضيق من كاشف الملحمة لأن سهم الترقية يشطر زرّه الأوسط (عرض ≈42)."""
    C = 6; cells = {}
    for y in range(120, 720, 2):
        for x in range(40, 1240, 2):
            if TEAL(*f.px(x, y)):
                k = (x // C, y // C); cells[k] = cells.get(k, 0) + 1
    hx = sorted([((b[0] + b[2]) // 2, (b[1] + b[3]) // 2) for b in _blobs(cells, C, (36, 84), (36, 84), 100)])
    best = []
    for i in range(len(hx)):
        ch = [hx[i]]
        for p in hx[i + 1:]:
            if 45 <= p[0] - ch[-1][0] <= 90 and abs(p[1] - ch[-1][1]) <= 24: ch.append(p)
        if len(ch) > len(best): best = ch
    return best[:3] if len(best) >= 3 else []


def _ribbon(f): return f.count((500, 120, 780, 165), RIBBON) > 1500
def mine_screen(f): return has_x(f) and _ribbon(f) and f.count(GOLD_UPG, GOLD) > 3000
def refine_screen(f): return has_x(f) and _ribbon(f) and f.count(GOLD_REF, GOLD) > 3000
def auto_popup(f): return f.count((500, 120, 780, 165), RIBBON) < 200 and f.count((380, 655, 610, 735), GOLD) > 3000 and f.count((665, 655, 890, 735), BLUE) > 300
def note_popup(f): return f.count((380, 125, 408, 150), XOR) > 40 and not auto_popup(f)
def limit_reached(f): return f.count(LIMIT_BOX, REDTXT, 2) >= 25


def close_all(n=3):
    for _ in range(n):
        f = frame()
        if not has_x(f): return
        tapx(*CLOSE_X, f.s); nap(1.2)


def open_refine(log, f):
    s = f.s
    for _ in range(3):                                           # نحن داخل شاشة من المنجم أصلاً؟
        if refine_screen(f): return f
        if mine_screen(f):
            tapx(*REFINE_BOX, s); nap(1.5); f = frame()
            if refine_screen(f): return f
        elif has_x(f): tapx(*CLOSE_X, s); nap(1.2); f = frame()
        else: break
    if not city(f): return None
    mx, my = MINE_XY
    for ox, oy in MINE_TAPS:
        hx = find_hexes(f)
        if len(hx) < 3:
            tapx(mx + ox, my + oy, s); nap(1.3); f = frame(); hx = find_hexes(f)
        if len(hx) == 3: tapx(*hx[0], s)                          # الزر الأول (مكعب المانا)
        elif ox == 0 and oy == 0: tapx(*HEX_XY, s)               # احتياط: الإحداثية المحدَّثة
        else: continue
        nap(1.8); f = frame()
        if mine_screen(f):
            tapx(*REFINE_BOX, s); nap(1.5); f = frame()
            if refine_screen(f): return f
        if has_x(f): tapx(*CLOSE_X, s); nap(1.2); f = frame()    # فُتح مبنى آخر بالخطأ: أغلقه وجرّب نقطة أخرى
    return None


def popups(log, cfg, s):
    """يعالج النوافذ بعد ضغط "تكرير": يرجع "short" إن ظهر نقص موارد، وإلا "ok"."""
    res = "ok"
    for _ in range(5):
        f = frame()
        if auto_popup(f):
            if cfg.get("mana_autouse", True): tapx(*USE_XY, s); log("المانا: استخدام موارد تلقائياً")
            else: tapx(*CANCEL_XY, s); log("المانا: نقص مورد؛ أُلغي الاستخدام التلقائي"); res = "short"
            nap(1.8); continue
        if note_popup(f):
            tapx(*CONFIRM_XY, s); log("المانا: ليس لديك موارد كافية؛ أُغلقت الملاحظة"); res = "short"; nap(1.3); continue
        if refine_screen(f) or mine_screen(f): break
        nap(1)                                                  # حركة/تحميل: انتظر ثم أعد الفحص
    return res


def run(log, cfg):
    f = frame()
    if f.w < f.h: return log("الشاشة عمودية؛ يلزم الوضع الأفقي")
    f = open_refine(log, f)
    if f is None: return log("المانا: لم تُفتح شاشة التكرير (تأكد من موضع المدينة؛ لم تظهر أزرار المنجم)")
    s = f.s; target = int(cfg.get("mana_count") or 5); done = fails = 0; lim = limit_reached(f)
    while not lim and done < target and fails < 2:
        tapx(*REFINE_BTN, s); nap(1.6)
        if popups(log, cfg, s) == "short": fails += 1
        else: done += 1; log("المانا: تكرير %d من %d" % (done, target))
        f = frame()
        if not refine_screen(f): break
        lim = limit_reached(f)
    log("المانا: تم %d تكرير%s" % (done, " — بلغنا حد التكرير اليومي" if lim else ""))
    close_all()
    return "limit" if lim or done >= target else None
