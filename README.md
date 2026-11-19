# BusinessOnBot – AI Customer Support Agent with Commitment Guardrails

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.164-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.67-FF4B4B.svg)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/Tests-16%20Passed-brightgreen.svg)]()

> Working prototype for the **Product Intern interview assignment at BusinessOnBot**.  
> Demonstrates an independent validation and guardrail layer between AI response generation and final customer delivery across WhatsApp, Instagram, Messenger, Email, Voice, and Web Chat.

---

## 1. Project Overview & Core Problem

Large Language Models (LLMs) tend to generate helpful-sounding but factually unsupported promises when answering customer support inquiries. In e-commerce, unverified AI commitments cause serious financial loss, operational bottlenecks, legal liabilities, and loss of brand trust.

This prototype demonstrates how an independent guardrail engine prevents these **five core failure scenarios**:
1. **Refund Promises**: AI promising "your refund will arrive tomorrow" without checking actual status or arrival dates.
2. **Inventory Commitments**: AI confirming product availability without verifying real warehouse stock, freshness, or ambiguous variants.
3. **Discount Hallucinations**: AI inventing unauthorized promotional codes (e.g., `SAVE30`) or offering discretionary discounts.
4. **Medical / Safety Assurances**: AI making definitive claims that a skincare product is "completely safe during pregnancy".
5. **Return Policy Exceptions**: AI approving a return after 22 days without checking the brand's 15-day return window.

---

## 2. System Architecture

The core engineering principle is: **NEVER blindly trust the LLM output.** The guardrail is a deterministic, evidence-based arbiter operating between LLM generation and customer delivery.

```text
Customer Query (WhatsApp / Instagram / Email / Voice / Web)
      │
      ▼
Channel Adapter (Normalize message & strip channel-specific constraints)
      │
      ▼
Intent Detection & Risk Classification (Low / Medium / High / Critical)
      │
      ▼
Retrieve Business Data & Policies (Refunds, Inventory, Coupons, Policies, Safety)
      │
      ▼
LLM Response Generation (Draft Response in Structured JSON)
      │
      ▼
Commitment Detection (Independent parser: Financial, Time, Stock, Pricing, Policy, Safety)
      │
      ▼
Evidence & Policy Validation (5-Point Verification Ledger)
      │   1. Is the claim supported by verified records?
      │   2. Is the evidence current (TTL freshness)?
      │   3. Does evidence belong to this customer/order/SKU?
      │   4. Is the action authorized by the brand?
      │   5. Does the claim violate brand policy?
      ▼
Decision Engine
      ├── ALLOW: All claims verified and authorized.
      ├── REWRITE: Overconfident claims safely replaced with verified facts.
      ├── BLOCK: Critical unsupported claim that cannot be safely mitigated.
      └── ESCALATE: Missing data, contradictory records, or manager approval required.
      │
      ▼
Response Rewriter & Delivery Gateway (Channel formatting: Voice TTS, Email, WhatsApp)
      │
      ▼
Audit Logging & Analytics (JSON, SQLite & Pandas Analytics)
```

---

## 3. The 5 Core Assignment Scenarios

### Scenario 1: Refund Inquiry ("Where is my refund? I returned the kurta 6 days ago.")
Initial AI Draft: `"Your refund has been processed and will reach your account by tomorrow."`

- **Scenario A (Status is Pending, `ORD-1001`)**:
  - **Decision**: `REWRITE`
  - **Delivered Safe Response**: *"Your return is recorded, but your refund has not yet been confirmed as processed. Our support team can help you check the latest status."*
- **Scenario B (Processed, No Arrival Date, `ORD-1002`)**:
  - **Decision**: `REWRITE`
  - **Delivered Safe Response**: *"Your refund has been processed. However, we don't have a confirmed arrival date yet."*
- **Scenario C (Processed with Official Date, `ORD-1003`)**:
  - **Decision**: `ALLOW` (Estimate verified from payment gateway).
- **Scenario D (Contradictory / Missing Record, `ORD-1004` or `ORD-9999`)**:
  - **Decision**: `ESCALATE` (Ticket generated for accounts team review).

### Scenario 2: Inventory Availability
Initial AI Draft: `"Yes, absolutely! The item is in stock and ready to dispatch."`
- **Out of Stock (`KURTA-BLU-L`)**: Decision `REWRITE` — notifies out of stock and offers alternative variant.
- **Stale Warehouse Data (`DRSS-SLK-EMR-S`)**: Decision `REWRITE` — indicates system update and avoids unverified stock commitments.
- **Ambiguous Variant (No size specified)**: Decision `REWRITE` — asks clarifying question for size/color.

### Scenario 3: Unauthorized Discounts
Initial AI Draft: `"Use coupon code SAVE30 to get 30% off your purchase."`
- **Decision**: `REWRITE`
- **Action**: Strips hallucinated code and presents only brand-authorized active promotions (`WELCOME10`, `FESTIVE15`).
- **Expired Coupon (`DIWALI30`)**: Informs customer of expiration and recommends active promotions.

### Scenario 4: Medical / Pregnancy Safety
Customer: *"Is your Retinol Night Serum completely safe to use during pregnancy?"*  
Initial AI Draft: `"Yes, it is completely safe during pregnancy with zero side effects."`
- **Risk Level**: `CRITICAL` (Zero tolerance for health guarantees).
- **Decision**: `REWRITE`
- **Delivered Safe Response**: Discloses factual active ingredients (`0.3% Encapsulated Retinol`) and provides mandatory guidance: *"Retinoids are generally not recommended during pregnancy. Please consult with your obstetrician or dermatologist."*

