"""
Script Name: submit2Cmrs.py
Description: Reporting automation to submit C2C reporting requirements to CMRS from the Cisco C2C Reporting App 3.0
Author: Chad Mitchell, chadmi@cisco.com
Version: 1.4
Contributors: Brent Matlock (Cisco), Thomas Barbour (GDIT)
"""

import logging
import csv
import re
import requests
import time
from jinja2 import Template
from datetime import datetime, timedelta
from cmrsCustomerData import *
import multiprocessing

# --- Logger setup ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s log_level=%(levelname)s pid=%(process)s tid=%(threadName)s file=%(filename)s:%(funcName)s:%(lineno)s | %(message)s')
handler = logging.FileHandler('submit2Cmrs.log', 'a')
handler.setFormatter(formatter)
logger.addHandler(handler)

# --- submit2Cmrs function (Added error handling) ---
def submit2Cmrs(xmlEnvelope: str) -> requests.Response:
    """
    Submits the XML envelope to the CMRS SOAP endpoint and validates the response.
    Returns the response object on success, or raises an exception on failure.
    """
    try:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "Notify"
        }
        response = requests.post(
            soapEndpoint,
            data=xmlEnvelope.encode("utf-8"),
            headers=headers,
            cert=(certFile, keyFile),
            verify=pkiTrust,
            timeout=60
        )

        # if the HTTP request returns an unsuccessful status code (4xx or 5xx).
        response.raise_for_status()

        # If the status code was successful (200-299)
        logger.info(f"Successfully received response from API. Status: {response.status_code}")
        return response

    except requests.exceptions.HTTPError as e:
        # This catches errors like 400 Bad Request, 401 Unauthorized, 500 Server Error
        print(f"  - Submission FAILED. The server responded with an error.")
        logger.error(f"HTTP Error: {e.response.status_code} {e.response.reason}")
        # If the response contains a SOAP Fault with a detailed error message.
        logger.error(f"Server Response Body: {e.response.text}")
        # Re-raise the exception to stop the main script execution.
        raise

    except requests.exceptions.RequestException as e:
        # This catches network-level errors
        print(f"  - Submission FAILED. A network or connection error occurred.")
        logger.error(f"Connection Error: {e.response.status_code}")
        # Re-raise the exception to stop the main script execution.
        raise


# --- createReportEnvelope function ---
def createReportEnvelope(deviceBatch):
    sensorType = "Cisco ISE"
    reportingTimestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    benchmarkName = "C2C_Data"
    benchmarkVersion = "6.1.0.1"
    publisherMessageId = publisherName + ":" + sensorType.lower().replace(" ", "_") + ":" + reportingTimestamp
    
    reportData = {
        "sensorType": sensorType,
        "reportingTimestamp": reportingTimestamp,
        "benchmarkName": benchmarkName,
        "benchmarkVersion": benchmarkVersion,
        "publisherMessageId": publisherMessageId,
        "publisherName": publisherName,
        "publisherVersion": publisherVersion,
        "iseVersion": iseVersion,
        "iseSerial": iseSerial,
        "reportingOwnOrg": reportingOwnOrg,
        "reportingAdminOrg": reportingAdminOrg,
        "reportingCndsp": reportingCndsp,
        "reportingCcsafa": reportingCcsafa,
        "reportingCocomaor": reportingCocomaor,
        "reportingGeolocation": reportingGeolocation,
        "deviceBatch": deviceBatch
    }
    
    headerFooterTemplate = '''
<S:Envelope xmlns:S="http://schemas.xmlsoap.org/soap/envelope/">
  <S:Body>
    <wsnt:Notify xmlns:xsi="https://www.w3.org/2001/XMLSchema-instance" xmlns:wsnt="http://docs.oasis-open.org/wsn/b-2" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:tagged_value="http://metadata.dod.mil/mdr/ns/netops/shared_data/tagged_value/0.41">
      <wsnt:NotificationMessage>
        <wsnt:Topic Dialect="http://docs.oasis-open.org/wsn/t-1/TopicExpression/Simple">cisco_ise.benchmark#C2C_Data#.arf.results</wsnt:Topic>
        <wsnt:ProducerReference>
          <wsa:Address>{{ publisherName }}</wsa:Address>
          <wsa:Metadata>
            <wsa:MessageID>{{ publisherMessageId}}</wsa:MessageID>
            <tagged_value:taggedString name="Sensor Type" value="{{ sensorType }}" /> 
            <tagged_value:taggedString name="Cisco ISE Version" value="{{ iseVersion }}" /> 
            <tagged_value:taggedString name="Cisco ISE ID" value="{{ iseSerial }}" /> 
            <tagged_value:taggedString name="Cisco ISE Reporting App Version" value="{{ publisherVersion }}" /> 
            <tagged_value:taggedString name="ownorg.dod.mil" value="{{ reportingOwnOrg }}" />
            <tagged_value:taggedString name="adminorg.dod.mil" value="{{ reportingAdminOrg }}" />
            <tagged_value:taggedString name="cndsp.dod.mil" value="{{ reportingCndsp }}" />
            <tagged_value:taggedString name="ccsafa.dod.mil" value="{{ reportingCcsafa }}" />
            <tagged_value:taggedString name="cocomaor.dod.mil" value="{{ reportingCocomaor }}" />
            <tagged_value:taggedString name="geolocation.dod.mil" value="{{ reportingGeolocation }}" />
            <tagged_value:taggedString name="cisco ise Deployment ID" value="{{ iseSerial }}" />
            <tagged_value:taggedString name="Benchmark Name" value="{{ benchmarkName }}" />
            <tagged_value:taggedString name="Benchmark Version" value="{{ benchmarkVersion }}" />
            <tagged_value:taggedString name="Report Time" value="{{ reportingTimestamp }}" />
          </wsa:Metadata>
        </wsnt:ProducerReference>
        <wsnt:Message>
          <ar:AssessmentReport xmlns:ar="http://metadata.dod.mil/mdr/ns/netops/shared_data/assessment_report/0.41" xmlns:device="http://metadata.dod.mil/mdr/ns/netops/shared_data/device/0.41" xmlns:cpe="http://scap.nist.gov/schema/cpe-record/0.1" xmlns:tagged_value="http://metadata.dod.mil/mdr/ns/netops/shared_data/tagged_value/0.41" xmlns:cndc="http://metadata.dod.mil/mdr/ns/netops/net_defense/cnd-core/0.41">
        {{ deviceBatch }}
          </ar:AssessmentReport>
        </wsnt:Message>
      </wsnt:NotificationMessage>
    </wsnt:Notify>
  </S:Body>
</S:Envelope>'''

    jinjaTemplate = Template(headerFooterTemplate)
    try:
        xmlOutput = jinjaTemplate.render(reportData)
        return xmlOutput
    except Exception as e:
        print(f"An error occurred during envelope creation: {e}")
        logger.error(f"An error occurred during envelope creation: {e}")
        return None

