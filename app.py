import asyncio
import sys
import streamlit as st
import pandas as pd
import json
import time
import re
import os
from openai import OpenAI
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

if sys.platform == "win32" and not getattr(asyncio.proactor_events._ProactorBasePipeTransport, "_patched", False):
    import asyncio.proactor_events
    _orig_call_connection_lost = asyncio.proactor_events._ProactorBasePipeTransport._call_connection_lost

    def _patched_call_connection_lost(self, exc):
        try:
            _orig_call_connection_lost(self, exc)
        except ConnectionResetError:
            pass

    _patched_call_connection_lost._patched = True
    asyncio.proactor_events._ProactorBasePipeTransport._call_connection_lost = _patched_call_connection_lost
    asyncio.proactor_events._ProactorBasePipeTransport._patched = True

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY", "")

# ── Agency services (used in AI prompt) ───────────────────────────────────────
AGENCY_SERVICES = """
Our agency offers the following services:
1. AI & Machine Learning Solutions — chatbots, recommendation engines, predictive analytics
2. Computer Vision — product inspection, AI security cameras, people counting, shelf monitoring, face recognition
3. Web Development — business websites, ecommerce stores, booking systems, dashboards
4. Mobile App Development — iOS/Android apps
5. Custom Software Development — ERP, inventory management, POS systems, automation
6. Digital Marketing & SEO — social media, Google Ads, content marketing
7. Process Automation (RPA) — automating repetitive business tasks
"""

# Industry → best services to pitch
INDUSTRY_SERVICE_MAP = {
    "restaurant": ["Website", "Online Ordering System", "AI Chatbot for reservations", "Digital Marketing"],
    "retail":     ["Inventory Management Software", "Computer Vision for shelf monitoring", "POS System", "Ecommerce Store"],
    "factory":    ["Computer Vision for quality inspection", "Process Automation", "ERP System", "Predictive Maintenance AI"],
    "hospital":   ["Hospital Management Software", "AI Diagnosis Assistant", "Patient Booking System"],
    "school":     ["School Management System", "E-learning Platform", "Attendance Automation"],
    "real estate":["Property Listing Website", "Virtual Tour", "CRM Software", "AI Lead Scoring"],
    "security":   ["AI CCTV / Computer Vision", "Face Recognition System", "Intrusion Detection AI"],
    "logistics":  ["Fleet Tracking Software", "Route Optimization AI", "Warehouse Management System"],
    "hotel":      ["Hotel Booking System", "AI Chatbot", "Digital Marketing", "Review Management"],
    "gym":        ["Membership Management App", "AI Personal Trainer Chatbot", "Website + Booking"],
    "pharmacy":   ["Inventory & POS System", "Online Ordering", "Prescription Management Software"],
}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agency Lead Generator",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<h1 style='font-size:2rem; font-weight:bold;'>
    🎯 AI Agency Lead Generator
</h1>
<p style='color:gray; margin-top:-10px;'>
    Find businesses that need <b>AI · Computer Vision · Web · Software</b> solutions — scrape Google Maps → analyze → get outreach messages ready
</p>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    groq_model = st.selectbox(
        "Groq Model",
        ["llama-3.3-70b-versatile", "llama3-8b-8192", "llama-3.1-8b-instant", "gemma2-9b-it"],
        index=0
    )

    max_results = st.slider("Max leads to scrape", 5, 50, 10)
    enrich_leads = st.toggle("AI Enrichment (scoring + messages)", value=True)

    st.divider()
    st.header("🏢 Quick Target Industries")
    st.caption("Click to auto-fill search")

    quick_searches = [
        "restaurants Karachi",
        "factories Karachi",
        "retail shops Lahore",
        "hospitals Islamabad",
        "schools Karachi",
        "hotels Karachi",
        "gyms Lahore",
        "pharmacies Karachi",
        "real estate agencies Karachi",
        "security companies Lahore",
    ]
    for qs in quick_searches:
        if st.button(qs, use_container_width=True, key=f"btn_{qs}"):
            st.session_state["prefill_query"] = qs

    st.divider()
    st.header("ℹ️ How to Use")
    st.markdown("""
1. Type a search (e.g. *factories Karachi*)
2. Click **Generate Leads**
3. Get scored leads + ready-to-send WhatsApp & email messages
4. Download CSV
""")
    st.caption("💡 Tip: `[business type] [city]` works best")


# ── Groq client ────────────────────────────────────────────────────────────────
def get_groq_client():
    return OpenAI(
        api_key=groq_api_key,
        base_url="https://api.groq.com/openai/v1"
    )


