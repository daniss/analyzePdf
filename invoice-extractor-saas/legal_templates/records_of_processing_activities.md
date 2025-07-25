# RECORDS OF PROCESSING ACTIVITIES (ROPA)
## InvoiceAI SAS - GDPR Article 30 Compliance

**Document Reference:** ROPA-2024-001  
**Effective Date:** [DATE]  
**Last Updated:** [DATE]  
**Next Review:** [DATE + 1 year]  
**Prepared by:** Data Protection Officer  
**Organization:** InvoiceAI SAS

---

## ORGANIZATION DETAILS

**Data Controller/Processor:** InvoiceAI SAS  
**Registration Number:** [SIRET/SIREN]  
**Address:** [Complete Address]  
**Data Protection Officer:** [Name]  
**Contact:** dpo@invoiceai.com  
**EU Representative:** [If applicable for non-EU processors]

---

## PROCESSING ACTIVITY 1: CLIENT ACCOUNT MANAGEMENT

### Basic Information
**Processing Activity Name:** Client Account and User Management  
**Data Controller:** InvoiceAI SAS  
**Processing Type:** Controller Processing  
**Start Date:** [Service Launch Date]

### Legal Basis and Purpose
**Primary Purpose:** Provision of invoice processing SaaS services  
**Legal Basis:** 
- Art. 6(1)(b) GDPR - Performance of contract
- Art. 6(1)(f) GDPR - Legitimate interests (service improvement)

**Detailed Purposes:**
- User authentication and access control
- Service billing and subscription management
- Customer support and technical assistance
- Platform performance monitoring and improvement

### Data Subjects
**Categories:**
- Business users (accounting firm employees)
- Administrative contacts
- Technical contacts
- Billing contacts

**Estimated Number:** 500-2,000 individuals annually

### Personal Data Categories
**Identification Data:**
- Full names
- Professional titles/roles
- Company names

**Contact Information:**
- Professional email addresses
- Business phone numbers
- Business postal addresses

**Authentication Data:**
- Usernames/email addresses
- Hashed passwords (bcrypt)
- Multi-factor authentication tokens

**Billing Information:**
- Company billing details
- Payment method information (tokenized)
- Invoice history

**Usage Data:**
- Login timestamps
- Feature usage patterns
- System interaction logs

### Recipients
**Internal Recipients:**
- Customer support team
- Technical development team
- Billing and finance team
- Data Protection Officer

**External Recipients:**
- Payment processors (within EU)
- Cloud hosting providers (EU-based)
- Security monitoring services (EU-based)

**Third Country Recipients:** None for this processing activity

### Cross-Border Transfers
**Status:** No transfers outside EU/EEA for this processing

### Retention Period
**Active Account Data:** Duration of contract + 3 years (prescription period)  
**Billing Data:** 10 years (French accounting obligations)  
**Authentication Logs:** 12 months  
**Marketing Consent:** Until withdrawn

### Security Measures
**Technical Measures:**
- AES-256 encryption at rest
- TLS 1.3+ encryption in transit
- Multi-factor authentication required
- Role-based access controls
- Automated backup with encryption

**Organizational Measures:**
- Staff confidentiality agreements
- Regular GDPR training
- Access control procedures
- Incident response procedures
- Annual security audits

---

## PROCESSING ACTIVITY 2: INVOICE DATA EXTRACTION

### Basic Information
**Processing Activity Name:** AI-Powered Invoice Data Extraction  
**Data Controller:** Client accounting firms (InvoiceAI acts as Processor)  
**Processing Type:** Processor Processing  
**Start Date:** [Service Launch Date]

### Legal Basis and Purpose
**Primary Purpose:** Automated extraction of structured data from invoice documents  
**Legal Basis (as determined by Controllers):**
- Art. 6(1)(b) GDPR - Performance of contract (accounting services)
- Art. 6(1)(f) GDPR - Legitimate interests (efficient invoice processing)