# --- Datetime format detection and conversion ---
def convert_to_iso8601(dt_string):
    """
    Detect and convert various datetime formats to ISO 8601.
    Tries multiple common formats. Returns ISO 8601 string or original value if no format matches.
    """
    if not dt_string or dt_string in ["N/A", "None", ""]:
        return dt_string

    # List of datetime formats to try
    dt_formats = [
        "%a %b %d %H:%M:%S %Z %Y",           # ctime format (e.g., "Mon Apr 28 10:30:45 UTC 2026")
        "%Y-%m-%dT%H:%M:%S%z",               # ISO 8601 with timezone
        "%Y-%m-%dT%H:%M:%S.%f%z",            # ISO 8601 with microseconds and timezone
        "%Y-%m-%dT%H:%M:%S",                 # ISO 8601 without timezone
        "%m/%d/%y %H:%M:%S",                 # US short date format
        "%Y-%m-%d %H:%M:%S",                 # ISO date with time
        "%Y-%m-%d",                          # ISO date only
    ]

    for fmt in dt_formats:
        try:
            dt_obj = datetime.strptime(dt_string, fmt)
            return dt_obj.isoformat()
        except (ValueError, TypeError):
            continue

    # If no format matched, return original value
    return dt_string

# --- Combined Assessment and Normalization ---
def normalize_values(device_record):
    """
    Combined function that assesses CMRS compliance results first, then normalizes all values to XCCDF enumeration values.
    
    Assessment Logic (applied first to rule mapping):
    1. If result_value has content → normalize and return it
    2. If result_value empty, check if either CSV or KV store tag is populated → return "pass"
    3. If tags empty but PostureStatus has value → return "fail"
    4. Otherwise → return "" (empty/null)
    
    Normalization Logic (applied after assessment):
    - PostureStatus: "Compliant"/"GraceCompliant" → "pass", "NonCompliant" → "fail"
    - Compliance result values: "Passed" → "pass", "Failed" → "fail"
    - cybercomCategory: normalize recognized CYBERCOM category variants to canonical display values
    """
    
    # Get PostureStatus for assessment logic
    posture_status = device_record.get("PostureStatus", "")
    
    # Step 1: ASSESS - Apply assessment logic to compliance rules with CSV tags
    rule_mapping = {
        "c2cOwnorgRule": "ownorg_dod_mil",
        "c2cAdminorgRule": "adminorg_dod_mil",
        "c2cCcsafaRule": "ccsafa_dod_mil",
        "c2cCndspRule": "cndsp_dod_mil",
        "c2cCocomaorRule": "cocomaor_dod_mil",
        "c2cGeolocationRule": "geolocation_dod_mil",
        "c2cOperationalaccreditationRule": "operationalaccreditation_dod_mil"
    }

    for rule_var, csv_tag in rule_mapping.items():
        result_value = device_record.get(rule_var, "")
        csv_value = device_record.get(csv_tag, "")
        
        # Apply assessment logic
        if result_value:
            result_value = result_value.strip()
            if result_value == "Passed":
                device_record[rule_var] = "pass"
            elif result_value == "Failed":
                device_record[rule_var] = "fail"
            elif result_value:
                device_record[rule_var] = result_value
        else:
            # Check if CSV COAMS tag is populated
            csv_populated = bool(csv_value and csv_value.strip())

            if csv_populated:
                device_record[rule_var] = "pass"
            elif posture_status and posture_status.strip():
                device_record[rule_var] = "fail"
            else:
                device_record[rule_var] = ""
    
    # Step 2: NORMALIZE - Apply normalization to all compliance values
    
    # Normalize PostureStatus
    posture_status = device_record.get("PostureStatus", "").strip()
    if posture_status in ["Compliant", "GraceCompliant"]:
        device_record["PostureStatus"] = "pass"
    elif posture_status == "NonCompliant":
        device_record["PostureStatus"] = "fail"

    # Normalize c2c*Rule values
    c2c_rule_keys = [
        "c2cFirewallRule", "c2cEndpointMalwareRule", "c2cEndpointEncryptRule",
        "c2cPatchAgentRule", "c2cEndpointAppWlRule", "c2cPkiRootsRule",
        "c2cEndpointMonitorRule", "c2cPatchingRule", "C2COwnorgResult",
        "C2CAdminorgResult", "C2CCcsafaResult", "C2CCndspResult",
        "C2CCocomaorResult", "C2CGeolocationResult", "C2COperationalaccreditationResult"
    ]

    for key in c2c_rule_keys:
        value = device_record.get(key, "").strip()
        if value == "Passed":
            device_record[key] = "pass"
        elif value == "Failed":
            device_record[key] = "fail"

    # Normalize storage size fields from G/Gb/GB/Gig to MB-like numeric value (x1024)
    storage_fields = ["SysvolTotalSpace", "BootPartitionFreeSpace", "BootPartitionTotalSpace"]
    storage_pattern = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*(g|gb|gig)\s*$", re.IGNORECASE)
    for field in storage_fields:
        raw_value = (device_record.get(field, "") or "").strip()
        if not raw_value:
            continue
        match = storage_pattern.match(raw_value)
        if match:
            converted = float(match.group(1)) * 1024
            device_record[field] = str(int(converted)) if converted.is_integer() else ("{0:.6f}".format(converted).rstrip("0").rstrip("."))

    # Normalize cybercomCategory to canonical CMRS values when recognized
    cybercom_category = device_record.get("cybercomCategory", "")
    if cybercom_category:
        category_key = cybercom_category.strip()
        category_key = re.sub(r"[^a-z0-9]+", " ", category_key.lower()).strip()

        cybercom_category_matches = [
            ("cyber physical systems", "Cyber Physical Systems/Control Systems (CPS/CS)"),
            ("networked user support", "Networked User Support Devices"),
            ("network infrastructure", "Network Infrastructure"),
            ("workstations and servers", "Workstations and Servers"),
            ("internet of things", "Internet of Things (IoT)"),
            ("mobile devices", "Mobile Devices"),
        ]

        for match_text, canonical_value in cybercom_category_matches:
            if match_text in category_key:
                device_record["cybercomCategory"] = canonical_value
                break

