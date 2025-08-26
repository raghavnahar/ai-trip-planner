import os
import re
import time
import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from rag import build_context_with_retrieval
import logging
logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
from huggingface_hub import InferenceClient
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from pdf_utils import create_pdf

load_dotenv()

st.set_page_config(page_title="AI Trip Planner", page_icon="🧭", layout="centered")

HF_TOKEN = os.getenv("HF_TOKEN") or st.secrets.get("HF_TOKEN") if hasattr(st, "secrets") else None
DEFAULT_MODEL = os.getenv("HF_MODEL_ID", "HuggingFaceH4/zephyr-7b-beta")

@st.cache_resource
def get_client(token: str | None):
    return InferenceClient(token=token)

client = get_client(HF_TOKEN)

st.title("🧭 AI Trip Planner — Free & Smart")
st.caption("✨ Build a realistic, budget-aware itinerary with fresh web context")
# Branding footer (animated hearts)
st.markdown(
    "<div style='text-align:center; font-size:14px; margin-top:6px;'>"
    "<span style='animation:pulse 1.2s infinite; color:#e25555;'>❤️</span> "
    "Created with care by <b>Raghav Nahar</b> — AI Consultant"
    "</div>"
    "<style>@keyframes pulse {0%{transform:scale(1)}50%{transform:scale(1.2)}100%{transform:scale(1)}}</style>",
    unsafe_allow_html=True,
)

@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="trip_planner_ui")

geocoder = get_geocoder()

def geocode_place(place: str):
    if not place:
        return None
    try:
        loc = geocoder.geocode(place, timeout=10)
        if loc:
            return (loc.latitude, loc.longitude, loc.address)
    except Exception:
        return None
    return None

def validate_dates(start, end):
    if start >= end:
        return "Start date must be before end date."
    if (end - start).days > 60:
        return "Please limit trip duration to 60 days."
    return None

with st.form("trip_form"):
    st.markdown("### 📝 Trip Details")
    c1, c2 = st.columns(2)
    with c1:
        source = st.text_input("🏁 Source city (start/end)*", placeholder="e.g., Delhi, India")
        destination = st.text_input("📍 Destination(s)*", placeholder="e.g., Paris, France or Paris, Lyon")
        start_date = st.date_input("📅 Start date*")
        end_date = st.date_input("📅 End date*")
        num_people = st.number_input("👥 Number of people*", min_value=1, value=2, step=1)
        age_group = st.selectbox("🧑‍🤝‍🧑 Average age group*", ["18–25", "25–35", "35–50", "50+", "Family with kids"]) 
    with c2:
        currency_choice = st.radio("💱 Show prices in", ["INR", "USD", "Both"], index=2)
        budget = st.number_input("💰 Total budget (optional)", min_value=0, value=0, step=10000)
        travel_style = st.radio("🚗 Travel style (if no budget)", ["Budget-friendly", "Moderate", "Lavish"], index=1)
        accommodation_type = st.multiselect("🏨 Accommodation type", ["Hotel", "Hostel", "Apartment", "Resort", "Homestay"]) 
        accommodation_style = st.selectbox("🎯 Accommodation style", ["Budget", "Mid-range", "Luxury", "Boutique", "Family-friendly"]) 
    interests = st.multiselect("🎡 Interests", [
        "History & Culture", "Adventure", "Food & Wine", "Nature & Wildlife",
        "Shopping", "Nightlife", "Relaxation", "Photography"
    ])
    preferences = st.text_area("🧾 Specific preferences (dietary, must-see, pace, mobility, etc.)")
    c3, c4 = st.columns(2)
    with c3:
        internet_required = st.checkbox("🌐 Internet required", value=True)
        sim_card_required = st.checkbox("📶 Local SIM/eSIM required", value=True)
    with c4:
        travel_insurance = st.checkbox("🛡️ Travel insurance", value=True)
        special_assistance = st.checkbox("♿ Special assistance", value=False)
    submitted = st.form_submit_button("✨ Generate Itinerary")


def ddg_search(query: str, max_results: int = 6):
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []


def fetch_page_text(url: str, max_chars: int = 3500) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(" ")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


def build_web_context(query: str, top_k: int = 3) -> str:
    results = ddg_search(query, max_results=8)
    blocks = []
    count = 0
    for res in results:
        if count >= top_k:
            break
        url = res.get("href") or res.get("link") or ""
        title = res.get("title") or "Source"
        snippet = res.get("body") or ""
        body = fetch_page_text(url) if url else ""
        if body or snippet:
            count += 1
            blocks.append(f"---\nTitle: {title}\nURL: {url}\nSnippet: {snippet}\nExtract: {body}\n")
        time.sleep(0.4)
    return "\n".join(blocks)

MAX_NEW_TOKENS = 1500
TEMPERATURE = 0.9

