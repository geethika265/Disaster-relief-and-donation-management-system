# 🌍 Disaster Relief & Donation Management System

A Flask + MySQL–based database management system designed to streamline the coordination and resource distribution process during disaster events.  
This project demonstrates advanced DBMS concepts such as triggers, stored procedures, and complex queries integrated into a functional web interface.

---

## 📘 Project Overview
Disaster management involves coordination between multiple entities such as NGOs, government agencies, volunteers, and relief camps.  
Manual data handling can lead to inefficiency and redundancy.  
This system maintains a **centralized database** that tracks all disaster-related information — improving transparency, accountability, and decision-making.

---

## 🧩 Features
- ✅ CRUD operations for all major entities (Disaster, Camp, Victim, Volunteer, Resource, etc.)
- ✅ Stored procedures for automated volunteer assignment and aid distribution  
- ✅ Triggers for real-time data validation and stock management  
- ✅ Functions for analytical computation (e.g., camp occupancy)
- ✅ Dynamic SQL query execution from the frontend (Join, Aggregate, Nested)
- ✅ Flash messaging for success/error alerts
- ✅ Clean, responsive HTML-CSS interface

---

## ⚙️ Tech Stack
| Component | Tool / Technology |
|------------|------------------|
| **Database** | MySQL 8.0 |
| **Backend** | Python (Flask) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **IDE** | Visual Studio Code |
| **Diagramming** | Draw.io / MySQL Workbench |
| **Version Control** | Git & GitHub |

---

## 🏗️ Database Design

### **Entities**
- **Disaster:** Type, severity, city, district, state, timeline  
- **ReliefCamp:** Camp details, capacity, disaster linkage  
- **Volunteer:** Personal details, skills, availability  
- **Victim:** Camp assignment and demographic data  
- **Resource:** Items stocked and distributed  
- **NGO / GovernmentAgency / Donation:** Organizational and funding information  

### **Relationships**
- 1:M → Disaster → ReliefCamp, Camp → Victim  
- M:N → Camp–Volunteer, Camp–Resource  
- Ternary → FundAllocation (Agency–NGO–Donation)  
- Weak Entity → AidDistribution (composite PK)  

---

## 💾 Database Logic

### **Stored Procedures**
- `DistributeAid()` → Automates aid distribution and updates stock  
- `assign_volunteer()` → Assigns volunteers to camps dynamically  

### **Functions**
- `camp_occupancy_for()` → Returns occupancy percentage  
- `CountVictimsInCamp()` → Returns victim count in a camp  

### **Triggers**
- `bi_aiddist_check` → Validates before insert  
- `ai_aiddist_decrement` → Decrements stock automatically  
- `ad_aiddist_restock` → Restores stock after deletion  

---

## 🖥️ Application Structure
```
Disaster_Relief/
│
├── static/
│   └── app.css
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── crud_list.html
│   ├── dbops.html
│   └── queries.html
│
├── app.py
├── requirements.txt
└── disaster_relief_schema.sql
```

---

## 🚀 Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/geethika265/Disaster-relief-and-donation-management-system.git
   cd Disaster-relief-and-donation-management-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Import the SQL schema**
   ```bash
   mysql -u root -p < disaster_relief_schema.sql
   ```

4. **Run the Flask app**
   ```bash
   python app.py
   ```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 📊 Modules in the UI
| Module | Description |
|---------|--------------|
| **Dashboard (index.html)** | Displays summary stats and recent aid activities |
| **CRUD Interface (crud_list.html)** | Add, view, update, or delete table records |
| **DB Operations (dbops.html)** | Run stored procedures and functions |
| **Queries (queries.html)** | Execute Join, Aggregate, and Nested queries dynamically |

---

## 🧠 Learning Outcomes
- Applied **ER modeling**, **normalization**, and **relational mapping**
- Implemented **constraints, triggers, and stored procedures**
- Built an **interactive web interface** to test all DB operations
- Integrated **frontend and backend** for a complete DBMS workflow

---

## 👩‍💻 Team
**Submitted by:**  
- Geethika Annam – PES2UG23AM039  
- Chandana N K – PES2UG23AM022  

**Under the guidance of:**  
Dr. Geetha D, Associate Professor  
Department of CSE (AI & ML), PES University

---

## 🏛️ Institution
**Department of Computer Science and Engineering (AI & ML)**  
PES University, Electronic City Campus, Bengaluru – 560100  

---

## 🧾 License
This repository is for **academic purposes only**.  
Unauthorized reproduction or distribution of this work is not permitted.
