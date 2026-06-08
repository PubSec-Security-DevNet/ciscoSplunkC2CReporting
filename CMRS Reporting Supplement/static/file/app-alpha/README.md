# Splunk CMRS Submission Add-on

Automate the submission of endpoint compliance data to the DISA Continuous Monitoring and Risk Scoring (CMRS) system. This Splunk add-on transforms Cisco C2C endpoint data into DoD-compliant CMRS XML and submits it via secure mTLS to the DISA gateway.

---

## Table of Contents

- [Splunk CMRS Submission Add-on](#splunk-cmrs-submission-add-on)
  - [Table of Contents](#table-of-contents)
  - [Quick Start](#quick-start)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Deploy the Add-on](#deploy-the-add-on)
  - [Configuration Overview](#configuration-overview)
    - [General Settings](#general-settings)
      - [Configuration → **General**](#configuration--general)
      - [Configuration → **Online Submission**](#configuration--online-submission)
      - [Configuration → **Offline Submission**](#configuration--offline-submission)
      - [Configuration → **COAMS Configuration**](#configuration--coams-configuration)
      - [Configuration → **Logging**](#configuration--logging)
      - [Configuration → **Advanced**](#configuration--advanced)
        - [Logging \& Debug](#logging--debug)
        - [Performance](#performance)
        - [Compliance Rule Mapping](#compliance-rule-mapping)
  - [Creating and Managing Inputs](#creating-and-managing-inputs)
    - [Create a New Input](#create-a-new-input)
    - [Input Validation](#input-validation)
    - [Enable/Disable an Input](#enabledisable-an-input)
    - [Monitor Input Execution](#monitor-input-execution)
  - [Testing and Troubleshooting](#testing-and-troubleshooting)
    - [Test Connection](#test-connection)
    - [Common Issues and Solutions](#common-issues-and-solutions)
      - ["unable to get local issuer certificate"](#unable-to-get-local-issuer-certificate)
      - ["certificate verify failed"](#certificate-verify-failed)
      - ["Connection refused" or "timeout"](#connection-refused-or-timeout)
      - ["CSV file not found" or "Permission denied"](#csv-file-not-found-or-permission-denied)
      - [Input Doesn't Run on Schedule](#input-doesnt-run-on-schedule)
  - [Support \& Documentation](#support--documentation)
  - [Version History](#version-history)
  - [License](#license)

---

## Quick Start

1. **Install** the app in your Splunk instance
2. **Complete General Settings** — Configure publisher info and data source
3. **Set up Online Submission** — Configure mTLS credentials
4. **Test Connection** — Validate endpoint connectivity
5. **Configure Logging** (optional) — Set log verbosity
6. **Create an Input** — Schedule automatic submissions

---

## Installation

### Prerequisites

- Splunk 9.0 or later
- mTLS client certificate (PEM format)
- mTLS private key (PEM format)  
- CA trust bundle (PEM format) for DISA CMRS endpoint verification
- CSV report containing Cisco C2C endpoint data
- DISA CMRS SOAP endpoint URL and DoD organizational IDs

### Deploy the Add-on

1. **Via Splunk UI:**
   - Navigate to Apps > Manage Apps
   - Click "Install app from file"
   - Select the `.tgz` package
   - Click "Upload"

2. **Via CLI:**
   - Follow the default CLI installation method for your selected OS

---

## Configuration Overview

The Configuration tab has 6 sections. **All fields marked with `*` are required** before you can create a working input.

### General Settings

#### Configuration → **General**

![Configuration - General Tab](img/config-general.png)

The General tab contains core settings shared across all submission modes (online and offline).

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| **Publisher Version** | Text | **Yes** | Version of this reporting solution. Read-only, always 3.0.0. | `3.0.0` |
| **Publisher Name** | Text | **Yes** | FQDN or unique identifier for your Splunk search head. Used in all CMRS submissions for identification. | `splunk-01.example.com` |
| **Report Source CSV Path** | Text | **Yes** | Absolute path to the Cisco C2C endpoint CSV file. This file must be accessible by the `splunk` user. | The defaults are: Linux: `/opt/splunk/etc/apps/cisco-catalyst-app/lookups/cisco_catalyst_analytics_reports.csv` Windows:`C:\Program Files\Splunk\etc\apps\cisco-catalyst-app\lookups\cisco_catalyst_analytics_reports.csv` |
| **Reporting Batch Size** | Number | **Yes** | Number of endpoints to include in each SOAP submission. **Recommended: 200** (theoretical maximum ~250 per submission). | `200` |
| **ACAS Delta (Days)** | Number | **Yes** | Expected ACAS scan frequency in days. Endpoints not scanned within this window are marked as "Failed" for vulnerability compliance. | `7` |
| **ISE Version** | Text | **Yes** | Version of your Cisco ISE deployment. | Use the \<MAJOR\>.\<MINOR\>.\<PATCH\> standard: `3.4.3` is Cisco ISE Version 3.4.X - Patch 3 |
| **ISE Serial** | Text | **Yes** | Serial number or unique deployment ID of your Cisco ISE. | `12345ABCDE` |

---

#### Configuration → **Online Submission**

![Configuration - Online Submission Tab](img/config-online-submission.png)

Configure mTLS authentication and DISA CMRS endpoint details for direct submissions.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| **SOAP Endpoint** | Text | **Yes** | DISA CMRS SOAP gateway URL. Must be HTTPS. | `https://asdlite.disa.mil` |
| **Client Certificate File** | File Upload | **Yes** | PEM-encoded mTLS client certificate. Upload or drag-and-drop. | `client-cert.pem` |
| **Client Private Key File** | File Upload | **Yes** | PEM-encoded mTLS private key. Must match the client certificate. | `client-key.pem` |
| **Trust Bundle File** | File Upload | **Yes** | PEM-encoded CA + SOAP Identity certificate(s) for DISA server verification. Must include the full certificate chain (SOAP endpoint certificate, all intermediate CAs + Root CA). | `trust-bundle.pem` |

**Test Connection:**
1. Fill in all required Online Submission fields
2. Click **Save** - a connection test will run automatically after save completes
3. Click **Test Connection** (appears next to Save)
4. Review the output panel:
   - **[PASS]** — mTLS handshake successful, endpoint reachable
   - **[FAIL]** — See [Troubleshooting](#troubleshooting)

> **Note:** This does not submit anything to CMRS. It simply validates that the mTLS connection will successfully establish trust between this server and the CMRS endpoint.

---

#### Configuration → **Offline Submission**
> **Note:** Only enable offline submission for validation or true offline networks where manual file reporting is required.

![Configuration - Offline Submission Tab](img/config-offline-submission.png)

Configure XML file generation for testing or manual submission without direct SOAP connectivity.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| **Enable Offline Mode** | Toggle | No | When **True**, submissions are saved to XML files instead of sent to DISA. Use for testing and validation or in closed networks where online submission is not possible. | `False` |
| **Offline Report Base Name** | Text | Conditional | Output filename that will have datestamp added. Only used when Offline Mode is enabled. | `offlineReport.xml` |
| **Offline Report Backup Count** | Integer | Conditional | How many previous runs, including current, to keep in the specified directory. | `5` |
| **Output Directory** | Text | Conditional | Absolute path where offline XML files will be saved. Leave empty to use the app's `local` folder. Must be writable by the `splunk` user. | `/opt/splunk/etc/apps/submit2cmrs/local/` |

**When to use Offline Submission:**
- Testing XML generation without connecting to DISA
- Validation before enabling automated submissions
- Manual submission workflows for closed networks (generate XML, review, submit separately)

---


#### Configuration → **COAMS Configuration**

These DoD-assigned identifiers tag your compliance data in the CMRS system for proper routing and categorization. These values are assigned by DISA during your CMRS registration.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| **Reporting Owning Organization** | Text | **Yes** | DoD-assigned tag for the owning organization. | `12345` |
| **Reporting Admin Organization** | Text | **Yes** | DoD-assigned tag for the administering organization. | `12345` |
| **Reporting CNDSP** | Text | **Yes** | CNDSP (Computer Network Defense Service Provider) tag. | `12345` |
| **Reporting Area of Operations (CCSAFA)** | Text | **Yes** | CCSAFA (Cyber Common Situational Awareness for Force Application) Area of Operations tag. | `12345` |
| **Reporting Geographic AOR (COCOMAOR)** | Text | **Yes** | COCOMAOR (Combatant Command Area of Responsibility) geographic tag. | `12345` |
| **Reporting Geolocation** | Text | **Yes** | Geographical Location tag. | `12345` |
| **Reporting Operational Accreditation** | Text | **Yes** | Operational accreditation tag. | `12345` |

---

#### Configuration → **Logging**

Control the verbosity of add-on logs for debugging and monitoring.

| Setting | Type | Options | Description | Default |
|---------|------|---------|-------------|---------|
| **Log Level** | Dropdown | CRITICAL, ERROR, WARNING, INFO, DEBUG | Verbosity of logs written to `$SPLUNK_HOME/var/log/splunk/submit2cmrs.log` | `INFO` |

**Log Level Guide:**
- **CRITICAL** — Only fatal errors
- **ERROR** — Errors and failures
- **WARNING** — Warnings, errors, and recoverable issues
- **INFO** — Normal operation (recommended for production)
- **DEBUG** — Detailed troubleshooting (use when investigating issues)

---

#### Configuration → **Advanced**

![Configuration - Advanced Tab](img/config-advanced.png)

Fine-tuning options for logging, debug mode, parallel processing, and compliance rule mapping.

##### Logging & Debug

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| **Log Max Bytes** | Number | `10485760` | Maximum size in bytes for the log file before rotation (10MB = 10485760 bytes). |
| **Log Backup Count** | Number | `5` | Number of rotated log files to keep when log rotation occurs. |
| **CMRS Submission Debug** | Toggle | `False` | Enable interactive debug mode with batch inspection and retry options. Use during troubleshooting. |
| **CMRS Max Retries** | Number | `3` | Max retries for failed submissions when not in debug mode. |
| **Batches to Inspect** | Text | (empty) | Comma-separated list of batch numbers to pause on for inspection (e.g., `1,2,5`). Leave empty for no pauses. |

##### Performance

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| **Max Concurrent Processes** | Number | `8` | Number of CPU processes to use for parallel processing. Set to `0` to use all available CPU cores. |

##### Compliance Rule Mapping

These fields map your CSV column names to C2C compliance rules. **Only modify if your CSV uses different column names.** Multiple column names can be specified using comma delimiters (e.g., `ruleResultFirewall,C2CFirewallResult` matches either column).

| Setting | Type | Default |
|---------|------|---------|
| **Firewall Rule Names** | Text | `ruleResultFirewall,C2CFirewallResult` |
| **Endpoint Malware Rule Names** | Text | `ruleResultMalware,C2CMalwareResult` |
| **Endpoint Encryption Rule Names** | Text | `ruleResultEncrypt,C2CEncryptResult` |
| **Patch Agent Rule Names** | Text | `ruleResultPatch,C2CPatchResult` |
| **Endpoint Application Allowlist Rule Names** | Text | `ruleResultApps,C2CPatchResult` |
| **PKI Roots Rule Names** | Text | `ruleResultPKIRoots,C2CPKIRootsResult` |
| **Endpoint Monitor Rule Names** | Text | `ruleResultEndpointMonitor,C2CEndpointMonitorResult` |
| **Patching Rule Names** | Text | `ruleResultPatching,C2CPatchResult` |
| **Own Org Rule Names** | Text | `ruleResultOwnorg,C2COwnorgResult` |
| **Admin Org Rule Names** | Text | `ruleResultAdminorg,C2CAdminorgResult` |
| **CCSAFA Rule Names** | Text | `ruleResultCcsafa,C2CCcsafaResult` |
| **CNDSP Rule Names** | Text | `ruleResultCndsp,C2CCndspResult` |
| **COCOMAOR Rule Names** | Text | `ruleResultCocomaor,C2CCocomaorResult` |
| **Geolocation Rule Names** | Text | `ruleResultGeolocation,C2CGeolocationResult` |
| **Operational Accreditation Rule Names** | Text | `ruleResultOpAccreditation,C2COperationalaccreditationResult` |

**Comma Delimiter Note:** The system will match any column name in the comma-separated list. For example, `ruleResultFirewall,C2CFirewallResult` accepts both `ruleResultFirewall` and `C2CFirewallResult` as valid column names. This allows flexibility when integrating CSVs with varying column naming conventions.

---

## Creating and Managing Inputs

### Create a New Input

**Tab:** Inputs → **Create New Input**

![Inputs Page](img/inputs-page.png)

1. Navigate to the **Inputs** tab in the Submit2CMRS app
2. Click **Create New Input**
3. Enter the following:

   | Field | Description | Example |
   |-------|-------------|---------|
   | **Name** | Unique identifier for this submission job. Used in logs for tracking. | `CMRS_DEV` |
   | **Interval** | How often this input runs, in **seconds**. Common values: | |
   | | Daily: 86400 | |
   | | Every 6 hours: 21600 | |
   | | Every 4 hours: 14400 | |
   | | Weekly: 604800 | |
   | **Index** | Splunk index to write submission logs to. | `main` |

4. Click **Save**

### Input Validation

When you save an input, the add-on automatically validates:
- ✅ All General Settings are complete
- ✅ All Online Submission settings are complete (if Online mode enabled)
- ✅ CSV file path exists and is readable
- ✅ Certificate files are valid and readable

If validation fails, check the Configuration tab and correct any missing or invalid fields.

### Enable/Disable an Input

- **To enable:** Input Status shows as **Active** and runs on schedule
- **To disable:** Click the toggle for the input, and is shown as  **Inactive**

### Monitor Input Execution

Search for submission logs:

```spl
index=main sourcetype=submit2cmrs
```

**Sample Log Messages:**
```
action=started modular_input_name=CMRS_DEV
Starting Batch 1 of 4. Endpoint Range: 1-200. Total Completed So Far: 0.
Successfully received response from API. Status: 200
Batch 1 of 4 completed. Total Completed: 200 of 731 (27.4%). Attempt: 1.
...
Batch 4 of 4 completed. Total Completed: 731 of 731 (100.0%). Attempt: 1.
action=ended modular_input_name=CMRS_DEV
```

---

## Testing and Troubleshooting

### Test Connection

Before enabling automated inputs, always run the Test Connection validation:

1. Go to **Configuration > Online Submission**
2. Click **Test Connection**
3. Review the output:

**Test Output Examples:**

**✅ PASS:**
```
[PASS] CMRS mTLS connectivity and certificate validation checks completed successfully
```

**❌ FAIL - Trust Bundle Issue:**
```
[FAIL] unable to get local issuer certificate

Likely issue with the Trust Bundle. Please ensure all public keys from server to root are in this file.
```

**❌ FAIL - Certificate Expired:**
```
[FAIL] certificate verify failed: certificate has expired
```

**❌ FAIL - Connection Refused:**
```
[FAIL] Connection refused: Failed to connect to adslite.disa.mil:443
```

### Common Issues and Solutions

#### "unable to get local issuer certificate"

**Cause:** Trust bundle file is missing intermediate CAs or root CA required to validate the DISA server certificate.

**Solution:**
1. Verify the trust bundle contains **ALL CAs** in the chain:
   ```bash
   openssl crl2pkcs7 -nocrl -certfile /path/to/ca-bundle.pem | openssl pkcs7 -print_certs -text -noout | grep Subject
   ```
2. If certificates are split into separate files, combine them:
   ```bash
   cat intermediate-ca.pem root-ca.pem > ca-bundle.pem
   ```
3. Re-upload the trust bundle in Configuration > Online Submission
4. Test again

#### "certificate verify failed"

**Cause:** Client certificate or key is invalid, expired, or mismatched.

**Solution:**
1. Check certificate expiration:
   ```bash
   openssl x509 -in /path/to/client-cert.pem -noout -dates
   ```
2. Verify certificate is PEM format (begins with `-----BEGIN CERTIFICATE-----`)
3. Verify key is PEM format (begins with `-----BEGIN RSA PRIVATE KEY-----` or `-----BEGIN PRIVATE KEY-----`)
4. Validate certificate matches key:
   ```bash
   openssl x509 -noout -modulus -in /path/to/client-cert.pem | md5sum
   openssl rsa -noout -modulus -in /path/to/client-key.pem | md5sum
   # Both should output the same hash
   ```

#### "Connection refused" or "timeout"

**Cause:** DISA endpoint is unreachable or incorrect URL.

**Solution:**
1. Verify endpoint URL is correct (check with DISA program manager)
2. Test connectivity from the Splunk search head:
   ```bash
   curl -v --cert /path/to/client-cert.pem --key /path/to/client-key.pem --cacert /path/to/ca-bundle.pem https://cmrs-api.disa.mil/soap/submit
   ```
3. Check firewall rules allow outbound HTTPS (port 443) to DISA endpoint
4. Verify no proxy or VPN issues

#### "CSV file not found" or "Permission denied"

**Cause:** Report source CSV path doesn't exist or isn't readable by Splunk.

**Solution:**
1. Verify the path in Configuration > General exists:
   ```bash
   ls -la /opt/splunk/etc/apps/cisco-catalyst-app/lookups/cisco_catalyst_analytics_reports.csv
   ```
2. Check file permissions:
   ```bash
   ls -l /path/to/report.csv
   # Should be readable by splunk user. If not, run:
   chmod 644 /path/to/report.csv
   chown splunk:splunk /path/to/report.csv
   ```

#### Input Doesn't Run on Schedule

**Possible causes:**
1. **Input is disabled** — Check Inputs tab, verify Status is "Active"
2. **Splunk worker pool issue** — Restart Splunk:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```
3. **Configuration error** — Check Splunk logs:
   ```spl
   index=_internal group=thruput source=*submit2cmrs*
   ```

---

## Support & Documentation

- **Cisco C2C Documentation:** https://www.cisco.com/c/en/us/solutions/comply-to-connect.html
- **Cisco C2C Support Email:** [cisco_c2c_support@external.cisco.com](mailto:cisco_c2c_support@external.cisco.com)

---

## Version History

| Version | Release Date | Notes |
|---------|--------------|-------|
| 1.0.0 | Unreleased | Initial build and testing. |
| 1.0.3 | June 2026 | Initial UCC release. Replaces CLI-based submit2cmrs.py with Splunk web UI configuration. Features Test Connection button. |
| 1.0.4 | June 2026 | Updated COAMS Normalization routine and README |
| 1.0.5 | June 2026 | Access Level Normalization and Managed Device fix for Cisco Catalyst App v3.1 |

---

## License

See LICENSE file in the app directory.
