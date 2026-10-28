package com.jarvis.companion

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.widget.Toast
import androidx.core.app.NotificationCompat

class CompanionService : Service(), WebSocketClientManager.CompanionEventListener {

    inner class LocalBinder : Binder() {
        fun getService(): CompanionService = this@CompanionService
    }

    private val binder = LocalBinder()
    private var socketManager: WebSocketClientManager? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null
    var currentState: ConnectionState = ConnectionState.DISCONNECTED
        private set

    var uiListener: WebSocketClientManager.CompanionEventListener? = null

    companion object {
        const val CHANNEL_ID = "jarvis_companion_channel"
        const val NOTIFICATION_ID = 1001
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"
        const val EXTRA_HOST = "EXTRA_HOST"
        const val EXTRA_PORT = "EXTRA_PORT"
        const val EXTRA_PIN = "EXTRA_PIN"

        fun start(context: Context, host: String, port: Int, pin: String) {
            val intent = Intent(context, CompanionService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_HOST, host)
                putExtra(EXTRA_PORT, port)
                putExtra(EXTRA_PIN, pin)
            }
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(intent)
                } else {
                    context.startService(intent)
                }
            } catch (e: Exception) {
                try {
                    context.startService(intent)
                } catch (ex: Exception) {
                    ex.printStackTrace()
                }
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, CompanionService::class.java).apply {
                action = ACTION_STOP
            }
            try {
                context.stopService(intent)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        socketManager = WebSocketClientManager(this, this)
        acquireLocks()
    }

    private fun acquireLocks() {
        try {
            if (wakeLock == null) {
                val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager
                wakeLock = powerManager?.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK,
                    "JarvisCompanion::KeepAliveWakeLock"
                )?.apply {
                    setReferenceCounted(false)
                    acquire(24 * 60 * 60 * 1000L) // 24 hours keepalive
                }
            }

            if (wifiLock == null) {
                val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
                val lockMode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    WifiManager.WIFI_MODE_FULL_LOW_LATENCY
                } else {
                    WifiManager.WIFI_MODE_FULL_HIGH_PERF
                }
                wifiLock = wifiManager?.createWifiLock(lockMode, "JarvisCompanion::WifiLock")?.apply {
                    setReferenceCounted(false)
                    acquire()
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun releaseLocks() {
        try {
            wakeLock?.let {
                if (it.isHeld) it.release()
            }
            wakeLock = null

            wifiLock?.let {
                if (it.isHeld) it.release()
            }
            wifiLock = null
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            socketManager?.disconnect()
            releaseLocks()
            try {
                stopForeground(STOP_FOREGROUND_REMOVE)
            } catch (e: Exception) {
                // ignore
            }
            stopSelf()
            return START_NOT_STICKY
        }

        acquireLocks()
        val host = intent?.getStringExtra(EXTRA_HOST) ?: "192.168.137.183"
        val port = intent?.getIntExtra(EXTRA_PORT, 8765) ?: 8765
        val pin = intent?.getStringExtra(EXTRA_PIN) ?: "742918"

        try {
            startForegroundNotification("Connecting to JARVIS ($host)...")
        } catch (e: Exception) {
            e.printStackTrace()
        }

        socketManager?.connect(host, port, pin)
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder = binder

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                val channel = NotificationChannel(
                    CHANNEL_ID,
                    "JARVIS Companion Service",
                    NotificationManager.IMPORTANCE_LOW
                ).apply {
                    description = "Maintains Wi-Fi link with JARVIS on your laptop"
                    setShowBadge(false)
                }
                val manager = getSystemService(NotificationManager::class.java)
                manager.createNotificationChannel(channel)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun startForegroundNotification(statusText: String) {
        try {
            val pendingIntent = PendingIntent.getActivity(
                this,
                0,
                Intent(this, MainActivity::class.java),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )

            val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("J.A.R.V.I.S. Companion Active")
                .setContentText(statusText)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build()

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE or ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                )
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun updateNotification(statusText: String) {
        try {
            val pendingIntent = PendingIntent.getActivity(
                this,
                0,
                Intent(this, MainActivity::class.java),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )

            val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("J.A.R.V.I.S. Companion Active")
                .setContentText(statusText)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build()

            val manager = getSystemService(NotificationManager::class.java)
            manager.notify(NOTIFICATION_ID, notification)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun onStateChanged(state: ConnectionState, message: String) {
        currentState = state
        updateNotification(message)
        uiListener?.onStateChanged(state, message)
    }

    override fun onLogMessage(message: String) {
        uiListener?.onLogMessage(message)
    }

    override fun onCallTriggered(name: String, number: String) {
        try {
            Toast.makeText(this, "📞 JARVIS: Calling $name ($number)", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            e.printStackTrace()
        }
        uiListener?.onCallTriggered(name, number)
    }

    fun getSocketManager(): WebSocketClientManager? = socketManager

    override fun onDestroy() {
        super.onDestroy()
        releaseLocks()
        socketManager?.disconnect()
    }
}
