package com.jarvis.companion

import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import okhttp3.*
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class WebSocketClientManager(
    private val context: Context,
    private val listener: CompanionEventListener
) {
    interface CompanionEventListener {
        fun onStateChanged(state: ConnectionState, message: String)
        fun onLogMessage(message: String)
        fun onCallTriggered(name: String, number: String)
    }

    private val mainHandler = Handler(Looper.getMainLooper())
    private var client: OkHttpClient? = null
    private var webSocket: WebSocket? = null
    private var currentHost: String = ""
    private var currentPort: Int = 8765
    private var currentPin: String = ""
    private var isIntentionalDisconnect = false
    private var isReconnecting = false

    private val reconnectRunnable = Runnable {
        if (!isIntentionalDisconnect) {
            postLog("Auto-reconnecting to JARVIS...")
            performConnect()
        }
    }

    fun connect(host: String, port: Int, pin: String) {
        isIntentionalDisconnect = false
        mainHandler.removeCallbacks(reconnectRunnable)

        currentHost = host.trim().removePrefix("http://").removePrefix("ws://").removeSuffix("/")
        currentPort = port
        currentPin = pin.trim()

        performConnect()
    }

    private fun performConnect() {
        if (currentHost.isBlank()) return

        // Clean up any lingering websocket or dispatcher jobs
        try {
            webSocket?.cancel()
            client?.dispatcher?.cancelAll()
        } catch (e: Exception) {
            // ignore
        }

        val wsUrl = "ws://$currentHost:$currentPort"
        postLog("Connecting to $wsUrl...")
        postState(ConnectionState.CONNECTING, "Connecting to $currentHost:$currentPort...")

        // Build OkHttpClient with 15s keepalive ping interval to prevent router dropouts without excessive battery use
        client = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .connectTimeout(5, TimeUnit.SECONDS)
            .pingInterval(15, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()

        val request = Request.Builder()
            .url(wsUrl)
            .build()

        webSocket = client?.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                isReconnecting = false
                mainHandler.removeCallbacks(reconnectRunnable)
                postLog("Wi-Fi link established. Authenticating...")
                postState(ConnectionState.AUTHENTICATING, "Authenticating with JARVIS...")

                // Send Auth payload
                val authPayload = JSONObject().apply {
                    put("type", "auth")
                    put("pin", currentPin)
                    put("device", "Realme 10 Pro")
                    put("model", "${Build.MANUFACTURER} ${Build.MODEL}")
                }
                ws.send(authPayload.toString())
            }

            override fun onMessage(ws: WebSocket, text: String) {
                try {
                    val json = JSONObject(text)
                    handleIncomingMessage(ws, json)
                } catch (e: Exception) {
                    postLog("Error parsing message: ${e.localizedMessage}")
                }
            }

            override fun onClosing(ws: WebSocket, code: Int, reason: String) {
                try {
                    ws.close(1000, null)
                } catch (e: Exception) {
                    ws.cancel()
                }
                postState(ConnectionState.DISCONNECTED, "Disconnected from JARVIS.")
                scheduleReconnect()
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                try {
                    ws.cancel()
                } catch (e: Exception) {
                    // ignore
                }
                if (!isIntentionalDisconnect) {
                    postState(ConnectionState.ERROR, "Link interrupted. Reconnecting in 2s...")
                    postLog("Connection notice: ${t.localizedMessage ?: "Timeout"}")
                    scheduleReconnect()
                }
            }
        })
    }

    private fun scheduleReconnect() {
        if (isIntentionalDisconnect) return
        mainHandler.removeCallbacks(reconnectRunnable)
        mainHandler.postDelayed(reconnectRunnable, 2000)
    }

    private fun handleIncomingMessage(ws: WebSocket, json: JSONObject) {
        val type = json.optString("type")

        when (type) {
            "auth_ok" -> {
                val server = json.optString("server", "JARVIS Windows")
                postState(ConnectionState.CONNECTED, "Paired & connected with $server")
                postLog("Authentication accepted by $server!")
            }

            "auth_error" -> {
                val msg = json.optString("message", "Authentication rejected.")
                postState(ConnectionState.ERROR, "Auth failed: $msg")
                postLog("Auth Error: $msg")
            }

            "search_contact" -> {
                val reqId = json.optString("req_id")
                val query = json.optString("query")
                postLog("Searching phone contacts for: '$query'")

                val matches = ContactHelper.searchContacts(context, query)
                postLog("Found ${matches.size} match(es) for '$query'")

                val matchArray = JSONArray()
                matches.forEach { c ->
                    val obj = JSONObject().apply {
                        put("name", c.name)
                        put("number", c.number)
                    }
                    matchArray.put(obj)
                }

                val response = JSONObject().apply {
                    put("type", "search_contact_result")
                    put("req_id", reqId)
                    put("query", query)
                    put("matches", matchArray)
                }
                ws.send(response.toString())
            }

            "make_call" -> {
                val reqId = json.optString("req_id")
                val number = json.optString("number")
                val name = json.optString("name", "Contact")

                postLog("📞 JARVIS triggered call to: $name ($number)")

                // Trigger direct phone call immediately
                mainHandler.post {
                    listener.onCallTriggered(name, number)
                    val (success, msg) = CallManager.makePhoneCall(context, number)

                    postLog(if (success) "Dialing $name ($number)..." else "Call error: $msg")

                    val response = JSONObject().apply {
                        put("type", "make_call_result")
                        put("req_id", reqId)
                        put("name", name)
                        put("number", number)
                        put("success", success)
                        put("message", msg)
                    }
                    ws.send(response.toString())
                }
            }
        }
    }

    fun disconnect() {
        isIntentionalDisconnect = true
        mainHandler.removeCallbacks(reconnectRunnable)
        try {
            webSocket?.close(1000, "User disconnected")
        } catch (e: Exception) {
            // ignore
        }
        webSocket = null
        client?.dispatcher?.executorService?.shutdown()
        client = null
        postState(ConnectionState.DISCONNECTED, "Disconnected from JARVIS.")
    }

    private fun postState(state: ConnectionState, message: String) {
        mainHandler.post { listener.onStateChanged(state, message) }
    }

    private fun postLog(message: String) {
        mainHandler.post { listener.onLogMessage(message) }
    }
}