def generate_text(model_id: str, prompt: str, max_new_tokens: int, temperature: float) -> str:
    # First try text generation; if unsupported, fall back to chat completion
    try:
        return client.text_generation(
            model='google/gemma-2-9b-it',
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=0.9,
        )
    except Exception:
        # Try chat completion format
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
            out = client.chat_completion(
                model='google/gemma-2-9b-it',
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=temperature,
                top_p=0.9,
            )
            # Normalize different return shapes
            choices = getattr(out, "choices", None)
            if choices and len(choices) > 0:
                msg = getattr(choices[0], "message", None)
                if msg is not None:
                    content = getattr(msg, "content", None)
                    if isinstance(content, str):
                        return content
            if isinstance(out, dict):
                ch = out.get("choices") or []
                if ch:
                    content = (ch[0].get("message") or {}).get("content")
                    if isinstance(content, str):
                        return content
            return str(out)
        except Exception as e2:
            raise e2

model_id = 'google/gemma-2-9b-it'

REQUIRED_SECTIONS = [
    "# Trip Overview",
    "# Transport Plan",
    "# Stay Options",
    "# Day-by-Day Itinerary",
    "# Must-Try Food",
    "# Tickets & Pre-bookings",
    "# Packing & Prep Checklist",
    "# Estimated Costs",
    "# Planner’s Recommendation",
]

def _missing_sections(text: str) -> list[str]:
    lower_text = text.lower()
    missing = []
    aliases = {
        "# Trip Overview": ["# trip overview"],
        "# Transport Plan": ["# transport plan"],
        "# Stay Options": ["# stay options"],
        "# Day-by-Day Itinerary": ["# day-by-day itinerary", "# day by day itinerary"],
        "# Must-Try Food": ["# must-try food", "# must try food", "# food"],
        "# Tickets & Pre-bookings": ["# tickets & pre-bookings", "# tickets and pre-bookings", "# tickets"],
        "# Packing & Prep Checklist": ["# packing & prep checklist", "# packing checklist"],
        "# Estimated Costs": ["# estimated costs", "# costs"],
        "# Planner’s Recommendation": ["# planner’s recommendation", "# planners recommendation", "# planner recommendation"],
    }
    for section, keys in aliases.items():
        if not any(k in lower_text for k in keys):
            missing.append(section)
    return missing

def generate_full_itinerary(model_id: str, base_prompt: str) -> str:
    parts: list[str] = []
    # First pass
    first = generate_text(model_id, base_prompt, MAX_NEW_TOKENS, TEMPERATURE)
    parts.append(first if isinstance(first, str) else str(first))
    miss = _missing_sections(parts[0])
    logging.info("Initial output length=%d, missing sections=%s", len(parts[0]), ", ".join(miss))
    # Up to two continuations
    for _ in range(2):
        if not miss:
            break
        # Provide recent context so the model can continue seamlessly
        so_far = "\n\n".join(parts)
        tail = so_far[-4000:]  # include last chunk of text as context
        cont_prompt = (
            "You are continuing an itinerary in Markdown. Below is the content generated so far.\n\n"
            f"EXISTING ITINERARY (partial):\n{tail}\n\n"
            "Continue by writing ONLY the remaining sections with the same headings and formatting.\n"
            f"Sections still missing: {', '.join(miss)}\n"
            "Do not ask the user for the existing text; continue directly.\n"
            "Do not repeat any sections already covered."
        )
        cont = generate_text(model_id, cont_prompt, MAX_NEW_TOKENS, TEMPERATURE)
        cont_str = cont if isinstance(cont, str) else str(cont)
        parts.append(cont_str)
        miss = _missing_sections("\n\n".join(parts))
        logging.info("Continuation length=%d, still missing=%s", len(cont_str), ", ".join(miss))
    return "\n\n".join(parts)
