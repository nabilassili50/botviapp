package com.botvi.panel

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlin.concurrent.thread

/** خدمة أمامية تُبقي بايثون (لوحة البوت) شغّالة في الخلفية. */
class BotService : Service() {
    override fun onBind(i: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel("bot", "البوت", NotificationManager.IMPORTANCE_LOW))
        startForeground(
            1, Notification.Builder(this, "bot").setSmallIcon(android.R.drawable.ic_media_play)
                .setContentTitle("بوت لوردز يعمل").setContentText("اللوحة على المنفذ 8080").build()
        )
        if (!started) {
            started = true
            thread(name = "botvi-py") {
                try {
                    val home = Assets.sync(this).absolutePath
                    if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                    Python.getInstance().getModule("apk_main").callAttr("run", home)
                } catch (t: Throwable) {
                    Log.e("Botvi", "python stopped", t)
                    lastError = (t.cause ?: t).toString()
                }
                started = false
            }
        }
        return START_STICKY
    }

    companion object {
        @Volatile var started = false
        @Volatile var lastError: String? = null
    }
}
