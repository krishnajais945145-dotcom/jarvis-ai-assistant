package com.jarvis.companion

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.content.SharedPreferences
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.os.PowerManager
import android.provider.Settings
import android.text.method.ScrollingMovementMethod
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity(), WebSocketClientManager.CompanionEventListener {

    private lateinit var tvStatusBadge: TextView
    private lateinit var tvStatusDetails: TextView
    private lateinit var etHostIp: TextInputEditText
    private lateinit var etPort: TextInputEditText
    private lateinit var etPin: TextInputEditText
    private lateinit var btnConnect: MaterialButton

    private lateinit var tvPermContacts: TextView
    private lateinit var tvPermCalls: TextView
    private lateinit var btnPermissions: MaterialButton
    private lateinit var tvActivityLog: TextView

    private lateinit var prefs: SharedPreferences
    private var companionService: CompanionService? = null
    private var isBound = false
    private var currentState: ConnectionState = ConnectionState.DISCONNECTED

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            val localBinder = binder as CompanionService.LocalBinder
            companionService = localBinder.getService()
            isBound = true
            companionService?.uiListener = this@MainActivity

            // Sync current state
            companionService?.let {
                onStateChanged(it.currentState, if (it.currentState == ConnectionState.CONNECTED) "Paired & connected with JARVIS Windows" else "Ready")
            }
        }

        override fun onServiceDisconnected(name: ComponentName?) {
            companionService?.uiListener = null
            companionService = null
            isBound = false
        }
    }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { _ ->
        refreshPermissionStatus()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        prefs = getSharedPreferences("jarvis_companion_prefs", Context.MODE_PRIVATE)

        initViews()
        loadSavedConfig()
        refreshPermissionStatus()
        checkAndPromptPermissions()

        // Bind to background service
        val intent = Intent(this, CompanionService::class.java)
        bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
    }

    override fun onResume() {
        super.onResume()
        refreshPermissionStatus()
    }

    private fun initViews() {
        tvStatusBadge = findViewById(R.id.tvStatusBadge)
        tvStatusDetails = findViewById(R.id.tvStatusDetails)
        etHostIp = findViewById(R.id.etHostIp)
        etPort = findViewById(R.id.etPort)
        etPin = findViewById(R.id.etPin)
        btnConnect = findViewById(R.id.btnConnect)

        tvPermContacts = findViewById(R.id.tvPermContacts)
        tvPermCalls = findViewById(R.id.tvPermCalls)
        btnPermissions = findViewById(R.id.btnPermissions)
        tvActivityLog = findViewById(R.id.tvActivityLog)

        tvActivityLog.movementMethod = ScrollingMovementMethod()

        btnConnect.setOnClickListener {
            try {
                if (currentState == ConnectionState.CONNECTED || currentState == ConnectionState.CONNECTING) {
                    CompanionService.stop(this)
                    companionService?.getSocketManager()?.disconnect()
                    onStateChanged(ConnectionState.DISCONNECTED, "Disconnected from JARVIS.")
                } else {
                    saveConfig()
                    val ip = etHostIp.text.toString().trim()
                    val portStr = etPort.text.toString().trim()
                    val pin = etPin.text.toString().trim()

                    if (ip.isBlank()) {
                        Toast.makeText(this, "Please enter your laptop IP address", Toast.LENGTH_SHORT).show()
                        return@setOnClickListener
                    }
                    val port = portStr.toIntOrNull() ?: 8765

                    // Start 24/7 persistent foreground service
                    CompanionService.start(this, ip, port, pin)
                    if (!isBound) {
                        val serviceIntent = Intent(this, CompanionService::class.java)
                        bindService(serviceIntent, serviceConnection, Context.BIND_AUTO_CREATE)
                    }
                }
            } catch (e: Exception) {
                Toast.makeText(this, "Connection error: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
                e.printStackTrace()
            }
        }

        btnPermissions.setOnClickListener {
            requestRequiredPermissions()
        }
    }

    private fun checkAndPromptPermissions() {
        val hasContacts = ContactHelper.hasContactsPermission(this)
        val hasCalls = CallManager.hasCallPermission(this)
        if (!hasContacts || !hasCalls) {
            requestRequiredPermissions()
        }
        checkBatteryOptimization()
    }

    private fun checkBatteryOptimization() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager
                val pkgName = packageName
                if (powerManager != null && !powerManager.isIgnoringBatteryOptimizations(pkgName)) {
                    val intent = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
                    startActivity(intent)
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun requestRequiredPermissions() {
        val perms = mutableListOf(
            Manifest.permission.READ_CONTACTS,
            Manifest.permission.CALL_PHONE
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        permissionLauncher.launch(perms.toTypedArray())
    }

    private fun refreshPermissionStatus() {
        val hasContacts = ContactHelper.hasContactsPermission(this)
        val hasCalls = CallManager.hasCallPermission(this)

        if (hasContacts) {
            tvPermContacts.text = "Granted"
            tvPermContacts.setTextColor(Color.parseColor("#10B981"))
        } else {
            tvPermContacts.text = "Denied"
            tvPermContacts.setTextColor(Color.parseColor("#EF4444"))
        }

        if (hasCalls) {
            tvPermCalls.text = "Granted"
            tvPermCalls.setTextColor(Color.parseColor("#10B981"))
        } else {
            tvPermCalls.text = "Denied"
            tvPermCalls.setTextColor(Color.parseColor("#EF4444"))
        }

        if (hasContacts && hasCalls) {
            btnPermissions.text = getString(R.string.permissions_granted)
            btnPermissions.isEnabled = false
            btnPermissions.alpha = 0.5f
        } else {
            btnPermissions.text = getString(R.string.grant_permissions)
            btnPermissions.isEnabled = true
            btnPermissions.alpha = 1.0f
        }
    }

    private fun loadSavedConfig() {
        val savedIp = prefs.getString("host_ip", "192.168.137.183")
        val savedPort = prefs.getString("host_port", "8765")
        val savedPin = prefs.getString("pin", "742918")

        etHostIp.setText(savedIp)
        etPort.setText(savedPort)
        etPin.setText(savedPin)
    }

    private fun saveConfig() {
        prefs.edit().apply {
            putString("host_ip", etHostIp.text.toString().trim())
            putString("host_port", etPort.text.toString().trim())
            putString("pin", etPin.text.toString().trim())
            apply()
        }
    }

    override fun onStateChanged(state: ConnectionState, message: String) {
        currentState = state
        tvStatusDetails.text = message

        when (state) {
            ConnectionState.DISCONNECTED -> {
                tvStatusBadge.text = getString(R.string.status_disconnected)
                tvStatusBadge.setTextColor(Color.parseColor("#EF4444"))
                tvStatusBadge.setBackgroundColor(Color.parseColor("#20EF4444"))
                btnConnect.text = getString(R.string.connect)
                btnConnect.setBackgroundColor(Color.parseColor("#00E5FF"))
                btnConnect.setTextColor(Color.parseColor("#090D16"))
            }
            ConnectionState.CONNECTING, ConnectionState.AUTHENTICATING -> {
                tvStatusBadge.text = getString(R.string.status_connecting)
                tvStatusBadge.setTextColor(Color.parseColor("#F59E0B"))
                tvStatusBadge.setBackgroundColor(Color.parseColor("#20F59E0B"))
                btnConnect.text = "ABORT"
                btnConnect.setBackgroundColor(Color.parseColor("#F59E0B"))
                btnConnect.setTextColor(Color.parseColor("#090D16"))
            }
            ConnectionState.CONNECTED -> {
                tvStatusBadge.text = getString(R.string.status_connected)
                tvStatusBadge.setTextColor(Color.parseColor("#10B981"))
                tvStatusBadge.setBackgroundColor(Color.parseColor("#2010B981"))
                btnConnect.text = getString(R.string.disconnect)
                btnConnect.setBackgroundColor(Color.parseColor("#EF4444"))
                btnConnect.setTextColor(Color.WHITE)
            }
            ConnectionState.ERROR -> {
                tvStatusBadge.text = "RECONNECTING"
                tvStatusBadge.setTextColor(Color.parseColor("#F59E0B"))
                tvStatusBadge.setBackgroundColor(Color.parseColor("#20F59E0B"))
                btnConnect.text = "DISCONNECT"
                btnConnect.setBackgroundColor(Color.parseColor("#EF4444"))
                btnConnect.setTextColor(Color.WHITE)
            }
        }
    }

    override fun onLogMessage(message: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val formatted = "[$time] $message\n"
        tvActivityLog.append(formatted)

        val scrollAmount = tvActivityLog.layout?.let { layout ->
            layout.getLineTop(tvActivityLog.lineCount) - tvActivityLog.height
        } ?: 0
        if (scrollAmount > 0) {
            tvActivityLog.scrollTo(0, scrollAmount)
        }
    }

    override fun onCallTriggered(name: String, number: String) {
        // Direct call without blocking dialog
        Toast.makeText(this, "📞 JARVIS: Calling $name ($number)", Toast.LENGTH_SHORT).show()
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isBound) {
            companionService?.uiListener = null
            unbindService(serviceConnection)
            isBound = false
        }
        // Do NOT stop companionService here — it stays connected 24/7 in background!
    }
}
