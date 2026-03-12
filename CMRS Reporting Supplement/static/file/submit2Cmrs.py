"""
Script Name: submit2Cmrs.py
Description: Reporting automation to submit C2C reporting requirements to CMRS from the Cisco C2C Reporting App 3.0
Author: Chad Mitchell, chadmi@cisco.com
Version: 1.1
Contributors: Thomas Barbour (GDIT)
"""

import logging
import csv
import re
import requests
from jinja2 import Template
from datetime import datetime, timedelta
from cmrsCustomerData import *
import multiprocessing

# Multiprocess configuration - Adjust for number of CPU processes to use for parallel processing
# Set to None to use all available CPU cores
maxConcurrentProcesses = 8

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
            "SOAPAction": soapAction
        }
        response = requests.post(
            soapEndpoint,
            data=xmlEnvelope.encode("utf-8"),
            headers=headers,
            cert=(certFile, keyFile),
            verify=caBundle,
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
        # print(xmlOutput) # Removed for cleaner output in multiprocessing
        return xmlOutput
    except Exception as e:
        print(f"An error occurred during envelope creation: {e}")
        logger.error(f"An error occurred during envelope creation: {e}")
        return None

# Worker function for multiprocess
# This function processes a single row and returns the generated XML object.
def process_row(row):
    deviceTemplate = '''
          <ar:reportObject>
            <ar:device timestamp="{{ iseLastSeen }}">
              <device:device_ID>
                <cndc:resource>"{{ publisherName }}"</cndc:resource>
                <cndc:record_identifier>"{{ recordId }}"</cndc:record_identifier>
              </device:device_ID>
              <device:operational_attributes>
                <cndc:resource>"{{ publisherName }}"</cndc:resource>
                <cndc:record_identifier>"{{ recordId }}"</cndc:record_identifier>
              </device:operational_attributes>
              <device:identifiers>
                <device:FQDN>
                  <device:host_name>"{{ dnsName }}"</device:host_name>
                  <device:realm>"{{ AD_User_DNS_Domain }}"</device:realm>
                </device:FQDN>
              </device:identifiers>
              <device:configuration>
                <device:network_configuration>
                  <device:network_interface_ID>"{{ NAS_Port_Id }}"</device:network_interface_ID>
                  <device:host_network_data>
                    <device:connection_mac_address>"{{ macAddress }}"</device:connection_mac_address>
                    <device:connection_ip>
                      <cndc:IPv4>"{{ Ipv4Address }}"</cndc:IPv4>
                    </device:connection_ip>
                    <device:connection_ip>
                      <cndc:IPv6>"{{ Ipv6Address }}"</cndc:IPv6>
                    </device:connection_ip>
                  </device:host_network_data>
                </device:network_configuration>
                <device:cpe_inventory>
                  <device:cpe_record>
                    <cpe:platformName>
                      <cpe:assessedName name="{{ osPlatformName }}"/>
                    </cpe:platformName>
                    <tagged_value:taggedString name="OSVendor" value="{{ osVendor }}"/>
                    <tagged_value:taggedString name="OSName" value="{{ osCompositeName }}"/>
                    <tagged_value:taggedString name="OSVersion" value="{{ osVersion }}"/>
                    <tagged_value:taggedString name="OSEdition" value="{{ osEdition }}"/>
                    <tagged_value:taggedString name="OSMktVersion" value="{{ osMktVersion }}"/>
                    <tagged_value:taggedString name="OSArch" value="{{ osArch }}"/>
                    <tagged_value:taggedString name="OSCompositeName" value="{{ osCompositeName }}"/>
                  </device:cpe_record>
                </device:cpe_inventory>
              </device:configuration>
              <tagged_value:taggedString name="ccsafa.dod.mil" value="{{ ccsafa_dod_mil }}"/>
              <tagged_value:taggedString name="geolocation.dod.mil" value="{{ geolocation_dod_mil }}"/>
              <tagged_value:taggedString name="ownorg.dod.mil" value="{{ ownorg_dod_mil }}"/>
              <tagged_value:taggedString name="cndsp.dod.mil" value="{{ cndsp_dod_mil }}"/>
              <tagged_value:taggedString name="adminorg.dod.mil" value="{{ adminorg_dod_mil }}"/>
              <tagged_value:taggedString name="cocomaor.dod.mil" value="{{ cocomaor_dod_mil }}"/>
              <tagged_value:taggedString name="SwLocation" value="{{ Location }}"/>
              <tagged_value:taggedString name="SwHostname" value="{{ NetworkDeviceName }}"/>
              <tagged_value:taggedString name="SwPortDescription" value="{{ NAS_Port_Id }}"/>
              <tagged_value:taggedString name="SwPortAlias" value=""/>
              <tagged_value:taggedString name="SegmentPath" value=""/>
              <tagged_value:taggedString name="DeviceRole" value=""/>
              <tagged_value:taggedString name="VendorClassificationInfo" value="{{ SystemManufacturer }}"/>
              <tagged_value:taggedString name="NetworkFunction" value=""/>
              <tagged_value:taggedString name="ManufacturerClassification" value="{{ SystemManufacturer }}"/>
              <tagged_value:taggedString name="GuestCorporateState" value=""/>
              <tagged_value:taggedString name="ClassificationType" value=""/>
              <tagged_value:taggedString name="SystemRoles" value="{{ cybercomCategory }}"/>
              <tagged_value:taggedString name="NICVendor" value="{{ NICVendor }}"/>
              <tagged_value:taggedString name="username" value="{{ UserName }}"/>
              <tagged_value:taggedString name="BIOSGUID" value="{{ BIOSGUID }}"/>
              <tagged_value:taggedString name="BiosVendor" value="{{ BiosVendor }}"/>
              <tagged_value:taggedString name="BiosSerialNumber" value="{{ BiosSerialNumber }}"/>
              <tagged_value:taggedString name="BiosVersion" value="{{ BiosVersion }}"/>
              <tagged_value:taggedString name="BootPartitionTotalSpace" value="{{ BootPartitionTotalSpace }}"/>
              <tagged_value:taggedString name="TPMVersion" value="{{ TPMVersion }}"/>
              <tagged_value:taggedString name="SysvolDescription" value=""/>
              <tagged_value:taggedString name="SysvolFileSystem" value=""/>
              <tagged_value:taggedString name="SysvolFreeSpace" value=""/>
              <tagged_value:taggedString name="SysvolName" value=""/>
              <tagged_value:taggedString name="SysvolTotalSpace" value=""/>
              <tagged_value:taggedString name="FreeDiskSpace" value="{{ BootPartitionFreeSpace }}"/>
              <tagged_value:taggedString name="TotalDiskSpace" value="{{ BootPartitionTotalSpace }}"/>
              <tagged_value:taggedString name="NumOfCPU" value="{{ NumCpuCores }}"/>
              <tagged_value:taggedString name="SystemManufacturer" value="{{ SystemManufacturer }}"/>
              <tagged_value:taggedString name="SystemModel" value="{{ SystemModel }}"/>
              <tagged_value:taggedString name="NumInstalledCPU" value="{{ NumInstalledCPU }}"/>
              <tagged_value:taggedString name="TotalPhysicalMemory" value="{{ TotalPhysicalMemory }}"/>
              <tagged_value:taggedString name="MotherBoard Manufacturer" value="{{ BiosVendor }}"/>
              <tagged_value:taggedString name="MotherBoard Serial Number" value="{{ BiosSerialNumber }}"/> 
              <tagged_value:taggedString name="MotherBoard Version" value="{{ BiosVersion }}"/>
              <tagged_value:taggedString name="CPUManufacturer" value="{{ CpuVersion }}"/>
              <tagged_value:taggedString name="CPUSpeed" value="{{ CPUSpeed }}"/>
              <tagged_value:taggedString name="CPUCoreCount" value="{{ NumCpuCores }}"/>
              <tagged_value:taggedString name="CyberComCategory" value="{{ cybercomCategory }}"/>
              <tagged_value:taggedString name="C2C Managed" value="{{ c2cManaged }}"/>
              <tagged_value:taggedString name="Sensor version" value="{{ iseVersion }}"/>
              <tagged_value:taggedString name="Sensor ID" value="{{ iseSerial }}"/>
              <tagged_value:taggedString name="Sensor Publisher Version" value="Cisco ISE Reporting App Version {{ publisherVersion }}"/>
              <tagged_value:taggedString name="rule C2C OverallComplianceStatus" value="{{ PostureStatus }}"/>
              <tagged_value:taggedString name="rule C2C EndpointFirewall" value="{{ c2cFirewallRule }}"/>
              <tagged_value:taggedString name="rule C2C EndpointAntiMalware" value="{{ c2cEndpointMalwareRule }}"/>
              <tagged_value:taggedString name="rule C2C EndpointDAREncryption" value="{{ c2cEndpointEncryptRule }}"/>
              <tagged_value:taggedString name="rule C2C PatchAgent" value="{{ c2cPatchingRule }}"/>
              <tagged_value:taggedString name="rule C2C VulnScanCurrent" value="{{ VulnScanCurrent }}"/>
              <tagged_value:taggedString name="rule C2C EndpointAppWhitelisting" value="{{ c2cEndpointAppWlRule }}"/>
              <tagged_value:taggedString name="rule C2C PKITrustRoots" value="{{ c2cPkiRootsRule }}"/>
              <tagged_value:taggedString name="rule C2C EndpointMonitoring" value="{{ c2cEndpointMonitorRule }}" />
              <tagged_value:taggedString name="rule C2C Patching" value="{{ c2cPatchingRule }}" />
              <tagged_value:taggedString name="C2C Auth Result" value="{{ C2C_Auth_Result }}" />
              <tagged_value:taggedString name="C2C Authorization Source" value="{{ C2C_Authorization_Source }}" />
              <tagged_value:taggedString name="C2C Connection" value="{{ C2C_Connection }}" />
              <tagged_value:taggedString name="C2C Device Token" value="{{ C2C_Device_Token }}" />
              <tagged_value:taggedString name="C2C Last Auth" value="{{ C2C_Last_Auth }}" />
              <tagged_value:taggedString name="C2C Last Auth Access Assignment" value="{{ C2C_Last_Auth_Access_Assignment }}" />
              <tagged_value:taggedString name="C2C Primary Auth" value="{{ C2C_Primary_Auth }}" />
              <tagged_value:taggedString name="C2C Secondary Auth" value="{{ C2C_Primary_Auth }}" />
              <tagged_value:taggedString name="C2C ICAM Last Auth Device" value="{{ ICAM_Device }}"/><!--Common Name followed by double-dash delimiter then cert SN -->
              <tagged_value:taggedString name="C2C ICAM Last Auth Device CA" value="{{ ICAM_Device_CA }}"/>
              <tagged_value:taggedString name="C2C ICAM Last Auth Device Root CA" value="{{ ICAM_Device_Sub_CA }}"/>
              <tagged_value:taggedString name="C2C ICAM Last Auth Device" value="{{ ICAM_User }}"/><!--Common Name followed by double-dash delimiter then cert SN -->
              <tagged_value:taggedString name="C2C ICAM Last Auth Device CA" value="{{ ICAM_User_CA }}"/>
              <tagged_value:taggedString name="C2C ICAM Last Auth Device Root CA" value="{{ ICAM_User_Sub_CA }}"/>
              <tagged_value:taggedString name="C2C Wired Connections" value="{{ Wired_Connections }}" />
              <tagged_value:taggedString name="C2C Wireless Connections" value="{{ Wireless_Connections }}" />
              <tagged_value:taggedString name="C2C Access Level Unknown" value="{{ Total_Full_Access }}" />
              <tagged_value:taggedString name="C2C Access Level Remediation" value="{{ Total_Remediation }}" />
              <tagged_value:taggedString name="C2C Access Level Full Access" value="{{ Total_Unknown }}" />
            </ar:device>
          </ar:reportObject>
    '''
    
    # Clean and transform the record
    deviceRecord = {key.replace(".", "_").replace(" ", "_"): (value.replace('\n', ' ') if isinstance(value, str) and value != 'N/A' and value != 'None' else "") for key, value in row.items()}
    
    # Set recordId with Coalesce
    deviceRecord["recordId"] = deviceRecord.get('uuid') or deviceRecord.get('BIOSGUID') or deviceRecord.get('record_id') or deviceRecord.get('macAddress')

    # Extract CPU Speed
    cpu_version = deviceRecord.get("CpuVersion", "")
    cpuMatch = re.search(r"(\d+\.\d+GHz)", cpu_version)
    deviceRecord["CPUSpeed"] = cpuMatch.group(1) if cpuMatch else ""

    # Set VulnScanCurrent
    def dateDelta(dtInput: str) -> bool:
        dtFormat = "%m/%d/%y %H:%M:%S"
        if not dtInput:
            return False
        try:
            dt_input = datetime.strptime(dtInput, dtFormat)
            return (datetime.now() - dt_input) > timedelta(days=acasDelta)
        except (ValueError, TypeError):
            # logger.warning(f"Could not parse date: {dtInput}") # log parsing errors
            return False
            
    deviceRecord["VulnScanCurrent"] = "Passed" if dateDelta(deviceRecord.get('acasSeen')) else "Failed"

    # Set CMRS Posture Rules
    c2cRules = {
        "c2cFirewallRule": c2cFirewallRule, "c2cEndpointMalwareRule": c2cEndpointMalwareRule,
        "c2cEndpointEncryptRule": c2cEndpointEncryptRule, "c2cPatchAgentRule": c2cPatchAgentRule,
        "c2cEndpointAppWlRule": c2cEndpointAppWlRule, "c2cPkiRootsRule": c2cPkiRootsRule,
        "c2cEndpointMonitorRule": c2cEndpointMonitorRule, "c2cPatchingRule": c2cPatchingRule
    }
    for key, value_key in c2cRules.items():
        deviceRecord[key] = deviceRecord.get(value_key, "")

    # Add Publisher Details
    deviceRecord["iseVersion"] = iseVersion
    deviceRecord["iseSerial"] = iseSerial
    deviceRecord["publisherVersion"] = publisherVersion
    deviceRecord["c2cManaged"] = "True" if deviceRecord.get("PostureStatus") else ""

    # Render the template for this single device
    try:
        jinjaTemplate = Template(deviceTemplate)
        return jinjaTemplate.render(deviceRecord)
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
    print(f"  - Processing a batch of {len(csv_data_batch)} devices in parallel...")
    logger.info(f"Processing a batch of {len(csv_data_batch)} devices...")

    with multiprocessing.Pool(processes=maxConcurrentProcesses) as pool:
        xml_outputs = pool.map(process_row, csv_data_batch)

    # Joins the results of a small batch (reportingBatchSize)
    return "".join(filter(None, xml_outputs))

# --- REFACTORED: Main processing logic `process4Cmrs` ---
def process4Cmrs(filePath: str, batchSize: int = reportingBatchSize):
    try:
        with open(filePath, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
    except FileNotFoundError:
        print(f"Error: {filePath} not found. Please create the file or update the path.")
        logger.error(f"Error: {filePath} not found. Please create the file or update the path.")
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
                    batch = rows[i:i + batchSize]
                    print(f"Processing batch {i//batchSize + 1} of {num_batches}...")
                    
                    # Process the small batch in parallel
                    deviceBatch_xml = createReportObject(batch)
                    
                    # Append the result of this batch to the file
                    file.write(deviceBatch_xml)

                # Write the final XML footer once all batches are done
                file.write(footer)
            
            print(f"\nSuccessfully wrote {len(rows)} records to {offlineReport}")
            logger.info(f"Successfully wrote {len(rows)} records to {offlineReport}")

        except Exception as e:
            print(f"\nAn error occurred during file writing: {e}")
            logger.error(f"An error occurred during file writing: {e}")

    # --- Online Upload (Logic with Error Handling) ---
    else:
        print(f"Starting online submission for {len(rows)} records...")
        logger.info(f"Starting online submission for {len(rows)} records...")
        num_batches = (len(rows) + batchSize - 1) // batchSize
        
        for i in range(0, len(rows), batchSize):
            batch = rows[i:i + batchSize]
            print(f"Processing and sending batch {i//batchSize + 1} of {num_batches}...")

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

            except Exception as e:
                # Any exception from createReportObject or submit2Cmrs will be caught here
                print("\nCRITICAL ERROR: An unrecoverable error occurred.")
                print("Aborting further submissions to prevent data loss or invalid posts.")
                logger.critical(f"Aborting script due to unrecoverable error: {e}")
                # Exit the script entirely
                return

# --- Main execution block ---
if __name__ == '__main__':
    try:
        process4Cmrs(c2cReportPath, reportingBatchSize)
    except NameError as e:
        print(f"Configuration Error: A variable is not defined. Please check cmrsCustomerData.py. Details: {e}")