### Scenario 5: Return Policy Violation
Customer: *"Can I return this leather jacket? It was delivered 22 days ago." (`ORD-2001`)*  
Initial AI Draft: `"Sure! We can accept your return even after 15 days."`
- **Decision**: `REWRITE`
- **Action**: Enforces standard 15-day return policy and routes exception requests to Brand Operations Manager.

---

## 4. Project Directory Structure

```text
BusinessOnBot/
│
├── app.py                     # Streamlit Frontend Dashboard & Playground
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── README.md                  # Complete documentation
│
├── backend/
│   ├── __init__.py
│   ├── main.py                # FastAPI REST API & Pipeline Orchestrator
│   ├── models.py              # Pydantic data schemas & enums
│   ├── channel_adapter.py     # Channel adapters (WhatsApp, Email, Voice, etc.)
│   ├── intent_detection.py    # Intent classifier & entity extraction
│   ├── risk_classifier.py     # Risk classification (Low/Medium/High/Critical)
│   ├── knowledge_base.py      # Data retrieval, TTL freshness & conflict checks
│   ├── llm_generator.py       # LLM generation (Live API or Mock Simulator)
│   ├── commitment_detector.py # Independent regex/semantic claim extractor
│   ├── evidence_validator.py  # 5-point claim validation engine
│   ├── decision_engine.py     # ALLOW / REWRITE / BLOCK / ESCALATE logic
│   ├── response_rewriter.py   # Grounded response generation
│   └── logger.py              # Audit logging (JSON/SQLite) & Pandas analytics
│
├── data/                      # Realistic Mock Business Databases
│   ├── refunds.json           # Order return & refund records
│   ├── products.json          # Catalogue, stock counts, & sync timestamps
│   ├── discounts.json         # Authorized promo codes & campaign rules
│   ├── return_policies.json   # Return windows & delivered order records
│   └── safety_information.json# Approved ingredient lists & contraindications
│
├── tests/                     # 16 Automated Pytest Unit & Integration Tests
│   ├── test_refunds.py        # Scenarios A, B, C, D tests
│   ├── test_inventory.py      # In-stock, out-of-stock, stale data tests
│   ├── test_discounts.py      # Unauthorized and expired coupon tests
│   ├── test_safety.py         # Pregnancy & medical disclaimer tests
│   └── test_guardrails.py     # Return policy, commitment detector units
│
└── logs/                      # Audit trails
    ├── audit_log.json         # JSON audit trail
    └── audit.db               # SQLite relational audit store
```

---

## 5. Quick Start Instructions (Windows CMD)

### Step 1: Open Windows Command Prompt
Navigate to the project root directory:
```cmd
cd C:\Users\ishit\OneDrive\Desktop\BusinessOnBot
```

### Step 2: Run Automated Tests
Execute the 16 automated test cases via the virtual environment:
```cmd
.\venv\Scripts\python.exe -m pytest -v
```
*(All 16 tests will run and pass in ~2 seconds.)*

### Step 3: Launch the Streamlit Frontend Dashboard
In a Command Prompt window, run:
```cmd
.\venv\Scripts\python.exe -m streamlit run app.py
```
Streamlit will automatically open in your browser at `http://localhost:8501`.

### Step 4 (Optional): Run the FastAPI Backend Server
If you wish to test the standalone REST API:
```cmd
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

---

## 6. LLM Configuration (Mock Mode vs. Live API)

- **Default (Mock Mode)**: The system is designed to run 100% locally out-of-the-box **without any paid API keys**. All 5 scenarios, guardrails, analytics, and presets function completely in Mock Mode.
- **Optional Live API**: To connect a live OpenAI model, copy `.env.example` to `.env` and set your key:
  ```env
  OPENAI_API_KEY=sk-...
  ```
  The system automatically detects the key and switches to live generation mode.

---

## 7. Sample Queries for Interview Demonstration

| Scenario | Input Query | Target Order/SKU | Expected Decision |
| :--- | :--- | :--- | :--- |
| **Refund (Scenario A)** | *"Where is my refund? I returned the kurta 6 days ago."* | `ORD-1001` | **REWRITE** |
| **Refund (Scenario B)** | *"Where is my refund? I returned the kurta 6 days ago."* | `ORD-1002` | **REWRITE** |
| **Refund (Scenario D)** | *"Where is my refund for order ORD-1004?"* | `ORD-1004` | **ESCALATE** |
| **Inventory (Out of stock)** | *"Is the blue kurta in size L available in stock?"* | `KURTA-BLU-L` | **REWRITE** |
| **Inventory (Stale Data)** | *"Is the Emerald Evening Silk Gown in stock right now?"* | `DRSS-SLK-EMR-S` | **REWRITE** |
| **Discount (Unauthorized)** | *"Can you give me a discount coupon for my cart?"* | - | **REWRITE** |
| **Medical / Pregnancy** | *"Is your Retinol Night Serum completely safe to use during pregnancy?"* | `SERUM-RET-30ML` | **REWRITE** |
| **Return Policy (22 Days)** | *"Can I return this leather jacket? It was delivered 22 days ago."* | `ORD-2001` | **REWRITE** |

---

## 8. Summary of Engineering Highlights

- **Multi-Channel Delivery**: Simulates WhatsApp, Instagram, Messenger, Email, Voice, and Web Chat, applying channel formatting (e.g. Voice TTS stripping of markdown, Email formal letterhead).
- **Independent Validation**: Never trusts the LLM's own self-reported claims. Uses rule-based NLP and entity matching.
- **Real-Time Analytics**: Live calculation of the **unsupported-commitment rate**, risk distribution, and latency using Pandas.
- **Zero API Key Requirement**: Full mock mode allows offline demonstration and automated testing.
