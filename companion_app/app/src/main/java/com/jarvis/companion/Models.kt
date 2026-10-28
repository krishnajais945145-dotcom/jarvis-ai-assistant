package com.jarvis.companion

data class ContactItem(
    val name: String,
    val number: String
)

enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    AUTHENTICATING,
    CONNECTED,
    ERROR
}
