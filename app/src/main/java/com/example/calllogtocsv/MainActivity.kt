package com.example.calllogtocsv

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.ContactsContract
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileWriter

class MainActivity : AppCompatActivity() {

    private lateinit var btnExport: Button
    private lateinit var progressBar: ProgressBar
    private lateinit var tvStatus: TextView
    private var contactCount = 0

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            exportCallLogToCSV()
        } else {
            Toast.makeText(this, "Permission required to read call logs", Toast.LENGTH_LONG).show()
            btnExport.isEnabled = true
            progressBar.visibility = android.view.View.GONE
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        btnExport = findViewById(R.id.btnExport)
        progressBar = findViewById(R.id.progressBar)
        tvStatus = findViewById(R.id.tvStatus)

        btnExport.setOnClickListener {
            btnExport.isEnabled = false
            progressBar.visibility = android.view.View.VISIBLE
            tvStatus.visibility = android.view.View.VISIBLE
            tvStatus.text = "Checking permission..."

            checkPermissionAndExport()
        }
    }

    private fun checkPermissionAndExport() {
        when {
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.READ_CALL_LOG
            ) == PackageManager.PERMISSION_GRANTED -> {
                tvStatus.text = "Reading call logs..."
                exportCallLogToCSV()
            }
            else -> {
                requestPermissionLauncher.launch(Manifest.permission.READ_CALL_LOG)
            }
        }
    }

    private fun exportCallLogToCSV() {
        try {
            tvStatus.text = "Reading call logs..."
            
            val callLogMap = mutableMapOf<String, String?>()
            
            val cursor = contentResolver.query(
                android.provider.CallLog.Calls.CONTENT_URI,
                arrayOf(
                    android.provider.CallLog.Calls.NUMBER,
                    android.provider.CallLog.Calls.CACHED_NAME
                ),
                null,
                null,
                android.provider.CallLog.Calls.DATE + " DESC"
            )

            cursor?.use {
                val numberIndex = it.getColumnIndex(android.provider.CallLog.Calls.NUMBER)
                val nameIndex = it.getColumnIndex(android.provider.CallLog.Calls.CACHED_NAME)

                while (it.moveToNext()) {
                    val number = it.getString(numberIndex)
                    val name = it.getString(nameIndex)
                    
                    if (number != null && number.isNotBlank()) {
                        if (!callLogMap.containsKey(number)) {
                            callLogMap[number] = name
                        }
                    }
                }
            }

            contactCount = callLogMap.size

            if (callLogMap.isEmpty()) {
                runOnUiThread {
                    Toast.makeText(this, "No call logs found", Toast.LENGTH_SHORT).show()
                    btnExport.isEnabled = true
                    progressBar.visibility = android.view.View.GONE
                    tvStatus.visibility = android.view.View.GONE
                }
                return
            }

            tvStatus.text = "Creating CSV file..."
            
            val csvFile = File(cacheDir, "call_log_contacts.csv")
            FileWriter(csvFile).use { writer ->
                writer.append("Phone Number,Name\n")
                
                callLogMap.entries.sortedBy { it.value ?: "" }.forEach { (number, name) ->
                    val displayName = name ?: getContactName(number) ?: ""
                    writer.append("\"$number\",\"$displayName\"\n")
                }
            }

            tvStatus.text = "Preparing to share..."
            shareFile(csvFile)

        } catch (e: Exception) {
            e.printStackTrace()
            runOnUiThread {
                Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                btnExport.isEnabled = true
                progressBar.visibility = android.view.View.GONE
                tvStatus.visibility = android.view.View.GONE
            }
        }
    }

    private fun getContactName(phoneNumber: String): String? {
        try {
            val uri = Uri.withAppendedPath(
                ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
                Uri.encode(phoneNumber)
            )
            
            val cursor = contentResolver.query(
                uri,
                arrayOf(ContactsContract.PhoneLookup.DISPLAY_NAME),
                null,
                null,
                null
            )

            cursor?.use {
                if (it.moveToFirst()) {
                    val nameIndex = it.getColumnIndex(ContactsContract.PhoneLookup.DISPLAY_NAME)
                    if (nameIndex >= 0) {
                        return it.getString(nameIndex)
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return null
    }

    private fun shareFile(file: File) {
        try {
            val uri = FileProvider.getUriForFile(
                this,
                "${packageName}.fileprovider",
                file
            )

            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                type = "text/csv"
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }

            runOnUiThread {
                startActivity(Intent.createChooser(shareIntent, "Share Call Log CSV"))
                
                Toast.makeText(
                    this,
                    "Found $contactCount unique contacts",
                    Toast.LENGTH_SHORT
                ).show()

                btnExport.isEnabled = true
                progressBar.visibility = android.view.View.GONE
                tvStatus.visibility = android.view.View.GONE
            }

        } catch (e: Exception) {
            e.printStackTrace()
            runOnUiThread {
                Toast.makeText(this, "Share error: ${e.message}", Toast.LENGTH_LONG).show()
                btnExport.isEnabled = true
                progressBar.visibility = android.view.View.GONE
                tvStatus.visibility = android.view.View.GONE
            }
        }
    }
}