# ── Industry detection ─────────────────────────────────────────────────────────
def detect_industry(name: str, category: str) -> str:
    text = (name + " " + category).lower()
    for industry in INDUSTRY_SERVICE_MAP:
        if industry in text:
            return industry
    return "general"

def get_suggested_services(industry: str) -> list:
    return INDUSTRY_SERVICE_MAP.get(industry, [
        "Custom Software Development",
        "Business Website",
        "AI Automation",
        "Digital Marketing"
    ])


# ── Google Maps Scraper ────────────────────────────────────────────────────────
def scrape_google_maps(query: str, max_results: int = 10):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="en-US",
        )
        page = context.new_page()

        try:
            search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector('[role="feed"]', timeout=30000)
            page.wait_for_timeout(2000)

            scrollable = page.locator('[role="feed"]')
            last_count = 0
            scroll_attempts = 0

            while len(results) < max_results and scroll_attempts < 10:
                listings = page.locator('[role="feed"] > div > div > a').all()

                if len(listings) == last_count:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                    last_count = len(listings)

                for listing in listings[len(results):]:
                    if len(results) >= max_results:
                        break
                    try:
                        name = listing.get_attribute("aria-label") or ""
                        href = listing.get_attribute("href") or ""
                        if name and href:
                            results.append({"name": name, "maps_url": href})
                    except Exception:
                        continue

                try:
                    scrollable.evaluate("el => el.scrollBy(0, 1000)")
                    page.wait_for_timeout(1500)
                except Exception:
                    break

            # Get details for each listing
            detailed = []
            for i, lead in enumerate(results[:max_results]):
                try:
                    page.goto(lead["maps_url"], wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2000)

                    # Phone
                    phone = ""
                    try:
                        phone_el = page.locator('[data-item-id*="phone"]').first
                        phone = phone_el.get_attribute("data-item-id", timeout=3000) or ""
                        phone = phone.replace("phone:", "").strip()
                    except Exception:
                        pass

                    # Address
                    address = ""
                    try:
                        addr_el = page.locator('[data-item-id="address"]').first
                        address = addr_el.inner_text(timeout=3000).strip()
                    except Exception:
                        pass

                    # Website
                    website = ""
                    try:
                        web_el = page.locator('a[data-item-id="authority"]').first
                        website = web_el.get_attribute("href", timeout=3000) or ""
                    except Exception:
                        pass

                    # Rating — multiple selectors for reliability
                    rating = ""
                    rating_selectors = [
                        'div[jslog] span[aria-hidden="true"]',
                        'span.ceNzKf[aria-hidden="true"]',
                        'span[aria-label*="stars"]',
                        'div.F7nice span[aria-hidden="true"]',
                    ]
                    for sel in rating_selectors:
                        try:
                            val = page.locator(sel).first.inner_text(timeout=1500).strip()
                            if re.match(r'^\d\.?\d?$', val):
                                rating = val
                                break
                        except Exception:
                            continue

                    # Reviews count — multiple selectors
                    reviews = ""
                    review_selectors = [
                        'span[aria-label*="review"]',
                        'span[aria-label*="reviews"]',
                        'div.F7nice span[aria-label]',
                    ]
                    for sel in review_selectors:
                        try:
                            val = page.locator(sel).first.get_attribute("aria-label", timeout=1500) or ""
                            cleaned = re.sub(r'[^\d,]', '', val).strip(",")
                            if cleaned:
                                reviews = cleaned
                                break
                        except Exception:
                            continue

                    # Category
                    category = ""
                    try:
                        cat_el = page.locator('button[jsaction*="category"]').first
                        category = cat_el.inner_text(timeout=2000).strip()
                    except Exception:
                        pass

                    detailed.append({
                        "name": lead["name"],
                        "category": category,
                        "phone": phone,
                        "address": address,
                        "website": website,
                        "rating": rating,
                        "reviews": reviews,
                        "maps_url": lead["maps_url"],
                    })

                except Exception as e:
                    detailed.append({
                        "name": lead["name"],
                        "category": "",
                        "phone": "",
                        "address": "",
                        "website": "",
                        "rating": "",
                        "reviews": "",
                        "maps_url": lead["maps_url"],
                    })

            browser.close()
            return detailed

        except Exception as e:
            browser.close()
            st.error(f"Scraping error: {e}")
            return []


