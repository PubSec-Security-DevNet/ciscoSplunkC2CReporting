# =========================================
# Data Source Configuration (CSV File)
# =========================================
# c2cReportPath needs to be the full path to the reporting tool output file
# This is by default /opt/splunk/etc/apps/cisco-catalyst-app/lookups/cisco_catalyst_analytics_reports.csv
# For Linux Installations use
c2cReportPath = "/opt/splunk/etc/apps/cisco-catalyst-app/lookups/cisco_catalyst_analytics_reports.csv"
# For Windows Installations use
# c2cReportPath = "C:\\Program Files\\Splunk\\etc\\apps\\cisco-catalyst-app\\lookups\\cisco_catalyst_analytics_reports.csv"

# =========================================
# Submission Mode
# =========================================
# For manual submission to CMRS set offlineUpload to True and define a name for the XML
offlineUpload = False
offlineReport = "./offlineCMRSReport.xml"

# =========================================
# Publisher and Organizational Metadata
# =========================================
# The following should be your publisher identifying information
publisherName = "test.ciscosecuritylab.com"
publisherVersion = "3.0.0"
iseVersion = "3.4.3"
iseSerial = "12345ABCDE"
reportingOwnOrg = "12345"
reportingAdminOrg = "12345"
reportingCndsp = "12345"
reportingCcsafa = "12345"
reportingCocomaor = "12345"
reportingGeolocation = "12345"

# =========================================
# API Connectivity and Security 
# =========================================
# Update the following to match the Endpoint and certificate data provided during your registration with CMRS
soapEndpoint = "https://adslite.dev.cmrs.com"    # DISA CMRS SOAP Endpoint
certFile = "client.crt"             # Path to your client certificate (PEM)
keyFile = "client.key"              # Path to your private key (PEM)
pkiTrust = "cmrsProvidedTrust.crt"  # Trusted CMRS certificate to verify the server. This should be a single file with the full chain (PEM encoded) of trust including the ADSLITE endpoint certificate.
# Max retries for failed submissions when not in debug mode
cmrs_max_retries = 3

# =========================================
# Operational Parameters
# =========================================
# This is the number of endpoints that will be reported in each batch post to the CMRS API
# The theoretical maximum is ~250 endpoints, suggested batch size is 200
reportingBatchSize = 100

# This value is the delta of how often you expect a scan of each endpoint via ACAS
# If policy dictates 1 scan every week then leave at 7
acasDelta = 7

# =========================================
# Compliance Rule Mapping
# =========================================
# These are the extraction names in the reporting app search macros. 
# If the extraction names are unchanged then do not modify
c2cFirewallRule = "C2CFirewallResult"
c2cEndpointMalwareRule = "C2CMalwareResult"
c2cEndpointEncryptRule = "C2CEncryptResult"
c2cPatchAgentRule = "C2CPatchResult"
c2cEndpointAppWlRule = "C2CPatchResult"
c2cPkiRootsRule = "C2CPKIRootsResult"
c2cEndpointMonitorRule = "C2CEndpointMonitorResult"
c2cPatchingRule = "C2CPatchResult"
c2cOwnorgRule = "C2COwnorgResult"
c2cAdminorgRule = "C2CAdminorgResult"
c2cCcsafaRule = "C2CCcsafaResult"
c2cCndspRule = "C2CCndspResult"
c2cCocomaorRule = "C2CCocomaorResult"
c2cGeolocationRule = "C2CGeolocationResult"
c2cOperationalaccreditationRule = "C2COperationalaccreditationResult"

# =========================================
# ADVANCED & TROUBLESHOOTING CONFIGURATION 
# =========================================

# =========================================
# Multiprocess configuration - Adjust for number of CPU processes to use for parallel processing
# Set to None to use all available CPU cores
# =========================================
maxConcurrentProcesses = 8

# =========================================
# Debug and Submission Configuration
# =========================================
# Set to True for interactive debug mode with batch inspection and retry options
cmrs_submission_debug = False

# List of batch numbers to pause on for inspection (empty list = no pauses)
# Example: batches_to_inspect = [1, 2, 5] will pause after batches 1, 2, and 5
batches_to_inspect = [1]