# Worker function for multiprocess
# This function processes a single row and returns the generated XML object.
def process_row(row):

    deviceTemplate = '''
          <ar:reportObject>
            <ar:device {% if iseLastSeen %}timestamp="{{ iseLastSeen }}"{% endif %}>
              <device:device_ID>
                {% if publisherName %}<cndc:resource>{{ publisherName }}</cndc:resource>{% endif %}
                {% if recordId %}<cndc:record_identifier>{{ recordId }}</cndc:record_identifier>{% endif %}
              </device:device_ID>
              <device:operational_attributes>
                {% if publisherName %}<cndc:resource>{{ publisherName }}</cndc:resource>{% endif %}
                {% if recordId %}<cndc:record_identifier>{{ recordId }}</cndc:record_identifier>{% endif %}
              </device:operational_attributes>
              <device:identifiers>
                <device:FQDN>
                  {% if dnsName %}<device:host_name>{{ dnsName }}</device:host_name>{% endif %}
                  {% if AD_User_DNS_Domain %}<device:realm>SIE.LOCATION.{{ AD_User_DNS_Domain }}</device:realm>{% endif %}
                </device:FQDN>
              </device:identifiers>
              <device:configuration>
                <device:network_configuration>
                  {% if NAS_Port_Id %}<device:network_interface_ID>{{ NAS_Port_Id }}</device:network_interface_ID>{% endif %}
                  <device:host_network_data>
                    {% if macAddress %}<device:connection_mac_address>{{ macAddress }}</device:connection_mac_address>{% endif %}
                    {% if Ipv4Address %}<device:connection_ip>
                      <cndc:IPv4>{{ Ipv4Address }}</cndc:IPv4>
                    </device:connection_ip>{% endif %}
                    {% if Ipv6Address %}<device:connection_ip>
                      <cndc:IPv6>{{ Ipv6Address }}</cndc:IPv6>
                    </device:connection_ip>{% endif %}
                  </device:host_network_data>
                </device:network_configuration>
                <device:cpe_inventory>
                  <device:cpe_record>
                    {% if osPlatformName %}<cpe:platformName>
                      <cpe:assessedName name="{{ osPlatformName }}"/>
                    </cpe:platformName>{% endif %}
                    {% if osVendor %}<tagged_value:taggedString name="OSVendor" value="{{ osVendor }}"/>{% endif %}
                    {% if osCompositeName %}<tagged_value:taggedString name="OSName" value="{{ osCompositeName }}"/>{% endif %}
                    {% if osVersion %}<tagged_value:taggedString name="OSVersion" value="{{ osVersion }}"/>{% endif %}
                    {% if osEdition %}<tagged_value:taggedString name="OSEdition" value="{{ osEdition }}"/>{% endif %}
                    {% if osMktVersion %}<tagged_value:taggedString name="OSMktVersion" value="{{ osMktVersion }}"/>{% endif %}
                    {% if osArch %}<tagged_value:taggedString name="OSArch" value="{{ osArch }}"/>{% endif %}
                    {% if osCompositeName %}<tagged_value:taggedString name="OSCompositeName" value="{{ osCompositeName }}"/>{% endif %}
                  </device:cpe_record>
                </device:cpe_inventory>
              </device:configuration>

              {% if iseVersion %}<tagged_value:taggedString name="Sensor version" value="{{ iseVersion }}"/>{% endif %}
              {% if iseSerial %}<tagged_value:taggedString name="Sensor ID" value="{{ iseSerial }}"/>{% endif %}
              {% if publisherVersion %}<tagged_value:taggedString name="Sensor Publisher Version" value="Cisco ISE Reporting App Version {{ publisherVersion }}"/>{% endif %}

              {# COAMS Tags using Version 3.1.0 CSV Reporting Template #}
              {% if ccsafa_dod_mil %}<tagged_value:taggedString name="ccsafa.dod.mil" value="{{ ccsafa_dod_mil }}"/>{% endif %}
              {% if geolocation_dod_mil %}<tagged_value:taggedString name="geolocation.dod.mil" value="{{ geolocation_dod_mil }}"/>{% endif %}
              {% if ownorg_dod_mil %}<tagged_value:taggedString name="ownorg.dod.mil" value="{{ ownorg_dod_mil }}"/>{% endif %}
              {% if cndsp_dod_mil %}<tagged_value:taggedString name="cndsp.dod.mil" value="{{ cndsp_dod_mil }}"/>{% endif %}
              {% if adminorg_dod_mil %}<tagged_value:taggedString name="adminorg.dod.mil" value="{{ adminorg_dod_mil }}"/>{% endif %}
              {% if cocomaor_dod_mil %}<tagged_value:taggedString name="cocomaor.dod.mil" value="{{ cocomaor_dod_mil }}"/>{% endif %}
              {% if operationalaccreditation_dod_mil %}<tagged_value:taggedString name="operationalaccreditation.dod.mil" value="{{ operationalaccreditation_dod_mil }}"/>{% endif %}

              {% if Location %}<tagged_value:taggedString name="SwLocation" value="{{ Location }}"/>{% endif %}
              {% if NetworkDeviceName %}<tagged_value:taggedString name="SwHostname" value="{{ NetworkDeviceName }}"/>{% endif %}
              {% if NAS_Port_Id %}<tagged_value:taggedString name="SwPortDescription" value="{{ NAS_Port_Id }}"/>{% endif %}
              {% if SwPortAlias %}<tagged_value:taggedString name="SwPortAlias" value="{{ SwPortAlias }}"/>{% endif %}
              {% if SegmentPath %}<tagged_value:taggedString name="SegmentPath" value="{{ SegmentPath }}"/>{% endif %}
              {% if DeviceRole %}<tagged_value:taggedString name="DeviceRole" value="{{ DeviceRole }}"/>{% endif %}
              {% if SystemManufacturer %}<tagged_value:taggedString name="VendorClassificationInfo" value="{{ SystemManufacturer }}"/>{% endif %}
              {% if NetworkFunction %}<tagged_value:taggedString name="NetworkFunction" value="{{ NetworkFunction }}"/>{% endif %}
              {% if SystemManufacturer %}<tagged_value:taggedString name="ManufacturerClassification" value="{{ SystemManufacturer }}"/>{% endif %}
              {% if GuestCorporateState %}<tagged_value:taggedString name="GuestCorporateState" value="{{ GuestCorporateState }}"/>{% endif %}
              {% if ClassificationType %}<tagged_value:taggedString name="ClassificationType" value="{{ ClassificationType }}"/>{% endif %}
              {% if NICVendor %}<tagged_value:taggedString name="NICVendor" value="{{ NICVendor }}"/>{% endif %}
              {% if UserName %}<tagged_value:taggedString name="username" value="{{ UserName }}"/>{% endif %}
              {% if BIOSGUID %}<tagged_value:taggedString name="BIOSGUID" value="{{ BIOSGUID }}"/>{% endif %}
              {% if BiosVendor %}<tagged_value:taggedString name="BiosVendor" value="{{ BiosVendor }}"/>{% endif %}
              {% if BiosSerialNumber %}<tagged_value:taggedString name="BiosSerialNumber" value="{{ BiosSerialNumber }}"/>{% endif %}
              {% if BiosVersion %}<tagged_value:taggedString name="BiosVersion" value="{{ BiosVersion }}"/>{% endif %}
              {% if BootPartitionTotalSpace %}<tagged_value:taggedString name="BootPartitionTotalSpace" value="{{ BootPartitionTotalSpace }}"/>{% endif %}
              {% if TPMVersion %}<tagged_value:taggedString name="TPMVersion" value="{{ TPMVersion }}"/>{% endif %}
              {% if SysvolDescription %}<tagged_value:taggedString name="SysvolDescription" value="{{ SysvolDescription }}"/>{% endif %}
              {% if SysvolFileSystem %}<tagged_value:taggedString name="SysvolFileSystem" value="{{ SysvolFileSystem }}"/>{% endif %}
              {% if SysvolFreeSpace %}<tagged_value:taggedString name="SysvolFreeSpace" value="{{ SysvolFreeSpace }}"/>{% endif %}
              {% if SysvolName %}<tagged_value:taggedString name="SysvolName" value="{{ SysvolName }}"/>{% endif %}
              {% if SysvolTotalSpace %}<tagged_value:taggedString name="SysvolTotalSpace" value="{{ SysvolTotalSpace }}"/>{% endif %}
              {% if BootPartitionFreeSpace %}<tagged_value:taggedString name="FreeDiskSpace" value="{{ BootPartitionFreeSpace }}"/>{% endif %}
              {% if BootPartitionTotalSpace %}<tagged_value:taggedString name="TotalDiskSpace" value="{{ BootPartitionTotalSpace }}"/>{% endif %}
              {% if NumCpuCores %}<tagged_value:taggedString name="NumOfCPU" value="{{ NumCpuCores }}"/>{% endif %}
              {% if SystemManufacturer %}<tagged_value:taggedString name="SystemManufacturer" value="{{ SystemManufacturer }}"/>{% endif %}
              {% if SystemModel %}<tagged_value:taggedString name="SystemModel" value="{{ SystemModel }}"/>{% endif %}
              {% if NumInstalledCPU %}<tagged_value:taggedString name="NumInstalledCPU" value="{{ NumInstalledCPU }}"/>{% endif %}
              {% if TotalPhysicalMemory %}<tagged_value:taggedString name="TotalPhysicalMemory" value="{{ TotalPhysicalMemory }}"/>{% endif %}
              {% if BiosVendor %}<tagged_value:taggedString name="MotherBoard Manufacturer" value="{{ BiosVendor }}"/>{% endif %}
              {% if BiosSerialNumber %}<tagged_value:taggedString name="MotherBoard Serial Number" value="{{ BiosSerialNumber }}"/>{% endif %}
              {% if BiosVersion %}<tagged_value:taggedString name="MotherBoard Version" value="{{ BiosVersion }}"/>{% endif %}
              {% if CpuVersion %}<tagged_value:taggedString name="CPUManufacturer" value="{{ CpuVersion }}"/>{% endif %}
              {% if CPUSpeed %}<tagged_value:taggedString name="CPUSpeed" value="{{ CPUSpeed }}"/>{% endif %}
              {% if NumCpuCores %}<tagged_value:taggedString name="CPUCoreCount" value="{{ NumCpuCores }}"/>{% endif %}
              {% if cybercomCategory %}<tagged_value:taggedString name="CyberComCategory" value="{{ cybercomCategory }}"/>{% endif %}
              {% if c2cManaged %}<tagged_value:taggedString name="C2C Managed" value="{{ c2cManaged }}"/>{% endif %}
              
              {# Step 2-3 Compliance Rule Tags #}
              {% if PostureStatus %}<tagged_value:taggedString name="rule C2C OverallComplianceStatus" value="{{ PostureStatus }}"/>{% endif %}
              {% if c2cFirewallRule %}<tagged_value:taggedString name="rule C2C EndpointFirewall" value="{{ c2cFirewallRule }}"/>{% endif %}
              {% if c2cEndpointMalwareRule %}<tagged_value:taggedString name="rule C2C EndpointAntiMalware" value="{{ c2cEndpointMalwareRule }}"/>{% endif %}
              {% if c2cEndpointEncryptRule %}<tagged_value:taggedString name="rule C2C EndpointDAREncryption" value="{{ c2cEndpointEncryptRule }}"/>{% endif %}
              {% if c2cPatchAgentRule %}<tagged_value:taggedString name="rule C2C PatchAgent" value="{{ c2cPatchAgentRule }}"/>{% endif %}
              {% if VulnScanCurrent %}<tagged_value:taggedString name="rule C2C VulnScanCurrent" value="{{ VulnScanCurrent }}"/>{% endif %}
              {% if c2cEndpointAppWlRule %}<tagged_value:taggedString name="rule C2C EndpointAppWhitelisting" value="{{ c2cEndpointAppWlRule }}"/>{% endif %}
              {% if c2cPkiRootsRule %}<tagged_value:taggedString name="rule C2C PKITrustRoots" value="{{ c2cPkiRootsRule }}"/>{% endif %}
              {% if c2cEndpointMonitorRule %}<tagged_value:taggedString name="rule C2C EndpointMonitoring" value="{{ c2cEndpointMonitorRule }}" />{% endif %}
              {% if c2cPatchingRule %}<tagged_value:taggedString name="rule C2C Patching" value="{{ c2cPatchingRule }}" />{% endif %}
              {% if c2cOwnorgRule %}<tagged_value:taggedString name="rule C2C ownorg.dod.mil" value="{{ c2cOwnorgRule }}"/>{% endif %}
              {% if c2cAdminorgRule %}<tagged_value:taggedString name="rule C2C adminorg.dod.mil" value="{{ c2cAdminorgRule }}"/>{% endif %}
              {% if c2cCcsafaRule %}<tagged_value:taggedString name="rule C2C ccsafa.dod.mil" value="{{ c2cCcsafaRule }}"/>{% endif %}
              {% if c2cCndspRule %}<tagged_value:taggedString name="rule C2C cndsp.dod.mil" value="{{ c2cCndspRule }}"/>{% endif %}
              {% if c2cCocomaorRule %}<tagged_value:taggedString name="rule C2C cocomaor.dod.mil" value="{{ c2cCocomaorRule }}"/>{% endif %}
              {% if c2cGeolocationRule %}<tagged_value:taggedString name="rule C2C geolocation.dod.mil" value="{{ c2cGeolocationRule }}"/>{% endif %}
              {% if c2cOperationalaccreditationRule %}<tagged_value:taggedString name="rule C2C operationalaccreditation.dod.mil" value="{{ c2cOperationalaccreditationRule }}"/>{% endif %}
              
              {# Step 4 Tags using Version 3.1.0 CSV Reporting Template #}
              {% if C2C_Auth_Result %}<tagged_value:taggedString name="C2C Auth Result" value="{{ C2C_Auth_Result }}" />{% endif %}
              {% if C2C_Authorization_Source %}<tagged_value:taggedString name="C2C Authorization Source" value="{{ C2C_Authorization_Source }}" />{% endif %}
              {% if C2C_Connection %}<tagged_value:taggedString name="C2C Connection" value="{{ C2C_Connection }}" />{% endif %}
              {% if C2C_Device_Token %}<tagged_value:taggedString name="C2C Device Token" value="{{ C2C_Device_Token }}" />{% endif %}
              {% if C2C_Last_Auth %}<tagged_value:taggedString name="C2C Last Auth" value="{{ C2C_Last_Auth }}" />{% endif %}
              {% if C2C_Last_Auth_Access_Assignment %}<tagged_value:taggedString name="C2C Last Auth Access Assignment" value="{{ C2C_Last_Auth_Access_Assignment }}" />{% endif %}
              {% if C2C_Primary_Auth %}<tagged_value:taggedString name="C2C Primary Auth" value="{{ C2C_Primary_Auth }}" />{% endif %}
              {% if C2C_Secondary_Auth %}<tagged_value:taggedString name="C2C Secondary Auth" value="{{ C2C_Secondary_Auth }}" />{% endif %}
              {% if ICAM_Device %}<tagged_value:taggedString name="C2C ICAM Last Auth Device" value="{{ ICAM_Device }}"/>{% endif %}
              {% if ICAM_Device_CA %}<tagged_value:taggedString name="C2C ICAM Last Auth Device CA" value="{{ ICAM_Device_CA }}"/>{% endif %}
              {% if ICAM_Device_Sub_CA %}<tagged_value:taggedString name="C2C ICAM Last Auth Device Root CA" value="{{ ICAM_Device_Sub_CA }}"/>{% endif %}
              {% if ICAM_User %}<tagged_value:taggedString name="C2C ICAM Last Auth Device" value="{{ ICAM_User }}"/>{% endif %}
              {% if ICAM_User_CA %}<tagged_value:taggedString name="C2C ICAM Last Auth Device CA" value="{{ ICAM_User_CA }}"/>{% endif %}
              {% if ICAM_User_Sub_CA %}<tagged_value:taggedString name="C2C ICAM Last Auth Device Root CA" value="{{ ICAM_User_Sub_CA }}"/>{% endif %}
              {% if Wired_Connections %}<tagged_value:taggedString name="C2C Wired Connections" value="{{ Wired_Connections }}" />{% endif %}
              {% if Wireless_Connections %}<tagged_value:taggedString name="C2C Wireless Connections" value="{{ Wireless_Connections }}" />{% endif %}
              {% if Total_Full_Access %}<tagged_value:taggedString name="C2C Access Level Unknown" value="{{ Total_Full_Access }}" />{% endif %}
              {% if Total_Remediation %}<tagged_value:taggedString name="C2C Access Level Remediation" value="{{ Total_Remediation }}" />{% endif %}
              {% if Total_Unknown %}<tagged_value:taggedString name="C2C Access Level Full Access" value="{{ Total_Unknown }}" />{% endif %}
            </ar:device>
          </ar:reportObject>
    '''
    # Set VulnScanCurrent
    def dateDelta(dtInput: str):
        """
        Check if acasSeen date is within the expected delta.
        Uses convert_to_iso8601 to detect and parse date formats.
        Returns: "pass" if valid and within delta, "fail" if valid but outside delta, "" if invalid format
        """
        if not dtInput:
            return ""

        # Try to convert to ISO8601 - if it works, the date format was recognized
        iso_date = convert_to_iso8601(dtInput)
        if iso_date == dtInput:
            # Date format was not recognized
            return ""

        try:
            # Parse the ISO date to check delta
            dt_input = datetime.fromisoformat(iso_date)
            is_current = (datetime.now() - dt_input.replace(tzinfo=None)) <= timedelta(days=acasDelta)
            return "pass" if is_current else "fail"
        except (ValueError, TypeError):
            return ""

    # Clean and transform the record
    deviceRecord = {
        key.replace(".", "_").replace(" ", "_"): (
            value.replace('\n', ' ').split('</', 1)[0]
            if isinstance(value, str) and value != 'N/A' and value != 'None'
            else ""
        )
        for key, value in row.items()
    }

    # Set VulnScanCurrent based on acasSeen date
    deviceRecord["VulnScanCurrent"] = dateDelta(deviceRecord.get('acasSeen'))

    # Set iseLastSeen to ISO8601 Format
    deviceRecord["iseLastSeen"] = convert_to_iso8601(deviceRecord.get("iseLastSeen", ""))

    # Set recordId with Coalesce
    deviceRecord["recordId"] = deviceRecord.get('uuid') or deviceRecord.get('BIOSGUID') or deviceRecord.get('record_id') or deviceRecord.get('macAddress')

    # Extract CPU Speed
    cpu_version = deviceRecord.get("CpuVersion", "")
    cpuMatch = re.search(r"(\d+\.\d+GHz)", cpu_version)
    deviceRecord["CPUSpeed"] = cpuMatch.group(1) if cpuMatch else ""

    # Set CMRS Posture Rules
    c2cRules = {
        "c2cFirewallRule": c2cFirewallRule, "c2cEndpointMalwareRule": c2cEndpointMalwareRule,
        "c2cEndpointEncryptRule": c2cEndpointEncryptRule, "c2cPatchAgentRule": c2cPatchAgentRule,
        "c2cEndpointAppWlRule": c2cEndpointAppWlRule, "c2cPkiRootsRule": c2cPkiRootsRule,
        "c2cEndpointMonitorRule": c2cEndpointMonitorRule, "c2cPatchingRule": c2cPatchingRule
    }
    for key, value_key in c2cRules.items():
        deviceRecord[key] = deviceRecord.get(value_key, "")

    # Assess and normalize compliance values (assessment first, then normalization)
    normalize_values(deviceRecord)

    # Add Publisher Details
    deviceRecord["iseVersion"] = iseVersion
    deviceRecord["iseSerial"] = iseSerial
    deviceRecord["publisherName"] = publisherName
    deviceRecord["publisherVersion"] = publisherVersion

    deviceRecord["c2cManaged"] = (
        "Managed"
        if deviceRecord.get("cybercomCategory") == "Workstations and Servers" and (deviceRecord.get("PostureStatus") or "").strip()
        else "Manageable"
        if deviceRecord.get("cybercomCategory") == "Workstations and Servers"
        else ""
    )

    # Render the template for this single device
    try:
        jinjaTemplate = Template(deviceTemplate)
        rendered = jinjaTemplate.render(deviceRecord)
        # Remove blank lines and reconstruct with proper indentation
        lines = [line for line in rendered.split("\n") if line.strip()]
        # Find minimum indentation to remove
        min_indent = min(len(line) - len(line.lstrip()) for line in lines) if lines else 0
        # Strip base indentation and add proper indentation (12 spaces for reportObject)
        result_lines = []
        for line in lines:
            stripped = line[min_indent:] if len(line) > min_indent else line.lstrip()
            result_lines.append("          " + stripped)
        return "\n".join(result_lines)
    except Exception as e:
        # Using print for immediate feedback from worker processes
        print(f"Template render error for row {deviceRecord.get('recordId')}: {e}")
        return "" # Return empty string on error

