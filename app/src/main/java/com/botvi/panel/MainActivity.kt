package com.botvi.panel

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.TextView
import rikka.shizuku.Shizuku

class MainActivity : Activity() {
    private val ui = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var web: WebView
    private var loaded = false

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        if (Build.VERSION.SDK_INT >= 33)
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        status = TextView(this).apply {
            textSize = 14f; gravity = Gravity.CENTER; setPadding(12, 10, 12, 10)
            setTextColor(Color.WHITE); setBackgroundColor(Color.DKGRAY)
            setOnClickListener { askShizuku() }
        }
        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            webViewClient = object : WebViewClient() {
                override fun onReceivedError(v: WebView, r: WebResourceRequest, e: WebResourceError) {
                    if (r.isForMainFrame) { loaded = false; ui.postDelayed({ tryLoad() }, 1500) }
                }
                override fun onPageFinished(v: WebView, url: String) { loaded = true }
            }
        }
        val bar = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        fun tb(t: String, u: String) = TextView(this).apply {
            text = t; textSize = 14f; gravity = Gravity.CENTER; setPadding(12, 12, 12, 12)
            setTextColor(Color.WHITE); setBackgroundColor(Color.parseColor("#4f46e5"))
            setOnClickListener { web.loadUrl("http://127.0.0.1:8080$u") }
        }
        bar.addView(tb("اللوحة", "/"), LinearLayout.LayoutParams(0, -2, 1f))
        bar.addView(tb("معايرة المباني", "/layout"), LinearLayout.LayoutParams(0, -2, 1f))
        bar.addView(tb("ملفات التشخيص", "/debug"), LinearLayout.LayoutParams(0, -2, 1f))
        root.addView(status)
        root.addView(bar)
        root.addView(web, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        startForegroundService(Intent(this, BotService::class.java))
        ui.postDelayed({ tick() }, 500)
    }

    private fun askShizuku() {
        if (Shizuku.pingBinder() && Shizuku.checkSelfPermission() != PackageManager.PERMISSION_GRANTED)
            Shizuku.requestPermission(100)
    }

    private fun tryLoad() { web.loadUrl("http://127.0.0.1:8080/") }

    private fun tick() {
        val ping = Shizuku.pingBinder()
        val granted = ping && Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
        status.text = when {
            !ping -> "Shizuku غير شغّال: شغّله أولاً"
            !granted -> "اضغط هنا لمنح إذن Shizuku"
            BotService.lastError != null -> "خطأ بايثون: " + BotService.lastError
            else -> "Shizuku متصل ✓ — البوت يعمل في الخلفية"
        }
        if (ping && !granted) askShizuku()
        if (!loaded && BotService.started) tryLoad()
        ui.postDelayed({ tick() }, 3000)
    }

    @Deprecated("back")
    override fun onBackPressed() { if (web.canGoBack()) web.goBack() else moveTaskToBack(true) }
}
