package com.botvi.panel

import rikka.shizuku.Shizuku
import java.io.File
import java.lang.reflect.Method
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException

/** جسر بين بايثون (البوت) وShizuku: تنفيذ أوامر shell وحقن القرصة. يُستدعى من shizuku.py عبر Chaquopy. */
object Bridge {
    private val pool = Executors.newCachedThreadPool()
    private val newProc: Method by lazy {
        Shizuku::class.java.getDeclaredMethod(
            "newProcess", Array<String>::class.java, Array<String>::class.java, String::class.java
        ).apply { isAccessible = true }
    }

    private fun execBytes(cmd: String, timeoutMs: Long): ByteArray {
        val p = newProc.invoke(null, arrayOf("sh", "-c", "( $cmd\n) 2>/dev/null </dev/null"), null, null) as Process
        val f = pool.submit<ByteArray> { p.inputStream.readBytes() }
        try {
            return f.get(timeoutMs, TimeUnit.MILLISECONDS)
        } catch (e: TimeoutException) {
            f.cancel(true)
            throw RuntimeException("انتهت مهلة الأمر")
        } finally {
            try { p.destroy() } catch (_: Throwable) {}
        }
    }

    /** نص مخرجات الأمر؛ سلسلة فارغة عند أي فشل (مثلاً Shizuku متوقف) كي يعدّه البوت "غير متصل". */
    @JvmStatic
    fun sh(cmd: String, timeoutMs: Int): String = try {
        String(execBytes(cmd, timeoutMs.toLong()), Charsets.UTF_8)
    } catch (e: Throwable) { "" }

    /** يكتب stdout الثنائي (لقطات الشاشة) إلى ملف؛ يرمي استثناءً عند الفشل. */
    @JvmStatic
    fun shToFile(cmd: String, path: String, timeoutMs: Int): Int {
        val b = execBytes(cmd, timeoutMs.toLong())
        if (b.isEmpty()) throw RuntimeException("مخرجات فارغة (Shizuku متوقف؟)")
        File(path).writeBytes(b)
        return b.size
    }

    /** قرصة بإصبعين: الإحداثيات بكسلات حقيقية. تُرجع "OK ..." أو "ERR ...". */
    @JvmStatic
    fun pinch(a0x: Double, a0y: Double, b0x: Double, b0y: Double,
              a1x: Double, a1y: Double, b1x: Double, b1y: Double): String = try {
        "OK " + Injector.pinch(
            floatArrayOf(a0x.toFloat(), a0y.toFloat()), floatArrayOf(b0x.toFloat(), b0y.toFloat()),
            floatArrayOf(a1x.toFloat(), a1y.toFloat()), floatArrayOf(b1x.toFloat(), b1y.toFloat())
        )
    } catch (e: Throwable) { "ERR " + (e.cause ?: e).toString() }
}
