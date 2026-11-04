package com.botvi.panel

import android.content.Context
import java.io.File

/** ينسخ ملفات البوت من assets/botvi إلى filesDir/botvi (قابل للكتابة) دون المساس بإعدادات المستخدم. */
object Assets {
    private val keep = setOf("settings.json", "touch_dev.json", "zoom_mode.txt")

    fun sync(ctx: Context): File {
        val out = File(ctx.filesDir, "botvi").apply { mkdirs() }
        copyDir(ctx, "botvi", out)
        return out
    }

    private fun copyDir(ctx: Context, asset: String, dst: File) {
        val names = ctx.assets.list(asset) ?: return
        dst.mkdirs()
        for (n in names) {
            val child = "$asset/$n"
            val sub = ctx.assets.list(child)
            if (sub != null && sub.isNotEmpty()) copyDir(ctx, child, File(dst, n))
            else {
                val f = File(dst, n)
                if (n in keep && f.exists()) continue
                ctx.assets.open(child).use { i -> f.outputStream().use { o -> i.copyTo(o) } }
            }
        }
    }
}
