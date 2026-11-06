"""هدايا التحالف — v4.3.6.
المسار (من لقطاتك): المدينة ← زر التحالف في الشريط السفلي ← زر "مستوى الهدية" ← شاشة هدايا التحالف:
  تبويب "هدية التحالف": زر الصندوق ذي السهم (فتح الكل) ثم زر السلة (حذف المفتوح)،
  ثم تبويب "صندوق المكافآت": الشيء نفسه (فارغ = لا يفعل شيئاً).
  - لا يضغط السلة إلا إذا ظهر زر "مسح" الأحمر في أول صف (أي فُتحت الهدايا).
  - gifts_delete=false في settings.json يعطّل الحذف (الافتراضي: يحذف).
  - إن ظهرت نافذة بعد السلة يحفظ debug_gifts_trash.png ويضغط الزر الذهبي فيها؛ أرسل لي اللقطة إن ظهرت."""
import os
from shizuku import frame, tapx, nap, screencap
from tasks.saga import has_x, CLOSE_X, _blobs
from tasks.guard import city

RED = lambda r, g, b: r > 150 and g < 110 and b < 110 and r > g + 60           # زر "مسح" والسلة
OPEN = lambda r, g, b: r <= 58 and 112 <= g <= 130 and 125 <= b <= 160         # زر "فتح" وزر الصندوق (ليس خلفية الشاشة الفارغة)
BRIGHT = lambda r, g, b: r < 130 and g > 140 and b > 190                       # التبويب النشط
BROWN = lambda r, g, b: 120 < r < 200 and 65 < g < 130 and 25 < b < 85 and r > g + 30
GOLD = lambda r, g, b: 150 < r < 255 and 90 < g < 190 and b < 90 and r > g + 40

ALLIANCE_BTN, GIFT_LEVEL_BTN = (680, 752), (343, 305)
OPEN_ALL, TRASH = (213, 172), (340, 172)
TAB_GIFT, TAB_REWARD = (630, 270), (308, 270)
ROWS = [(150, 310, 295, 367), (150, 433, 295, 490), (150, 557, 295, 614), (150, 681, 295, 738)]


def gifts_screen(f): return has_x(f) and f.count((158, 140, 270, 205), OPEN) > 800 and f.count((285, 140, 395, 205), RED) > 1200
def alliance_screen(f): return has_x(f) and f.count((245, 275, 445, 342), BROWN) > 1200 and f.count((158, 140, 270, 205), OPEN) < 400
def tab_gift(f): return f.count((480, 248, 780, 290), BRIGHT) > 3000
def tab_reward(f): return f.count((160, 248, 455, 290), BRIGHT) > 3000
def n_open(f): return sum(1 for b in ROWS if f.count(b, OPEN) > 1500)
def any_red(f): return f.count(ROWS[0], RED) > 1500


def snap(name):
    try: open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug_%s.png" % name), "wb").write(screencap())
    except Exception: pass


def close_all(n=4):
    for _ in range(n):
        f = frame()
        if not has_x(f): return
        tapx(*CLOSE_X, f.s); nap(1.2)


def open_gifts(f):
    s = f.s
    for _ in range(5):
        if gifts_screen(f): return f
        if alliance_screen(f): tapx(*GIFT_LEVEL_BTN, s); nap(1.8); f = frame(); continue
        if has_x(f): tapx(*CLOSE_X, s); nap(1.2); f = frame(); continue          # شاشة أخرى: أغلقها
        if not city(f): return None
        tapx(*ALLIANCE_BTN, s); nap(1.8); f = frame()
    return f if gifts_screen(f) else None


def confirm_popup(log, s):
    """نافذة ظهرت بعد السلة (لم أرها): احفظ لقطتها واضغط الزر الذهبي الأيسر فيها."""
    snap("gifts_trash")
    f = frame(); C = 6; cells = {}
    for y in range(300, 790, 2):
        for x in range(200, 1100, 2):
            if GOLD(*f.px(x, y)): k = (x // C, y // C); cells[k] = cells.get(k, 0) + 1
    bl = sorted(_blobs(cells, C, (100, 320), (40, 100), 800))
    if bl:
        b = bl[0]; tapx((b[0] + b[2]) // 2, (b[1] + b[3]) // 2, s); log("الهدايا: ظهرت نافذة بعد الحذف؛ ضُغط الزر الذهبي (حُفظت debug_gifts_trash.png)"); nap(1.5)
    else: log("الهدايا: ظهرت نافذة غير معروفة بعد الحذف (حُفظت debug_gifts_trash.png)")


def work(log, cfg, s, name):
    opened = deleted = 0
    for _ in range(3):
        f = frame()
        if not gifts_screen(f): break
        k = n_open(f)
        if not k: break
        tapx(*OPEN_ALL, s); nap(2.5); opened += k
    f = frame()
    if cfg.get("gifts_delete", True) and gifts_screen(f) and any_red(f):
        tapx(*TRASH, s); nap(1.6); f = frame()
        if not gifts_screen(f): confirm_popup(log, s); f = frame()
        if gifts_screen(f) and not any_red(f): deleted = 1
        else: log("الهدايا: لم تُحذف القائمة بعد السلة")
    log("الهدايا: %s — فُتح %s%s" % (name, "%d+ هدية" % opened if opened else "لا شيء", "، وحُذفت المفتوحة" if deleted else ""))


def run(log, cfg):
    f = frame()
    if f.w < f.h: return log("الشاشة عمودية؛ يلزم الوضع الأفقي")
    f = open_gifts(f)
    if f is None: return log("الهدايا: لم تُفتح شاشة هدايا التحالف (حُفظت debug_gifts_open.png)") or snap("gifts_open")
    s = f.s
    if not tab_gift(f): tapx(*TAB_GIFT, s); nap(1.5)
    work(log, cfg, s, "هدية التحالف")
    f = frame()
    if gifts_screen(f):
        tapx(*TAB_REWARD, s); nap(1.5)
        work(log, cfg, s, "صندوق المكافآت")
    close_all()
