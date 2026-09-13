# ☀️ Solar Wise

### AI-Powered Residential Solar Planning & Decision Support

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red?logo=streamlit)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/LLM-Groq-orange)](https://groq.com/)
[![RAG](https://img.shields.io/badge/AI-RAG-purple)](#-ai--rag)
[![GitHub](https://img.shields.io/badge/Code-GitHub-black?logo=github)](https://github.com/EngineerArslan-dev/Solar_Wise)

---

## 📌 Overview

**Solar Wise** is an AI-powered residential solar planning assistant designed to help users estimate the solar system that may be suitable for their household.

The application combines:

- ⚡ **Electrical engineering calculations**
- ☀️ **Solar PV system sizing**
- 💰 **Cost and savings estimation**
- 🔋 **Battery and backup analysis**
- 📚 **Retrieval-Augmented Generation (RAG)**
- 🤖 **Groq-powered Generative AI**
- 📊 **Interactive Streamlit dashboard**

The goal is to make preliminary solar-system planning easier for non-technical users while maintaining a clear separation between **deterministic engineering calculations** and **AI-generated explanations**.

> **Important:** Solar Wise is a preliminary planning and decision-support tool. It does not replace a site survey, professional electrical design, structural assessment, or final quotation from a qualified solar professional.

---

# 🎯 Problem

For a homeowner, deciding to install solar can involve many technical and financial questions:

- How much solar capacity is required?
- How many panels are needed?
- What inverter size is appropriate?
- Is a battery required?
- How much roof space is needed?
- What will the system approximately cost?
- How much electricity could it generate?
- How long could it take to recover the investment?

This information is often fragmented across calculators, equipment datasheets, tariff information, installers and online resources.

Solar Wise brings the preliminary analysis into a **single guided workflow**.

---

# 💡 Solution

Solar Wise follows this architecture:

```text
User Inputs
     │
     ▼
Input Validation
     │
     ▼
Engineering Calculation Engine
     │
     ├── PV Sizing
     ├── Panel Count
     ├── Inverter Sizing
     ├── Battery Sizing
     ├── Generation Estimate
     └── Cost & Financial Analysis
     │
     ▼
Structured Results
     │
     ├───────────────┐
     ▼               ▼
   RAG          Groq LLM
Knowledge      Explanation
     │               │
     └───────┬───────┘
             ▼
       Streamlit UI
```

### Core principle

**Python is the source of truth for numerical engineering calculations.**

RAG provides supporting domain knowledge, while Groq is used to explain results and interact with the user.

This prevents the LLM from being responsible for critical numerical calculations.

---

# ✨ Features

## ☀️ Solar System Sizing

Solar Wise can estimate:

- Recommended PV capacity
- Number of solar panels
- Panel capacity assumptions
- Inverter capacity
- Battery requirement
- Expected solar generation

## 💰 Cost & Financial Analysis

The application provides indicative estimates for:

- Solar equipment cost
- Installation/system cost
- Expected savings
- Simple payback period

All financial values should be interpreted as **indicative estimates**, not binding quotations.

## 🔋 Backup & Battery Analysis

Users can specify their backup requirement:

- No backup
- Essential loads
- Full-house backup

Battery recommendations are then incorporated into the system analysis.

## 📍 Location-Aware Analysis

The application accepts the user's city/location and uses the configured solar-resource assumptions associated with the selected location.

## 📚 RAG Knowledge Base

Solar Wise uses Retrieval-Augmented Generation to provide contextual information from the project's knowledge base.

Potential knowledge sources include:

- Solar equipment specifications
- Panel/inverter/battery datasheets
- Solar installation guidance
- Relevant tariff information
- Regulatory information
- Frequently asked questions

## 🤖 AI Advisor

Groq powers the conversational AI layer.

The AI can:

- Explain the recommended system
- Explain the calculations in simple language
- Answer follow-up questions
- Provide context around equipment and solar concepts
- Use retrieved knowledge when answering domain-specific questions

## 📊 Interactive Dashboard

The Streamlit interface provides:

- Solar recommendation
- Cost and savings visualization
- Panel/inverter/battery breakdown
- Generation visualization
- Irradiance reference
- Knowledge-base information
- AI explanation and Q&A

---

# 🧮 Engineering Approach

Solar Wise intentionally separates engineering calculations from the AI layer.

Typical relationships used by the calculation engine include:

### Daily energy requirement

```text
Daily Energy = Monthly Energy Consumption / Number of Days
```

### Approximate PV capacity

```text
PV Capacity ≈ Daily Energy /
              (Effective Peak Sun Hours × Performance Factor)
```

### Panel quantity

```text
Panel Count = Required PV Capacity / Panel Rated Capacity
```

### Battery sizing

Battery sizing considers factors such as:

- Required backup energy
- Depth of discharge
- Battery/system efficiency
- Backup operating requirement

### Financial analysis

```text
Simple Payback ≈ Net System Cost / Annual Savings
```

The exact assumptions and coefficients are maintained within the application and should be independently validated before being used for a real installation.

---

# 🤖 AI & RAG

## Why RAG?

RAG is used as a **knowledge layer**, not as the engineering calculation engine.

Solar-related information can change over time or depend on external documentation. RAG allows Solar Wise to retrieve relevant information from a controlled knowledge base before generating an AI response.

### RAG workflow

```text
User Question
      │
      ▼
Query Processing
      │
      ▼
Knowledge Retrieval
      │
      ▼
Relevant Documents / Chunks
      │
      ▼
Groq LLM
      │
      ▼
Grounded Explanation
```

## AI Guardrails

The system is designed around several safeguards:

- Numerical calculations come from the engineering engine.
- AI should not invent equipment specifications.
- AI should not fabricate tariffs or regulations.
- Missing information should be identified rather than silently fabricated.
- Retrieved information should be preferred over unsupported model knowledge.
- Important assumptions and limitations should be visible to the user.

---

# 🖥️ Application Structure

The repository is organized into modular components:

```text
Solar_Wise/
│
├── app.py
├── main.py
├── config.py
├── requirements.txt
│
├── data/
│
├── data_ingestion/
│
├── engine/
│   └── Solar sizing and engineering calculations
│
├── generation/
│   └── AI / response generation
│
├── processing/
│   └── Data processing and preparation
│
├── validation/
│   └── Input/output validation
│
└── vectorstore/
    └── Retrieval / vector knowledge components
```

The Streamlit application is connected directly to the solar sizing engine so that displayed numerical results originate from the calculation layer rather than being independently recreated in the UI.

---

# 🚀 Getting Started

## 1. Clone the repository

```bash
git clone https://github.com/EngineerArslan-dev/Solar_Wise.git
cd Solar_Wise
```

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

The repository currently includes Plotly for the application's interactive visualizations.

## 4. Configure Groq API Key

Set the following environment variable:

```text
GROQ_API_KEY=your_groq_api_key
```

### Windows PowerShell

```powershell
$env:GROQ_API_KEY="your_groq_api_key"
```

### Linux / macOS

```bash
export GROQ_API_KEY="your_groq_api_key"
```

For Streamlit Community Cloud, add the key through:

```text
App Settings → Secrets
```

Do **not** commit the API key to GitHub. The current application is designed so that the engineering calculations can still operate without the Groq key; the AI explanation and Q&A features require it.

## 5. Run the application

```bash
streamlit run app.py
```

The application will normally open at:

```text
http://localhost:8501
```

---

# 🌐 Deployment

Solar Wise is designed for deployment using **Streamlit Community Cloud**.

Typical deployment workflow:

```text
GitHub Repository
       │
       ▼
Streamlit Community Cloud
       │
       ▼
Configure GROQ_API_KEY
       │
       ▼
Deploy
       │
       ▼
Public Solar Wise Application
```

The GitHub repository contains the Streamlit entry point in `app.py`.

---

# 🧪 Validation & Testing

The project should validate:

### Engineering calculations

- PV capacity calculations
- Panel-count calculations
- Inverter sizing
- Battery calculations
- Generation estimates
- Cost calculations
- Payback calculations

### Input validation

The application should correctly handle:

- Missing values
- Invalid values
- Negative consumption
- Unrealistic roof areas
- Unrealistic consumption
- Incompatible system configurations

### AI validation

AI responses should be evaluated for:

- Groundedness
- Numerical consistency
- Correct use of retrieved information
- Hallucination
- Proper handling of missing information

---

# ⚠️ Disclaimer

Solar Wise provides **preliminary estimates for educational, planning and decision-support purposes**.

Actual solar-system design depends on factors such as:

- Site survey
- Roof orientation
- Shading
- Structural conditions
- Actual solar irradiation
- Electrical load profile
- Equipment specifications
- Utility requirements
- Installation practices
- Current market prices
- Applicable regulations

Final system design, protection, installation and regulatory approval should be performed by appropriately qualified professionals.

---

# 🛠️ Roadmap

## V1 — Current MVP

- [x] Streamlit interface
- [x] Engineering calculation engine
- [x] Solar system sizing
- [x] Cost/savings analysis
- [x] Groq integration
- [x] Initial RAG architecture
- [x] Interactive charts

## Next

- [ ] Improved RAG knowledge base
- [ ] More comprehensive equipment database
- [ ] Improved battery sizing
- [ ] Scenario comparison
- [ ] PDF recommendation report
- [ ] More location-specific solar data

## Future

- [ ] Live electricity tariff integration
- [ ] Live equipment pricing
- [ ] Installer quotation comparison
- [ ] Rooftop image/shading analysis
- [ ] Advanced load profiling
- [ ] Personalized financing options
- [ ] Agentic solar-planning workflow

---

# 👥 Team

### M Arslan — Team Lead / Domain Expert
Electrical engineering, project leadership, system architecture and technical validation.

### Dr. Rabiah Badar — Technical & Research Lead
Engineering methodology, research, validation and technical documentation.


---

# 🎓 Hackathon Project

**Solar Wise** is being developed as an AI product for the **Generative & Agentic AI Training & Hackathon Program**.

The project focuses on combining:

```text
Renewable Energy
      +
Electrical Engineering
      +
Generative AI
      +
RAG
      +
Python
      +
Streamlit
```

The objective is to demonstrate a practical AI application that addresses a real-world problem and can be deployed for actual users.

---

# 📄 Hackathon Deliverables

The project is intended to produce:

1. **PRD Document**
2. **GitHub Code Repository**
3. **Presentation Slides**
4. **Working Application**
5. **Presentation/Demo Video**

---

# 🔗 Project Links

- **GitHub:** https://github.com/EngineerArslan-dev/Solar_Wise
- **Live Application:** *To be added*
- **PRD:** *To be added*
- **Presentation Slides:** *To be added*
- **Demo Video:** *To be added*

---

## ⭐ Project Vision

> **Solar Wise turns electricity usage into an understandable solar system plan, estimated cost and savings using engineering calculations, trusted knowledge and Generative AI.**

**Built with engineering accuracy in mind. Powered by AI. Designed for everyone.** ☀️