**Detailed Purposes:**
- OCR and intelligent text extraction from invoice images/PDFs
- Structured data extraction (amounts, dates, vendor details)
- Data validation and quality assurance
- Export preparation for accounting systems

### Data Subjects
**Categories:**
- Invoice vendors (business entities and individuals)
- Customer representatives
- Individual contractors/freelancers
- Business contact persons

**Estimated Number:** 10,000-50,000 individuals per month

### Personal Data Categories
**Identification Data:**
- Individual names (vendors, contacts)
- Business names and trading names
- Digital signatures

**Contact Information:**
- Business addresses
- Phone numbers
- Email addresses

**Financial Data:**
- Tax identification numbers
- VAT numbers
- Invoice amounts and payment terms
- Bank account details (when present)

**Professional Data:**
- Professional license numbers
- Business registration numbers
- Industry classifications

### Recipients
**Internal Recipients:**
- AI processing system (automated)
- Data validation team
- Technical support team
- Data Protection Officer

**External Recipients (Sub-processors):**
- Anthropic PBC (Claude AI API) - United States
- Cloud storage providers (EU-based)
- Backup services (EU-based)

### Cross-Border Transfers
**Transfer to:** United States (Anthropic PBC)  
**Legal Mechanism:** EU Standard Contractual Clauses (2021/914/EU)  
**Safeguards:**
- Data minimization applied
- Purpose limitation contractually enforced
- No data retention by recipient
- Encryption in transit (TLS 1.3+)
- Transfer Impact Assessment completed

**Transfer Frequency:** Real-time during processing requests  
**Data Volume:** Moderate (invoice-specific personal data only)

### Retention Period
**Raw Invoice Files:** Deleted immediately after extraction  
**Extracted Personal Data:** 90 days maximum, then automatic deletion  
**Processing Logs:** 12 months  
**Error Logs:** 24 months for improvement purposes

### Security Measures
**Technical Measures:**
- End-to-end encryption (AES-256)
- Secure API communications (TLS 1.3+)
- Access logging and monitoring
- Automated data deletion
- Backup encryption

**Organizational Measures:**
- Data Processing Agreements with clients
- Sub-processor agreements (SCCs)
- Regular security assessments
- Incident response procedures
- Staff training on data handling

---

## PROCESSING ACTIVITY 3: AUDIT AND COMPLIANCE LOGGING

### Basic Information
**Processing Activity Name:** GDPR Compliance and Audit Logging  
**Data Controller:** InvoiceAI SAS  
**Processing Type:** Controller Processing  
**Start Date:** [GDPR Implementation Date]

### Legal Basis and Purpose
**Primary Purpose:** GDPR compliance monitoring and audit trail maintenance  
**Legal Basis:**
- Art. 6(1)(c) GDPR - Legal obligation (GDPR Article 30)
- Art. 6(1)(f) GDPR - Legitimate interests (security monitoring)

**Detailed Purposes:**
- Maintaining records of processing activities
- Audit trail for data subject rights requests
- Security incident detection and response
- Regulatory compliance demonstration

### Data Subjects
**Categories:**
- System users (all account holders)
- Data subjects whose data is processed
- System administrators
- Support staff

**Estimated Number:** All users and data subjects in the system

### Personal Data Categories
**System Access Data:**
- User IDs and session identifiers
- IP addresses
- Login/logout timestamps
- User agent strings

**Processing Activity Data:**
- Data access events
- Data modification events
- Data deletion events
- Export activities

**Technical Data:**
- System error logs
- Performance metrics
- Security event logs

### Recipients
**Internal Recipients:**
- Data Protection Officer
- Security team
- System administrators
- Legal counsel (as needed)

**External Recipients:**
- External auditors (under confidentiality)
- Supervisory authorities (upon request)
- Legal advisors (under privilege)

### Cross-Border Transfers
**Status:** No systematic transfers outside EU/EEA  
**Exception:** Legal proceedings may require disclosure under court order

