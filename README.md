# 🏙️ CitySync AI

**Autonomous Multi-Agent Copilot for Building Plan Compliance**

CitySync AI is an enterprise-grade, fully autonomous compliance copilot. Driven by a specialized 5-agent architecture, it uses spatial OCR, deterministic rule engines, and Generative AI to analyze residential floor plans against municipal building codes—delivering instant audit results, actionable LLM fix suggestions, and perfectly mapped visual overlays.

---

## ✨ Enterprise Features

| Feature | Description |
|---|---|
| **Multi-Agent Orchestration** | 5 autonomous agents handle OCR, parsing, compliance, and reporting |
| **Spatial Document Intelligence** | High-fidelity OCR extracting precise `(x, y)` coordinate bounding boxes |
| **GenAI Fix Suggestions** | Gemini 2.0 Flash acts as a senior architect recommending build changes |
| **Self-Correcting Vision** | Fallback loops use OpenCV to enhance contrast on low-confidence blueprints |
| **Zero-Overlap Visualizer** | Interactive overlays powered by a custom Voronoi rectilinear collision algorithm |
| **Cryptographic Auditability** | Every system decision is logged to a structured, verifiable JSON ledger |
| **Multi-City Database** | Out-of-the-box compliance rules for New Delhi, Mumbai, and Bangalore |
| **Premium SaaS UI** | Custom Streamlit overrides with glassmorphism and animated components |

---

## 🏗️ Architecture

```text
CitySync/
├── app.py                      # Main Streamlit Application UI
├── agents/                     # Autonomous AI Workflow Agents
│   ├── orchestrator.py         # Master workflow controller
│   ├── document_agent.py       # Spatial OCR & Image enhancement
│   ├── room_agent.py           # NLP Dimension Parsing (Gemini)
│   ├── compliance_agent.py     # City Rules & LLM Recommendations
│   └── report_agent.py         # Audit Log Aggregator
├── core/                       
│   ├── audit_logger.py         # Verifiable JSON decision ledger
│   ├── vision_reader.py        # EasyOCR & OpenCV ingestion
│   ├── floor_plan_annotator.py # Zero-overlap Voronoi bounding boxes
│   └── report_generator.py     # Enterprise PDF certificate builder
├── data/
│   └── city_rules.py           # Local municipal bye-laws registry
├── ui/
│   └── layout.py               # Custom SaaS CSS and Layouts
└── requirements.txt
```

---

## 🚀 Setup & Installation

CitySync AI requires both a Python backend (for the autonomous agents) and a Node.js environment (for the React landing page/frontend).

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Poppler** (required by `pdf2image` for blueprint extraction)
  - macOS: `brew install poppler`
  - Ubuntu: `sudo apt-get install poppler-utils`
  - Windows: [Download binaries](https://github.com/oschwartz10612/poppler-windows) and add to PATH

### 1. Python AI Backend (Streamlit)

The backend handles the Multi-Agent orchestration, spatial OCR, and compliance rule verification.

```bash
# Clone the repository
git clone <repository-url>
cd CitySync

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Start the Streamlit Copilot Server
streamlit run app.py
```
*The AI backend will start at `http://localhost:8501`.*

### 2. React Frontend

The frontend provides the main landing portal for the enterprise application.

```bash
# Open a new terminal tab and navigate to the frontend folder
cd CitySync/frontend

# Install node dependencies
npm install

# Start the development server
npm run dev
```
*The React frontend will start at `http://localhost:3000` (or the port specified in your terminal output).*

---

## 📋 Usage Workflow

1. **Launch both servers** using the instructions above.
2. **Navigate** to the frontend portal (typically port 3000).
3. **Select a City** (New Delhi, Mumbai, or Bangalore).
4. **Upload a PDF** floor plan into the portal.
5. **Review** the autonomous agent execution timeline. 
6. **Analyze** the zero-overlap visualizer annotated directly over your floor plan.
7. **Download** the cryptographically verifiable JSON Audit trial and PDF Compliance Report.

---

## 🔧 Tech Stack

- **Autonomy Framework**: Native Python Multi-Agent Architecture
- **Vision Parsing**: `EasyOCR` + `OpenCV` (Spatial text blocks, thresholding filters) + `pdf2image`
- **Generative AI**: `google.genai` SDK querying **Gemini 2.0 Flash**
- **Application Logic**: Python (`pandas`, `fpdf2`, recursive deterministic rule engine)
- **User Interface**: `Streamlit` with deep custom CSS/HTML canvas injections + React Frontend

---

## 📜 License

This project was built for hackathon demonstration. All rights reserved.
