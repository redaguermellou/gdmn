# Medical Leave Management System (GDMN)

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

A Django web application for digital management of employee medical leave records, featuring role-based access control, automated document tracking, and reporting.

## ✨ Key Features

- **Role-based authentication** (Admin, HR, Employees)
- **Automated leave request processing**
- **Medical document management**
- **PDF report generation**
- **Audit trail for all changes**

## 🛠️ Technical Stack

- **Backend**: Django 4.2
- **Database**: PostgreSQL
- **Frontend**: Bootstrap 5
- **Deployment**: Docker + Nginx

## 🚀 Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 13+
- Redis (for Celery)

```bash
# Clone repository
git clone git@github.com:redaguermellou/gdmn.git
cd gdmn

# Set up environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