if submitted:
    if not source or not destination.strip():
        st.error("Please enter both source and destination(s).")
        st.stop()
    date_err = validate_dates(start_date, end_date)
    if date_err:
        st.error(date_err)
        st.stop()
    destinations = [d.strip() for d in destination.split(',') if d.strip()]
    if not destinations:
        st.error("Please provide at least one valid destination.")
        st.stop()
    # Geocode validation
    src_geo = geocode_place(source)
    if not src_geo:
        st.error(f"Could not locate source: {source}. Please check spelling.")
        st.stop()
    dest_geos = []
    invalid_dests = []
    for d in destinations:
        g = geocode_place(d)
        if g:
            dest_geos.append(g)
        else:
            invalid_dests.append(d)
    if invalid_dests:
        st.error(f"Could not locate: {', '.join(invalid_dests)}. Please correct them.")
        st.stop()
    # Feasibility advisory
    days = (end_date - start_date).days
    try:
        distance_km = geodesic((src_geo[0], src_geo[1]), (dest_geos[0][0], dest_geos[0][1])).km
    except Exception:
        distance_km = None
    feas_note = None
    if distance_km is not None:
        if distance_km > 1500 and days < 3:
            feas_note = f"Very short for intercontinental distance (~{int(distance_km)} km). Consider 3–5 days."
        elif 500 < distance_km <= 1500 and days < 2:
            feas_note = f"Trip distance is ~{int(distance_km)} km; consider at least 2–3 days."
    if feas_note:
        st.warning(f"Feasibility note: {feas_note}")

    # Build research context
    composed_context = ""
    with st.spinner("🔎 Gathering fresh web context..."):
        blocks = []
        for d in destinations:
            q = f"{d} travel guide attractions tickets opening hours prices neighborhoods best time local food safety"
            blocks.append(f"## {d}\n" + build_context_with_retrieval(q, k=6))
        composed_context = "\n\n".join(blocks)
    logging.info("Context length: %d for destinations: %s", len(composed_context), ", ".join(destinations))

    # Build prompt
    currency_directive = currency_choice
    budget_line = f"Approximate budget: {budget} {currency_choice if currency_choice != 'Both' else 'INR & USD'}" if budget and budget > 0 else f"Travel style: {travel_style or 'Moderate'}"

    user_input = {
        "source": source,
        "destination": ", ".join(destinations),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "num_people": num_people,
        "age_group": age_group,
        "budget": budget,
        "currency": currency_choice,
        "travel_style": travel_style,
        "interests": interests,
        "preferences": preferences,
        "accommodation_type": accommodation_type,
        "accommodation_style": accommodation_style,
        "internet_required": internet_required,
        "sim_card_required": sim_card_required,
        "travel_insurance": travel_insurance,
        "special_assistance": special_assistance,
        "duration": (end_date - start_date).days,
    }
    prompt = f"""
You are an expert travel planner with deep knowledge of global destinations. Create a highly detailed, practical, and personalized travel itinerary based on the user's inputs and the current information provided.

USER INPUTS
- Source: {user_input['source']}
- Destination(s): {user_input['destination']}
- Dates: {user_input['start_date']} to {user_input['end_date']} (days: {days})
- People: {user_input['num_people']}
- Average age: {user_input['age_group']}
- {budget_line}
- Interests: {', '.join(user_input['interests']) if user_input['interests'] else 'General sightseeing'}
- Specific preferences: {user_input['preferences'] or 'None'}
- Accommodation: {', '.join(user_input['accommodation_type']) if user_input['accommodation_type'] else 'Any'} — {user_input['accommodation_style']}
- Connectivity: Internet={user_input['internet_required']}, SIM/eSIM={user_input['sim_card_required']}
- Insurance: {user_input['travel_insurance']}, Special assistance: {user_input['special_assistance']}
- Currency display: {currency_directive}

RESEARCH (recent web snippets; may be partial)
{composed_context}

REQUIREMENTS
- Plan end-to-end Source → Destination(s) → Source respecting dates and realistic transfers.
- Include transport per leg with sample timings and fare ranges in {currency_directive}; suggest booking sites/passes.
- Stays: 2–3 options per destination across budget tiers (budget, mid, premium) with neighborhoods and typical nightly prices.
- Must-visit places, sightseeing, leisure activities, authentic local food and specialties.
- Tickets & pre-bookings: explicitly list items needing reservations or timed entry with indicative prices.
- Packing & prep: travel gear, eSIM/SIM/connectivity, local transport apps, important contacts, nearest airports/railway stations.
- Costs: itemized rough estimate per day and final total (show in INR and USD or both per selection).
- If the trip seems too short for distances, add a concise "Planner’s recommendation" suggesting more sensible time.
- If they have more than enough time, suggest nearby places to visit.
- Include important links: transport booking sites, emergency contacts, and any pre-booking pages.
- If local SIMs may not work at destination, suggest reliable eSIM or connectivity options.

FORMAT (Markdown)
# Trip Overview
# Transport Plan (with timings and sample fares)
# Stay Options (by destination and budget tier)
# Day-by-Day Itinerary (dates; morning/afternoon/evening)
# Must-Try Food & Specialties
# Tickets & Pre-bookings
# Packing & Prep Checklist
# Estimated Costs (daily + final total in requested currencies)
# Planner’s Recommendation (only if applicable)
"""

    with st.spinner("🧩 Assembling your itinerary..."):
        try:
            text = generate_full_itinerary(model_id, prompt)
        except Exception as e:
            st.error(f"Model call failed: {e}")
            st.stop()
    st.subheader("🗺️ Itinerary")
    text_str = text if isinstance(text, str) else str(text)
    st.markdown(text_str)
    # Download options
    st.download_button(
        "⬇️ Download as PDF",
        data=create_pdf(text_str, user_input),
        file_name="itinerary.pdf",
        mime="application/pdf",
    )