# --- REFACTORED: `createReportObject` now uses multiprocessing ---
def createReportObject(csv_data_batch):
    """
    Processes a batch of CSV rows in parallel and returns the combined XML string.
    """
    # This print statement now gives feedback on smaller batches
    # print(f"  - Processing a batch of {len(csv_data_batch)} devices in parallel...")
    # logger.info(f"Processing a batch of {len(csv_data_batch)} devices...")

    with multiprocessing.Pool(processes=maxConcurrentProcesses) as pool:
        xml_outputs = pool.map(process_row, csv_data_batch)

    # Joins the results of a small batch (reportingBatchSize)
    return "\n".join(filter(None, xml_outputs))

# --- REFACTORED: Main processing logic `process4Cmrs` ---
def process4Cmrs(filePath: str = None, batchSize: int = reportingBatchSize):
    try:
        # Fetch data from CSV file
        print("\nData source: CSV File")
        logger.info("Data source: CSV File")
        if not filePath:
            print("Error: filePath is required when using CSV data source")
            logger.error("Error: filePath is required when using CSV data source")
            return

        try:
            with open(filePath, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
        except FileNotFoundError:
            print(f"Error: {filePath} not found. Please create the file or update the path.")
            logger.error(f"Error: {filePath} not found. Please create the file or update the path.")
            return
    except Exception as e:
        print(f"Error fetching data: {e}")
        logger.error(f"Error fetching data: {e}")
        return

    # --- Offline Upload (Now uses batching) ---
    if offlineUpload:
        print(f"Starting offline report generation for {len(rows)} records...")
        logger.info(f"Starting offline report generation for {len(rows)} records...")

        try:
            with open(offlineReport, 'w', encoding='utf-8') as file:
                # Write the XML header
                placeholder = "<!--PLACEHOLDER-->"
                header_template = createReportEnvelope(placeholder)
                header, footer = header_template.split(placeholder)
                file.write(header)

                # Loop through the data in manageable chunks
                num_batches = (len(rows) + batchSize - 1) // batchSize
                for i in range(0, len(rows), batchSize):
                    current_batch_num = (i // batchSize) + 1
                    batch = rows[i:i + batchSize]
                    print(f"Processing batch {current_batch_num} of {num_batches}...")

                    # Process the small batch in parallel
                    deviceBatch_xml = createReportObject(batch)

                    # Append the result of this batch to the file
                    file.write(deviceBatch_xml)

                    # --- Batch Inspection Logic ---
                    if cmrs_submission_debug and current_batch_num in batches_to_inspect:
                        file.flush()
                        print(f"--> PAUSING on batch {current_batch_num} as requested for inspection.")
                        print(f"    The file '{offlineReport}' is ready for inspection.")
                        input("    Press Enter to continue to the next batch...")

                # Write the final XML footer once all batches are done
                file.write(footer)

            print(f"\nSuccessfully wrote {len(rows)} records to {offlineReport}")
            logger.info(f"Successfully wrote {len(rows)} records to {offlineReport}")

        except Exception as e:
            print(f"\nAn error occurred during file writing: {e}")
            logger.error(f"An error occurred during file writing: {e}")

    # --- Online Upload (Logic with Error Handling and Debug/Retry) ---
    else:
        print(f"Starting online submission for {len(rows)} records...")
        logger.info(f"Starting online submission for {len(rows)} records...")
        num_batches = (len(rows) + batchSize - 1) // batchSize

        for i in range(0, len(rows), batchSize):
            current_batch_num = (i // batchSize) + 1
            batch = rows[i:i + batchSize]
            print(f"Processing and sending batch {current_batch_num} of {num_batches}...")

            # =================== Debug/Retry Logic ===================
            submission_successful = False
            retry_count = 0

            while not submission_successful:
                try:
                    # First, create the XML for the current batch
                    deviceBatch_xml = createReportObject(batch)
                    xmlEnvelope = createReportEnvelope(deviceBatch_xml)

                    if xmlEnvelope:
                        # Now, attempt to submit it
                        submit2Cmrs(xmlEnvelope)

                        # This code will ONLY run if submit2Cmrs did NOT raise an exception
                        print(f"  - Successfully sent {len(batch)} records.")
                        logger.info(f"Sent {len(batch)} records to CMRS SOAP API")
                        submission_successful = True

                except Exception as e:
                    if cmrs_submission_debug:
                        # DEBUG MODE: Save payload and prompt user
                        error_filename = f"error_payload_batch_{current_batch_num}.xml"

                        with open(error_filename, 'w', encoding='utf-8') as f:
                            f.write(xmlEnvelope or "")

                        print(f"\n--- ATTENTION: DEBUG MODE - ERROR DETECTED ON BATCH {current_batch_num} ---")
                        logger.error(f"Submission failed for batch {current_batch_num}. Error: {e}")
                        print(f"The exact XML payload has been saved to: {error_filename}")

                        # Loop to get user input
                        while True:
                            choice = input("Choose an action: (r)etry, (s)top, or (c)ontinue (skip this batch): ").lower()
                            if choice in ['r', 's', 'c']:
                                break
                            print("Invalid input. Please enter 'r', 's', or 'c'.")

                        if choice == 'r':
                            print("Retrying submission for the current batch...")
                            continue  # Retry the while loop
                        elif choice == 's':
                            print("Stopping script as requested.")
                            logger.warning("Script execution stopped by user after an error.")
                            return
                        elif choice == 'c':
                            print("Skipping current batch and continuing with the next one.")
                            logger.warning(f"User skipped batch {current_batch_num} after an error.")
                            submission_successful = True  # Exit while loop to continue for loop
                    else:
                        # NON-DEBUG MODE: Automatic retry logic
                        retry_count += 1
                        if retry_count < cmrs_max_retries:
                            wait_time = 30
                            print(f"\n--- Attempt {retry_count}/{cmrs_max_retries} failed. Retrying in {wait_time} seconds...")
                            logger.warning(f"Attempt {retry_count} failed for batch {current_batch_num}. Retrying...")
                            time.sleep(wait_time)
                            continue
                        else:
                            # Max retries exceeded
                            print(f"\nCRITICAL ERROR: All {cmrs_max_retries} attempts failed for batch {current_batch_num}")
                            logger.critical(f"All {cmrs_max_retries} attempts failed for batch {current_batch_num}.")

                            error_filename = f"fatal_error_payload_batch_{current_batch_num}.xml"
                            with open(error_filename, 'w', encoding='utf-8') as f:
                                f.write(xmlEnvelope or "")
                            print(f"The failing payload has been saved to {error_filename}. Aborting script.")
                            logger.critical(f"Aborting script. Payload saved to {error_filename}")
                            return
            # ================================================================

# --- Main execution block ---
if __name__ == '__main__':
    start_time = time.time()
    try:
        # filePath required for CSV
        process4Cmrs(c2cReportPath, reportingBatchSize)
    except NameError as e:
        print(f"Configuration Error: A variable is not defined. Please check cmrsCustomerData.py. Details: {e}")
    finally:
        elapsed_time = time.time() - start_time
        print(f"✓ Reporting completed in {elapsed_time:.2f} seconds")
        logger.info(f"Reporting completed in {elapsed_time:.2f} seconds")
