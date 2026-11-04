package com.botvi.panel

import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.view.InputDevice
import android.view.InputEvent
import android.view.MotionEvent
import org.lsposed.hiddenapibypass.HiddenApiBypass
import rikka.shizuku.ShizukuBinderWrapper
import rikka.shizuku.SystemServiceHelper
import java.lang.reflect.Method

/** حقن لمس متعدد الأصابع عبر IInputManager بصلاحية shell من Shizuku (بدل sendevent المرفوض). */
object Injector {
    private var im: Any? = null
    private var method: Method? = null

    @Synchronized
    private fun init() {
        if (im != null) return
        if (Build.VERSION.SDK_INT >= 28) HiddenApiBypass.addHiddenApiExemptions("L")
        val binder = ShizukuBinderWrapper(SystemServiceHelper.getSystemService("input"))
        val stub = Class.forName("android.hardware.input.IInputManager\$Stub")
        im = stub.getMethod("asInterface", IBinder::class.java).invoke(null, binder)
        method = Class.forName("android.hardware.input.IInputManager").methods.first { it.name == "injectInputEvent" }
    }

    private fun inject(ev: InputEvent): Boolean {
        val m = method!!
        val r = if (m.parameterTypes.size >= 3) m.invoke(im, ev, 0, -1) else m.invoke(im, ev, 0)
        return r as? Boolean ?: true
    }

    private fun touchDeviceId(): Int = InputDevice.getDeviceIds().firstOrNull {
        InputDevice.getDevice(it)?.supportsSource(InputDevice.SOURCE_TOUCHSCREEN) == true
    } ?: 0

    /** الإصبع الأول من a0 إلى a1 والثاني من b0 إلى b1 (بكسلات حقيقية). */
    fun pinch(a0: FloatArray, b0: FloatArray, a1: FloatArray, b1: FloatArray, steps: Int = 24, stepMs: Long = 16): String {
        init()
        val dev = touchDeviceId()
        val props = Array(2) { i -> MotionEvent.PointerProperties().apply { id = i; toolType = MotionEvent.TOOL_TYPE_FINGER } }
        fun coords(t: Float) = Array(2) { i ->
            val s = if (i == 0) a0 else b0
            val e = if (i == 0) a1 else b1
            MotionEvent.PointerCoords().apply {
                x = s[0] + (e[0] - s[0]) * t; y = s[1] + (e[1] - s[1]) * t; pressure = 1f; size = 1f
            }
        }
        val down = SystemClock.uptimeMillis()
        var fails = 0
        fun send(action: Int, count: Int, t: Float) {
            val ev = MotionEvent.obtain(
                down, SystemClock.uptimeMillis(), action, count, props, coords(t),
                0, 0, 1f, 1f, dev, 0, InputDevice.SOURCE_TOUCHSCREEN, 0
            )
            if (!inject(ev)) fails++
            ev.recycle()
        }
        val shift = MotionEvent.ACTION_POINTER_INDEX_SHIFT
        send(MotionEvent.ACTION_DOWN, 1, 0f); Thread.sleep(40)
        send(MotionEvent.ACTION_POINTER_DOWN or (1 shl shift), 2, 0f); Thread.sleep(60)
        for (i in 1..steps) { send(MotionEvent.ACTION_MOVE, 2, i.toFloat() / steps); Thread.sleep(stepMs) }
        Thread.sleep(40)
        send(MotionEvent.ACTION_POINTER_UP or (1 shl shift), 2, 1f); Thread.sleep(30)
        send(MotionEvent.ACTION_UP, 1, 1f)
        return "dev=$dev fails=$fails"
    }
}
