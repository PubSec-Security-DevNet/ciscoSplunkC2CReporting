# Comply to Connect Reporting with Splunk

This repository contains the implementation guides and supporting files for Comply to Connect (C2C) reporting with Splunk, Cisco ISE, optional Cisco Catalyst Center, optional Tenable enrichment, and optional CMRS export workflows.

## Recommended Baseline Versions

Use this baseline unless your program requires a different approved stack.

| Component | Recommended Release/Version |
|---|---|
| Cisco Enterprise Networking for Splunk Platform App | 3.2.10+ | 
| Cisco Catalyst Add-on for Splunk (TA) | 3.2.41+ |
| CMRS reporting supplement tooling | 1.0.6 | 

Primary references:
- App guide (v3.2): [C2C Reporting with Splunk/C2CReportingInstallationGuide-v3.2.md](C2C%20Reporting%20with%20Splunk/C2CReportingInstallationGuide-v3.2.md)
- CMRS guide: [CMRS Reporting Supplement/submit2cmrsAppInstallationGuide.md](CMRS%20Reporting%20Supplement/submit2cmrsAppInstallationGuide.md)
- (Optional) Tenable audit guide: [Tenable C2C HW Auditing/TenableAuditFileInstallationGuide.md](Tenable%20C2C%20HW%20Auditing/TenableAuditFileInstallationGuide.md)

## Documentation Navigation Map

### Core C2C Splunk Reporting Guides
- Current (recommended): [C2C Reporting with Splunk/C2CReportingInstallationGuide-v3.2.md](C2C%20Reporting%20with%20Splunk/C2CReportingInstallationGuide-v3.2.md)
- Legacy reference: [C2C Reporting with Splunk/C2CReportingInstallationGuide-v3.1.md](C2C%20Reporting%20with%20Splunk/C2CReportingInstallationGuide-v3.1.md)

### CMRS Supplement Guides
- Current guide: [CMRS Reporting Supplement/submit2cmrsAppInstallationGuide.md](CMRS%20Reporting%20Supplement/submit2cmrsAppInstallationGuide.md)

> **Migration Note (CMRS Python Workflow):**
> Legacy standalone CMRS Python-file workflows have been migrated into the CMRS app-based implementation.
> Use [CMRS Reporting Supplement/submit2cmrsAppInstallationGuide.md](CMRS%20Reporting%20Supplement/submit2cmrsAppInstallationGuide.md) as the source of truth for setup, configuration, and operational steps.
> If you are upgrading from an older deployment, follow the app guide and do not re-introduce deprecated standalone Python workflow steps.

### Tenable Supplement Guide
- Tenable audit file onboarding: [Tenable C2C HW Auditing/TenableAuditFileInstallationGuide.md](Tenable%20C2C%20HW%20Auditing/TenableAuditFileInstallationGuide.md)

## Step-by-Step Implementation Order

Follow this sequence for a clean deployment.

### Step 1: Start with the v3.2 core guide
1. Open [C2C Reporting with Splunk/C2CReportingInstallationGuide-v3.2.md](C2C%20Reporting%20with%20Splunk/C2CReportingInstallationGuide-v3.2.md).
2. Complete prerequisites and communications planning.
3. Install the app and required TA packages.

### Step 2: Configure data sources
1. Configure Cisco ISE syslog and analytics repositories.
2. Configure Cisco Catalyst Center inputs if used.
3. Confirm Splunk indexes and inputs match your design.

Quick jump links in the v3.2 guide:
- [Cisco Identity Services Engine Configuration](C2C%20Reporting%20with%20Splunk/C2CReportingInstallationGuide-v3.2.md#cisco-identity-services-engine-configuration)
- [Cisco Catalyst Center Configuration - Optional](C2C%20Reporting%20with%20Splunk/C2CReportingInstallationGuide-v3.2.md#cisco-catalyst-center-configuration---optional)
- [Splunk Reporting Application Configuration](C2C%20Reporting%20with%20Splunk/C2CReportingInstallationGuide-v3.2.md#splunk-reporting-application-configuration)

### Step 3: Validate saved-search pipeline behavior (v3.2)
1. Review appendix saved-search documentation in the v3.2 guide.
2. Confirm staged lookup creation and KV store population using `cisco_catalyst_kv_view` saved search or Master Endpoint Record Dashboard to confirm data collection and storage is functional.
3. Validate expected scheduling cadence in your Splunk environment.

Quick jump link:
- [APPENDIX > Reports / Saved Searches](C2C%20Reporting%20with%20Splunk/C2CReportingInstallationGuide-v3.2.md#reports--saved-searches)

### Step 4: Add Tenable enrichment (optional)
1. Deploy the Tenable audit files.
2. Confirm Tenable fields are flowing into the staged searches and endpoint record.

Guide:
- [Tenable C2C HW Auditing/TenableAuditFileInstallationGuide.md](Tenable%20C2C%20HW%20Auditing/TenableAuditFileInstallationGuide.md)

### Step 5: Add CMRS reporting supplement
1. Implement the CMRS app installation guide.
2. If migrating from older deployments, treat legacy standalone CMRS Python-file steps as deprecated and use only the app workflow.
3. Complete app-specific submit2cmrs steps.
4. Validate export/report output.

Guides:
- [CMRS Reporting Supplement/submit2cmrsAppInstallationGuide.md](CMRS%20Reporting%20Supplement/submit2cmrsAppInstallationGuide.md)
