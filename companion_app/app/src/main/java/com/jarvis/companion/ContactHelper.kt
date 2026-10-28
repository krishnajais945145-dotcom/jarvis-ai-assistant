package com.jarvis.companion

import android.content.Context
import android.content.pm.PackageManager
import android.provider.ContactsContract
import androidx.core.content.ContextCompat

object ContactHelper {

    fun hasContactsPermission(context: Context): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.READ_CONTACTS
        ) == PackageManager.PERMISSION_GRANTED
    }

    private val relationMap = mapOf(
        "mummy" to listOf("mummy", "mom", "maa", "mother", "मम्मी", "माँ"),
        "mom" to listOf("mom", "mummy", "maa", "mother", "मम्मी"),
        "maa" to listOf("maa", "mummy", "mom", "mother", "माँ", "मम्मी"),
        "papa" to listOf("papa", "dad", "father", "पापा", "पिताजी"),
        "dad" to listOf("dad", "papa", "father", "पापा"),
        "bhai" to listOf("bhai", "bhaiya", "bro", "brother", "भाई", "भैया"),
        "bhaiya" to listOf("bhaiya", "bhai", "bro", "brother", "भैया", "भाई"),
        "didi" to listOf("didi", "sis", "sister", "दीदी"),
        "sister" to listOf("sister", "didi", "sis", "दीदी")
    )

    private fun scoreContact(contactName: String, queryWords: List<String>, fullQuery: String): Int {
        val cleanName = contactName.trim().lowercase()
        if (cleanName.isBlank() || fullQuery.isBlank()) return 0

        // 1. EXACT match (e.g. contact "Aman" == query "aman")
        if (cleanName == fullQuery) {
            return 10000
        }

        // 2. Relation alias exact match (e.g. query "mummy", contact "Maa" or "Mom")
        val aliases = relationMap[fullQuery]
        if (aliases != null && aliases.any { cleanName == it }) {
            return 9000
        }

        val nameWords = cleanName.split(Regex("[\\s._-]+")).filter { it.isNotBlank() }

        // 3. Exact word token match (e.g. contact "Aman Kumar", query "Aman")
        val exactWordMatches = queryWords.count { qWord -> nameWords.contains(qWord) }
        if (exactWordMatches == queryWords.size) {
            return 8000 - cleanName.length
        }

        // 4. Starts with full query (e.g. contact "Aman Deep", query "Aman")
        if (cleanName.startsWith(fullQuery)) {
            return 7000 - cleanName.length
        }

        // 5. Name words start with query (e.g. contact "Bhai Aman", query "Aman")
        if (nameWords.any { it.startsWith(fullQuery) }) {
            return 6000 - cleanName.length
        }

        // 6. Any query word matched as exact word in name
        if (exactWordMatches > 0) {
            return (5000 * exactWordMatches / queryWords.size) - cleanName.length
        }

        // 7. Substring inside a word ONLY if query length >= 4 (to avoid 2-3 letter accidental matches)
        // Strictly penalized with low score so it never beats real word matches
        if (fullQuery.length >= 4 && cleanName.contains(fullQuery)) {
            return 1000 - cleanName.length
        }

        return 0
    }

    /**
     * Searches phone contacts by name with intelligent ranking.
     * Returns deduplicated contacts sorted with highest relevance first.
     */
    fun searchContacts(context: Context, query: String): List<ContactItem> {
        if (!hasContactsPermission(context)) {
            return emptyList()
        }

        val cleanQuery = query.trim().lowercase()
        if (cleanQuery.isBlank()) return emptyList()

        val queryWords = cleanQuery.split(Regex("[\\s._-]+")).filter { it.isNotBlank() }
        val scoredList = mutableListOf<Pair<ContactItem, Int>>()
        val seenNumbers = mutableSetOf<String>()

        val contentResolver = context.contentResolver
        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER,
            ContactsContract.CommonDataKinds.Phone.IS_SUPER_PRIMARY
        )
        val uri = ContactsContract.CommonDataKinds.Phone.CONTENT_URI

        try {
            contentResolver.query(uri, projection, null, null, null)?.use { cursor ->
                val nameIndex = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIndex = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                val primaryIndex = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.IS_SUPER_PRIMARY)

                while (cursor.moveToNext()) {
                    val name = cursor.getString(nameIndex) ?: ""
                    val rawNumber = cursor.getString(numberIndex) ?: ""
                    val isSuperPrimary = if (primaryIndex >= 0) cursor.getInt(primaryIndex) else 0
                    val normalizedNumber = rawNumber.replace(Regex("[^0-9+]"), "")

                    if (normalizedNumber.isBlank() || seenNumbers.contains(normalizedNumber)) {
                        continue
                    }

                    val baseScore = scoreContact(name, queryWords, cleanQuery)
                    if (baseScore > 0) {
                        seenNumbers.add(normalizedNumber)
                        val finalScore = baseScore + (if (isSuperPrimary > 0) 50 else 0)
                        scoredList.add(
                            Pair(
                                ContactItem(name = name.trim(), number = rawNumber.trim()),
                                finalScore
                            )
                        )
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        // Sort strictly by highest match score first
        scoredList.sortByDescending { it.second }

        return scoredList.map { it.first }
    }
}
