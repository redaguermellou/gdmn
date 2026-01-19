# Changelog V2.1 - Analytics, Coverage & Smart Automation

## [2.1.0] - 2026-01-19

### 🌟 Major New Features

#### 🏥 Medical Coverage System (Prise en Charge)
- **New Lifecycle Management**: Introduced a complete module for "Prise en Charge" (PEC) requests.
- **Automated Reference Tracking**: Implemented a dedicated generator for clinical IDs (`PEC-YYYYMMDD-XXXX`).
- **Care Type Categorization**: Support for specialized soins (Consultation, Hospitalisation, Pharmarcie, Chirurgie, etc.).
- **Financial Calculation**: Automatic calculation of "Reste à charge" (remaining balance) based on coverage percentage and estimated costs.
- **Lifecycle Actions**: Built-in Approval/Rejection workflow for Admins and Controllers with real-time status updates.

#### 📊 Global Analytics Dashboard
- **Interactive Visualizations**: Integrated Chart.js for real-time data analysis.
  - **Dossier Distribution**: Doughnut charts for status and priority tracking.
  - **Department Insights**: Bar charts tracking medical activity by organization unit.
  - **PEC Financials**: Pie charts breaking down coverage types and costs.
- **Reporting Hub**: A centralized page for high-level management to track critical dossiers and recent submissions.

#### 🏢 Multi-Department Organization
- **User Linking**: Added a native `department` field to the User model.
- **Cross-Model Integration**: Both dossiers and coverage requests now link directly to organizational departments.

---

### 🚀 Smart Automation & UX (Zero-Typing Focus)

- **Smart Department Fetching**: dossiers and PECs now automatically inherit the department from the assigned patient/employee, removing redundant data entry.
- **Drop-down Standardization**: Replaced manual text fields with curated selection menus for:
  - **Medical Staff**: Predefined list of doctors and practitioners.
  - **Institutions**: Searchable list of clinics, hospitals, and pharmacies.
- **Simplified Creation Flow**: Forms now hide auto-filled fields (like department) to minimize visual noise and cognitive load.
- **Direct Navigation**: Integrated PEC and Analytics links into the main navigation sidebar for instant access.

---

### 🛠️ Technical Improvements & Stability

- **Medical Categorization**: Added a `category` field (Optique, Cardiologie, etc.) to Medical dossiers for more granular reporting.
- **Role Simplification**: 
  - Completely retired the 'NORMAL' user role.
  - Migrated standard users to the 'AGENT' role for a more powerful self-service experience.
  - Standardized all permission checks across views (`AGENT`, `CONTROLLER`, `ADMIN`).
- **Financial Precision Fix**: 
  - Resolved `TypeError` regarding Decimal vs Float multiplication in financial modules.
  - Migrated all cost-related logic to use strictly precise Decimal arithmetic.
- **Database Resilience**:
  - Implemented a Pymysql monkey patch for Python 3.14/Django compatibility.
  - Disabled the `RETURNING` clause to ensure 100% compatibility with older MariaDB/MySQL environments.
  - Applied migration sequence (0013-0016) to synchronize the new data architecture.
- **Global Error Handling**: Added a validation dashboard to the PEC creation form to catch and display all submission issues clearly.

this is a draft vertion 