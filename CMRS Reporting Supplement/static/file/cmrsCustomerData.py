# =========================================
# File Paths and Submission Mode
# =========================================
# c2cReportPath needs to be the full path to the reporting tool output file
# This is by default /opt/splunk/etc/apps/cisco-catalyst-app/lookups/cisco_catalyst_analytics_reports.csv
# For Linux Installations use
c2cReportPath = "/opt/splunk/etc/apps/cisco-catalyst-app/lookups/cisco_catalyst_analytics_reports.csv"
# For Windows Installations use
# c2cReportPath = "C:\Program Files\Splunk\etc\apps\cisco-catalyst-app\lookups\cisco_catalyst_analytics_reports.csv"

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
soapEndpoint = "https://example.com/soap/submit"    # DISA CMRS SOAP Endpoint
certFile = "client.crt"             # Path to your client certificate (PEM)
keyFile = "client.key"              # Path to your private key (PEM)
caBundle = "ca_bundle.crt"          # CA certificate to verify the server
soapAction = "SubmitRecords"        # This should not be modified

# =========================================
# Operational Parameters
# =========================================
# This is the number of endpoints that will be reported in each batch post to the CMRS API
# The theoretical maximum is ~250 endpoints, suggested batch size is 200
reportingBatchSize = 200

# This value is the delta of how often you expect a scan of each endpoint via ACAS
# If policy dictates 1 scan everyweek then leave at 7
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
c2cPkiRootsRule = ""
c2cEndpointMonitorRule = ""
c2cPatchingRule = "C2CPatchResult"