### Retention Period
**Audit Logs:** 5 years (regulatory compliance)  
**Security Logs:** 12 months  
**Access Logs:** 24 months  
**Incident Records:** 7 years after resolution

### Security Measures
**Technical Measures:**
- Tamper-evident logging system
- Encrypted log storage
- Access controls to log data
- Automated log backup
- Log integrity verification

**Organizational Measures:**
- Log access procedures
- Regular log review processes
- Incident escalation procedures
- Audit trail documentation
- Compliance reporting procedures

---

## PROCESSING ACTIVITY 4: MARKETING AND COMMUNICATIONS

### Basic Information
**Processing Activity Name:** Marketing Communications and Lead Management  
**Data Controller:** InvoiceAI SAS  
**Processing Type:** Controller Processing  
**Start Date:** [Marketing Launch Date]

### Legal Basis and Purpose
**Primary Purpose:** Marketing communications and business development  
**Legal Basis:**
- Art. 6(1)(a) GDPR - Consent (for marketing emails)
- Art. 6(1)(f) GDPR - Legitimate interests (existing customer communications)

**Detailed Purposes:**
- Product announcements and updates
- Educational content delivery
- Lead qualification and nurturing
- Customer satisfaction surveys

### Data Subjects
**Categories:**
- Marketing newsletter subscribers
- Trial users and prospects
- Existing customers
- Webinar attendees
- Conference contacts

**Estimated Number:** 2,000-5,000 individuals

### Personal Data Categories
**Basic Information:**
- Names and professional titles
- Company names
- Professional email addresses

**Preferences:**
- Communication preferences
- Content interests
- Unsubscribe status

**Engagement Data:**
- Email open/click rates
- Website visit patterns
- Content download history

### Recipients
**Internal Recipients:**
- Marketing team
- Sales team
- Customer success team

**External Recipients:**
- Email service providers (EU-based)
- Analytics providers (EU-based)
- CRM service providers (EU-based)

### Cross-Border Transfers
**Status:** Limited transfers may occur with marketing tool providers  
**Safeguards:** Data Processing Agreements with adequate protection clauses

### Retention Period
**Active Subscribers:** Until consent withdrawn  
**Inactive Subscribers:** 24 months, then automatic removal  
**Customer Communications:** Duration of relationship + 3 years  
**Analytics Data:** 12 months in identifiable form

### Security Measures
**Technical Measures:**
- Encrypted data transmission
- Secure data storage
- Access controls
- Consent management platform

**Organizational Measures:**
- Consent recording procedures
- Unsubscribe handling processes
- Data minimization practices
- Regular data cleanup

---

## PROCESSING ACTIVITY 5: BREACH INCIDENT MANAGEMENT

### Basic Information
**Processing Activity Name:** Data Breach Detection and Response  
**Data Controller:** InvoiceAI SAS  
**Processing Type:** Controller Processing  
**Start Date:** [GDPR Implementation Date]

### Legal Basis and Purpose
**Primary Purpose:** Data breach detection, investigation, and regulatory notification  
**Legal Basis:**
- Art. 6(1)(c) GDPR - Legal obligation (GDPR Articles 33-34)
- Art. 6(1)(f) GDPR - Legitimate interests (security protection)

**Detailed Purposes:**
- Security incident detection and analysis
- Breach impact assessment
- Regulatory authority notifications
- Data subject notifications when required
- Incident response coordination

### Data Subjects
**Categories:**
- Individuals affected by potential breaches
- System users involved in incidents
- Security personnel
- External contacts (authorities, clients)

**Estimated Number:** Variable based on incident scope

### Personal Data Categories (in case of breach)
**Potentially Affected Data:**
- All categories from other processing activities
- Incident-specific personal data
- Contact details for notifications

**Investigation Data:**
- User activity logs
- System access records
- Communication records
- Incident timeline data

### Recipients
**Internal Recipients:**
- Incident response team
- Data Protection Officer
- Legal counsel
- Senior management

