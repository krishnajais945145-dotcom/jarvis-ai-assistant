package com.jarvis.companion

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.telecom.TelecomManager
import androidx.core.content.ContextCompat

object CallManager {

    fun hasCallPermission(context: Context): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.CALL_PHONE
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * Dials a contact number directly.
     * Primary: TelecomManager.placeCall() (Works seamlessly from background services on Android 10-14+ without activity start restrictions).
     * Fallback: Intent.ACTION_CALL with FLAG_ACTIVITY_NEW_TASK.
     */
    fun makePhoneCall(context: Context, rawNumber: String): Pair<Boolean, String> {
        if (!hasCallPermission(context)) {
            return Pair(false, "CALL_PHONE permission is not granted on this phone.")
        }

        val cleanNumber = rawNumber.replace(Regex("[^0-9+]"), "")
        if (cleanNumber.isBlank()) {
            return Pair(false, "Invalid phone number provided.")
        }

        val uri = Uri.parse("tel:$cleanNumber")

        // 1. Primary: Direct system telephony subsystem invocation via TelecomManager
        try {
            val telecomManager = context.getSystemService(Context.TELECOM_SERVICE) as? TelecomManager
            if (telecomManager != null) {
                telecomManager.placeCall(uri, Bundle())
                return Pair(true, "Dialing $cleanNumber successfully via Telecom.")
            }
        } catch (e: SecurityException) {
            // Telecom security exception, continue to intent fallback
        } catch (e: Exception) {
            // Any other telecom error, continue to intent fallback
        }

        // 2. Secondary Fallback: Standard Intent.ACTION_CALL
        return try {
            val callIntent = Intent(Intent.ACTION_CALL).apply {
                data = uri
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
            }
            context.startActivity(callIntent)
            Pair(true, "Dialing $cleanNumber successfully.")
        } catch (e: Exception) {
            Pair(false, "Error placing call: ${e.localizedMessage}")
        }
    }
}
