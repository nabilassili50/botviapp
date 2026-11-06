"""فتح مبنى من المدينة بإعادة اكتشافه بصرياً في كل مرة (v4.3.10).
المشكلة: كل مهمة كانت تضغط المبنى ثم إحداثية ثابتة للزر السداسي (إزاحة محفوظة)، فإذا اختلف موضع المبنى أو الزر ولو قليلاً فشلت المهمة.
الحل: بعد ضغط المبنى (بموضعه المحدَّث من layout) تُكتشف صف الأزرار السداسية الفعلي على الشاشة بلونها، ويُضغط الأول من اليسار (زر التنفيذ) ولا يُضغط زر المعلومات i أقصى اليمين أبداً،
فإن لم تفتح الشاشة المطلوبة (verify) أُغلقت وجُرّب الزر التالي من اليسار، ثم نقاط ضغط بديلة حول المبنى. لا تتغير باقي منطق المهام."""
import time
from shizuku import frame, tapx, nap
from tasks.saga import has_x, CLOSE_X, TEAL, _blobs
from tasks.guard import popup_x

JIT = [(0, 0), (30, -18), (45, -28), (-25, 10), (15, -5)]      # نقاط ضغط بديلة حول المبنى


def hex_row(f, bx, by):
    """صف الأزرار السداسية الظاهر تحت المبنى المضغوط: مراكز [(x, y)] مرتبة من اليسار (اثنان فأكثر). فارغة إن لم يوجد."""
    C = 6; cells = {}
    x0, x1, y0, y1 = max(40, bx - 280), min(1240, bx + 280), max(120, by - 10), min(720, by + 320)
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            if TEAL(*f.px(x, y)):
                k = (x // C, y // C); cells[k] = cells.get(k, 0) + 1
    hx = sorted([((b[0] + b[2]) // 2, (b[1] + b[3]) // 2) for b in _blobs(cells, C, (36, 84), (36, 84), 100)])
    best = []
    for i in range(len(hx)):
        ch = [hx[i]]
        for p in hx[i + 1:]:
            if 45 <= p[0] - ch[-1][0] <= 90 and abs(p[1] - ch[-1][1]) <= 24: ch.append(p)
        if len(ch) > len(best) and abs(sum(p[0] for p in ch) / float(len(ch)) - bx) <= 190: best = ch      # الصف يتوسط المبنى تقريباً
    return best if len(best) >= 2 else []


def dismiss(f, s, n=3):
    """يغلق نوافذ المعلومات/التنبيه (معين أحمر بعلامة X) وشاشات الزاوية العليا اليسرى إن وُجدت؛ يرجع آخر لقطة. لا يضغط أزرار النافذة (تأكيد/انتقال)."""
    for _ in range(n):
        p = popup_x(f)
        if p: tapx(p[0], p[1], s)
        elif has_x(f): tapx(*CLOSE_X, s)
        else: break
        nap(1.2); f = frame()
    return f


def open_building(log, name, build, hexp, verify, wait=3.5, tries=3):
    """يضغط المبنى ثم الزر السداسي المناسب حتى تتحقق verify(frame). يرجع آخر لقطة (تفحصها المهمة كالمعتاد).
    v4.3.10: بدل انتظار ثابت (1.2 ثم 2.5-3 ث) يفحص الشاشة كل نصف ثانية ويتابع فور ظهور الأزرار / فتح الشاشة (الحد الأقصى كما كان أو أكثر)."""
    f = frame(); s = f.s; seen_row = False
    for ox, oy in JIT:
        bx, by = int(build[0]) + ox, int(build[1]) + oy
        for k in range(tries):
            tapx(bx, by, s); t0 = time.time(); row = []
            while True:                                                               # انتظر ظهور صف الأزرار (أو فتح الشاشة مباشرة)
                nap(0.5); f = frame()
                if verify(f): return f
                row = hex_row(f, bx, by)
                if row or time.time() - t0 > 1.8: break
            if row:
                seen_row = True
                order = row[:-1] if len(row) >= 3 else row[:1]          # زر المعلومات (i) أقصى اليمين: لا يُضغط أبداً؛ والباقي من اليسار (زر التنفيذ أولاً)
                if k >= len(order): break
                tx, ty = order[k]
            elif ox == 0 and oy == 0 and k == 0: tx, ty = int(hexp[0]), int(hexp[1])         # لم يُكتشف صف: الموضع المتوقع كاحتياط
            else: break
            tapx(tx, ty, s); t0 = time.time()
            while True:                                                               # انتظر فتح الشاشة المطلوبة
                nap(0.5); f = frame()
                if verify(f): return f
                if time.time() - t0 > wait or (time.time() - t0 > 0.9 and popup_x(f)): break       # ظهرت نافذة تنبيه/معلومات = الزر خاطئ: لا داعي للانتظار
            if k == 0 or row: log("%s: الزر عند (%d,%d) لم يفتح الشاشة المطلوبة؛ أجرّب غيره" % (name, tx, ty))
            f = dismiss(f, s)                                                         # أغلق ما فُتح بالخطأ (معلومات/ترقية/نافذة تنبيه) قبل المحاولة التالية
        if seen_row: break                                                                # الصف ظهر وجُرّبت أزراره: لا فائدة من نقاط بديلة
    return f