**External Recipients:**
- CNIL (regulatory notifications)
- Affected clients (controllers)
- External legal counsel
- Cybersecurity experts
- Law enforcement (if criminal activity)

### Cross-Border Transfers
**Status:** May occur during incident response  
**Legal Basis:** Vital interests or legal obligation  
**Safeguards:** Case-by-case assessment with appropriate protections

### Retention Period
**Incident Records:** 7 years after incident closure  
**Investigation Materials:** 5 years  
**Regulatory Correspondence:** 10 years  
**Lessons Learned:** Indefinite (anonymized)

### Security Measures
**Technical Measures:**
- Secure incident tracking system
- Encrypted communication channels
- Access controls to incident data
- Forensic data preservation

**Organizational Measures:**
- Incident response procedures
- Escalation protocols
- Communication templates
- Training and awareness programs
- External expert relationships

---

## SHARED RECIPIENTS ACROSS ALL ACTIVITIES

### Internal Recipients
**Data Protection Officer**
- All processing activities oversight
- Compliance monitoring
- Data subject rights coordination
- Regulatory liaison

**IT Security Team**
- Security monitoring all systems
- Incident response
- Access control management
- Security testing and audits

**Legal Team**
- Compliance advice
- Contract review
- Regulatory correspondence
- Litigation support

### External Recipients (Common)
**Cloud Infrastructure Providers**
- Service: Secure hosting and data storage
- Location: European Union
- Safeguards: Data Processing Agreements, GDPR compliance

**Security Monitoring Services**
- Service: 24/7 security monitoring
- Location: European Union
- Safeguards: Confidentiality agreements, limited access

**External Auditors**
- Service: Compliance and security audits
- Location: European Union
- Safeguards: Professional confidentiality, audit agreements

---

## DATA PROTECTION IMPACT ASSESSMENTS

**Completed DPIAs:**
- DPIA-2024-001: AI-Powered Invoice Processing (High risk processing)
- DPIA-2024-002: Cross-border transfers to US (Anthropic PBC)

**Scheduled DPIAs:**
- Annual review of all high-risk processing activities
- New technology implementations
- Significant changes to processing purposes

---

## INTERNATIONAL TRANSFERS SUMMARY

### Active Transfers
**Anthropic PBC (United States)**
- Purpose: AI-powered invoice data extraction
- Legal Mechanism: Standard Contractual Clauses (2021/914/EU)
- Frequency: Real-time during processing
- Safeguards: Data minimization, encryption, no retention
- TIA Status: Completed (acceptable risk with safeguards)

### Transfer Risk Management
- Annual review of all international transfers
- Monitoring of adequacy decisions and regulatory guidance
- Regular assessment of SCC effectiveness
- Supplementary measures implementation as needed

---

## SUPERVISORY AUTHORITY INFORMATION

**Primary Supervisory Authority:** Commission Nationale de l'Informatique et des Libertés (CNIL)  
**Registration Status:** [If required by Member State law]  
**Last Communication:** [Date if applicable]  
**Pending Matters:** None

---

## REVIEW AND MAINTENANCE

**Review Frequency:** Annual or upon material changes  
**Last Review Date:** [DATE]  
**Next Scheduled Review:** [DATE + 1 year]  
**Responsible Person:** Data Protection Officer

**Change Triggers:**
- New processing activities
- Changes to legal basis or purposes
- New categories of personal data
- Changes to recipients or transfers
- Regulatory requirements changes

---

**DOCUMENT APPROVAL**

**Data Protection Officer:**  
Name: _________________________  
Date: _________________________  
Signature: ____________________

**Legal Counsel:**  
Name: _________________________  
Date: _________________________  
Signature: ____________________

---

**Document Control:**
- **Version:** 1.0
- **Classification:** Confidential
- **Distribution:** Senior Management, DPO, Legal Team
- **Storage:** Secure document management system
- **Backup:** Encrypted backup with 7-year retention