# ── AI Enrichment — Agency-focused prompt ─────────────────────────────────────
def enrich_with_groq(leads: list, search_query: str):
    if not groq_api_key:
        st.error("Groq API key is required for enrichment")
        return leads

    client = get_groq_client()
    enriched = []
    progress = st.progress(0)
    status = st.empty()

    for i, lead in enumerate(leads):
        status.text(f"🤖 Analyzing {i+1}/{len(leads)}: {lead['name']}...")
        progress.progress((i + 1) / len(leads))

        industry = detect_industry(lead.get("name", ""), lead.get("category", ""))
        suggested_services = get_suggested_services(industry)
        has_website = bool(lead.get("website"))
        rating = lead.get("rating") or "unknown"
        reviews = lead.get("reviews") or "0"

        prompt = f"""You are a senior business development manager at a tech agency in Pakistan.

{AGENCY_SERVICES}

You are analyzing a potential client lead to decide:
1. How badly do they need our services?
2. Which specific service is the best fit?
3. How to approach them with outreach messages?

LEAD INFORMATION:
- Business Name: {lead.get('name', 'N/A')}
- Category: {lead.get('category', 'N/A')}
- Location: {lead.get('address', 'N/A')}
- Phone: {lead.get('phone', 'N/A')}
- Website: {"YES — " + lead.get('website') if has_website else "NO WEBSITE (big gap!)"}
- Google Rating: {rating}/5
- Number of Reviews: {reviews}
- Search Context: "{search_query}"
- Detected Industry: {industry}
- Likely needed services: {", ".join(suggested_services)}

SCORING RULES (be strict and realistic):
- No website = +30 points (huge opportunity)
- Rating below 3.5 = +20 points (needs digital help)
- Under 20 reviews = +15 points (low online presence)
- Industry heavily benefits from AI/CV (factory, retail, security, hospital) = +20 points
- Already has good website + high rating = lower score

Return ONLY a valid JSON object with these exact keys:

{{
  "score": <integer 1-100>,
  "potential": <"High" | "Medium" | "Low">,
  "urgency": <"Urgent" | "Normal" | "Low">,
  "pain_points": <string, 2-3 specific pain points this business likely has>,
  "best_service_to_pitch": <string, single best service from our list>,
  "why_they_need_it": <string, 1-2 sentences why this specific business needs that service>,
  "outreach_channel": <"WhatsApp" | "Email" | "Call" | "Visit">,
  "whatsapp_message": <string, short casual WhatsApp message, 3-4 sentences, mention their business name, the problem you noticed, what you offer. Sound human not salesy>,
  "email_subject": <string, catchy cold email subject line>,
  "email_body": <string, professional cold email, 4-5 sentences, personalized, end with soft CTA>
}}

No markdown fences. No extra text. Just the JSON."""

        try:
            response = client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": "You are a business development expert. Return ONLY valid JSON. No markdown, no explanation, just the JSON object."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=700
            )

            result = response.choices[0].message.content.strip()
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]

            ai_data = json.loads(result)
            enriched.append({**lead, **ai_data})

        except json.JSONDecodeError as e:
            st.warning(f"Lead #{i+1} ({lead['name']}): AI returned invalid JSON — {e}")
            enriched.append({
                **lead,
                "score": 50, "potential": "Medium", "urgency": "Normal",
                "pain_points": "Could not analyze",
                "best_service_to_pitch": suggested_services[0],
                "why_they_need_it": "Needs further analysis",
                "outreach_channel": "WhatsApp",
                "whatsapp_message": "", "email_subject": "", "email_body": ""
            })
        except Exception as e:
            st.warning(f"Lead #{i+1} ({lead['name']}): Groq API error — {e}")
            enriched.append({
                **lead,
                "score": 50, "potential": "Medium", "urgency": "Normal",
                "pain_points": "Could not analyze",
                "best_service_to_pitch": suggested_services[0],
                "why_they_need_it": "Needs further analysis",
                "outreach_channel": "WhatsApp",
                "whatsapp_message": "", "email_subject": "", "email_body": ""
            })

        time.sleep(0.5)

    progress.empty()
    status.empty()
    return enriched


