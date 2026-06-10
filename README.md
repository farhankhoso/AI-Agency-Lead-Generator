# AI Agency Lead Generator

An AI-powered lead generation platform built with **Streamlit**, **Playwright**, and **Groq LLMs**.

The application automatically scrapes business listings from Google Maps, analyzes each lead using AI, scores their potential value, identifies business pain points, and generates personalized outreach messages ready for WhatsApp or Email campaigns.

---

## Features

### Google Maps Lead Scraping

* Search businesses directly from Google Maps
* Extract:

  * Business Name
  * Phone Number
  * Website
  * Address
  * Rating
  * Review Count
  * Category

### AI Lead Qualification

* AI-powered lead scoring (1-100)
* Business pain point analysis
* Service recommendation engine
* Opportunity assessment

### Automated Outreach Generation

* Personalized WhatsApp messages
* Personalized Email drafts
* AI-generated sales pitches
* Ready-to-send outreach content

### Lead Management

* Sort leads by AI score
* View detailed business insights
* Export results to CSV
* Interactive Streamlit dashboard

---

# Tech Stack

* Python
* Streamlit
* Playwright
* Groq API
* Pandas
* Python Dotenv

---

# Project Structure

```bash
AI-Agency-Lead-Generator/
│
├── app.py
├── requirements.txt
├── .env
├── README.md
└── assets/
```

---

# Installation

## 1. Clone Repository

```bash
git clone https://github.com/farhankhoso/AI-Agency-Lead-Generator.git

cd AI-Agency-Lead-Generator
```

## 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate:

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Install Playwright Browser

Playwright requires an additional browser installation:

```bash
playwright install chromium
```

---

# Configuration

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key
```

### Note

If no Groq API key is provided:

* Google Maps scraping will still work
* AI lead enrichment will be disabled
* Outreach generation will be unavailable

---

# Running the Application

```bash
streamlit run app.py
```

The application will launch locally in your browser.

---

# How It Works

## Step 1: Scrape Google Maps

The application uses Playwright to:

* Open Google Maps
* Search businesses by keyword
* Scroll through search results
* Visit individual listings
* Extract business information

Collected fields:

* Name
* Phone
* Website
* Address
* Rating
* Reviews
* Category

---

## Step 2: AI Lead Enrichment

Each lead is sent to a Groq-hosted LLM.

Default model:

```text
llama-3.3-70b-versatile
```

The AI returns:

```json
{
  "lead_score": 92,
  "pain_points": [
    "Weak online presence",
    "No appointment booking system"
  ],
  "best_service": "AI Chatbot",
  "whatsapp_message": "...",
  "email_message": "..."
}
```

---

## Step 3: Lead Dashboard

The Streamlit dashboard provides:

* Lead ranking
* AI scores
* Business insights
* Outreach templates
* CSV export

---

# Example Use Cases

### AI Agencies

Find businesses that could benefit from:

* AI Chatbots
* Lead Generation Systems
* CRM Automation
* Customer Support Automation

### Marketing Agencies

Identify businesses needing:

* Better websites
* SEO services
* Digital marketing

### Software Houses

Discover prospects for:

* Custom software
* Mobile applications
* Web development

---

# Exporting Leads

All enriched leads can be downloaded as:

```csv
CSV File
```

For further outreach and CRM integration.

---

# Disclaimer

This project is intended for educational and business prospecting purposes only.

Users are responsible for complying with:

* Google Maps Terms of Service
* Local privacy regulations
* Applicable outreach and marketing laws

---

# Future Improvements

* Multi-location scraping
* CRM integrations
* LinkedIn enrichment
* Email verification
* Bulk campaign export
* AI-powered lead clustering
* Automated follow-up generation

---

# Author

Farhan Ali
AI Engineer | Computer Vision Engineer | Automation Developer
Feel free to contribute, fork, or submit pull requests.