# ── Display Results ────────────────────────────────────────────────────────────
def display_leads(leads: list, enriched: bool):
    if not leads:
        st.warning("No leads found. Try a different search query.")
        return

    if enriched and "score" in leads[0]:
        leads = sorted(leads, key=lambda x: x.get("score", 0), reverse=True)

    st.success(f"✅ Found **{len(leads)}** leads")

    # Summary stats
    if enriched:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🔥 High Potential", sum(1 for l in leads if l.get("potential") == "High"))
        c2.metric("🟡 Medium",         sum(1 for l in leads if l.get("potential") == "Medium"))
        c3.metric("🔵 Low",            sum(1 for l in leads if l.get("potential") == "Low"))
        c4.metric("🌐 No Website",     sum(1 for l in leads if not l.get("website")))
        c5.metric("⚡ Urgent",         sum(1 for l in leads if l.get("urgency") == "Urgent"))

    st.divider()

    for i, lead in enumerate(leads):
        score     = lead.get("score", 0)
        potential = lead.get("potential", "")
        urgency   = lead.get("urgency", "")

        pot_icon   = {"High": "🔥", "Medium": "🟡", "Low": "🔵"}.get(potential, "")
        urg_tag    = " ⚡ URGENT" if urgency == "Urgent" else ""
        score_color = "green" if score >= 70 else ("orange" if score >= 40 else "red")

        label = f"{pot_icon} #{i+1}  {lead.get('name', 'N/A')}  ·  {lead.get('category', '')}  {urg_tag}"

        with st.expander(label, expanded=(i < 2)):
            col1, col2 = st.columns([1, 1])

            # ── Left: business info + what to pitch ───────────────────────────
            with col1:
                st.markdown("#### 📋 Business Info")
                if enriched:
                    st.markdown(
                        f"**Lead Score:** <span style='color:{score_color}; font-size:1.4rem'>{score}/100</span>  &nbsp; {pot_icon} {potential}",
                        unsafe_allow_html=True
                    )
                if lead.get("phone"):
                    st.markdown(f"📞 **Phone:** `{lead['phone']}`")
                if lead.get("address"):
                    st.markdown(f"📍 **Address:** {lead['address']}")
                if lead.get("website"):
                    st.markdown(f"🌐 **Website:** [Visit]({lead['website']})")
                else:
                    st.markdown("🌐 **Website:** ❌ None — big opportunity!")
                if lead.get("rating"):
                    st.markdown(f"⭐ **Rating:** {lead['rating']}/5  ({lead.get('reviews', '?')} reviews)")
                st.markdown(f"[📍 Open in Google Maps]({lead.get('maps_url', '#')})")

                if enriched:
                    st.divider()
                    st.markdown("#### 🎯 What to Pitch")
                    st.success(f"**{lead.get('best_service_to_pitch', 'N/A')}**")
                    st.markdown(f"*{lead.get('why_they_need_it', '')}*")
                    if lead.get("pain_points"):
                        st.markdown(f"**Pain points:** {lead['pain_points']}")
                    st.markdown(f"**Best channel:** {lead.get('outreach_channel', 'WhatsApp')}")

            # ── Right: ready-to-send messages ─────────────────────────────────
            with col2:
                if enriched:
                    st.markdown("#### 💬 Ready-to-Send Messages")

                    tab1, tab2 = st.tabs(["📱 WhatsApp", "📧 Email"])

                    with tab1:
                        wa_msg = lead.get("whatsapp_message", "")
                        if wa_msg:
                            st.text_area(
                                "Copy & paste to WhatsApp",
                                value=wa_msg,
                                height=180,
                                key=f"wa_{i}",
                                label_visibility="collapsed"
                            )
                        else:
                            st.info("No WhatsApp message generated")

                    with tab2:
                        email_subj = lead.get("email_subject", "")
                        email_body = lead.get("email_body", "")
                        if email_subj:
                            st.markdown(f"**Subject:** `{email_subj}`")
                            st.text_area(
                                "Email body",
                                value=email_body,
                                height=180,
                                key=f"email_{i}",
                                label_visibility="collapsed"
                            )
                        else:
                            st.info("No email generated")

    # Download CSV
    st.divider()
    df  = pd.DataFrame(leads)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download All Leads as CSV",
        data=csv,
        file_name=f"leads_{int(time.time())}.csv",
        mime="text/csv",
        use_container_width=True
    )


# ── Main ───────────────────────────────────────────────────────────────────────
default_query = st.session_state.pop("prefill_query", "")

col1, col2 = st.columns([3, 1])
with col1:
    search_query = st.text_input(
        "Search",
        value=default_query,
        placeholder="e.g.  factories Karachi  |  restaurants Lahore  |  retail shops Islamabad",
        label_visibility="collapsed"
    )
with col2:
    run = st.button("🚀 Generate Leads", use_container_width=True, type="primary")

st.caption("💡 Best for AI/Software agency: `factories Karachi` · `hospitals Lahore` · `retail shops Karachi` · `security companies Islamabad`")

if run:
    if not search_query:
        st.error("Please enter a search query")
    elif enrich_leads and not groq_api_key:
        st.error("GROQ_API_KEY not found in .env — add it and restart")
    else:
        with st.spinner(f"🗺️ Scraping Google Maps: **{search_query}**..."):
            leads = scrape_google_maps(search_query, max_results)

        if leads:
            if enrich_leads:
                st.info(f"✅ Scraped {len(leads)} businesses. Enriching with Groq AI...")
                leads = enrich_with_groq(leads, search_query)

            st.session_state["leads"]   = leads
            st.session_state["enriched"] = enrich_leads

if "leads" in st.session_state:
    display_leads(st.session_state["leads"], st.session_state.get("enriched", False))