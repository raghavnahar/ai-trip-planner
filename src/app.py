import streamlit as st
import sys
import os

# Add the parent directory to sys.path so Python can find 'utils'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from search import WebSearch
from knowledge_processor import KnowledgeProcessor
from ai_integration import ItineraryGenerator
from utils.pdf_generator import create_pdf
from utils.caching import cache_itinerary, get_cached_itinerary

import logging
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize components
search_tool = WebSearch()
knowledge_processor = KnowledgeProcessor()
itinerary_generator = ItineraryGenerator()

# Initialize session state variables
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = None
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'destination_info' not in st.session_state:
    st.session_state.destination_info = None
if 'knowledge_processed' not in st.session_state:
    st.session_state.knowledge_processed = False
if 'user_input' not in st.session_state:
    st.session_state.user_input = {}
if 'generation_start_time' not in st.session_state:
    st.session_state.generation_start_time = None

# App configuration
st.set_page_config(
    page_title="✈️ AI Trip Planner Pro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Create a placeholder for the preloader
preloader = st.empty()

# Inject custom CSS and show styled preloader inside the placeholder
with preloader.container():
    st.markdown("""
        <style>
        .centered-spinner {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 80vh;
            font-family: 'Segoe UI', sans-serif;
            font-size: 2rem;
            color: #2c3e50;
            font-weight: 600;
            animation: fadeIn 1s ease-in-out;
        }
        @keyframes fadeIn {
            from {opacity: 0;}
            to {opacity: 1;}
        }
        </style>
        <div class='centered-spinner'>🚀 Launching your AI Trip Planner Pro...</div>
    """, unsafe_allow_html=True)

    with st.spinner("Initializing the app..."):
        time.sleep(2)

# Clear the preloader
preloader.empty()
# preloader code ends here 

# main code begin here 
# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2e75b6;
        border-bottom: 2px solid #2e75b6;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
    }
    .success-box {
        background-color: #dff0d8;
        border: 1px solid #d6e9c6;
        border-radius: 4px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .info-box {
        background-color: #d9edf7;
        border: 1px solid #bce8f1;
        border-radius: 4px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .stProgress > div > div > div > div {
        background-color: #2e75b6;
    }
    .download-btn {
        background-color: #2e75b6;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
        margin-top: 10px;
    }
    .download-btn:hover {
        background-color: #1f4e79;
    }
</style>
""", unsafe_allow_html=True)

# App title and description
st.markdown('<h1 class="main-header">✈️ AI Trip Planner Pro</h1>', unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; margin-bottom: 2rem;'>
    Craft your perfect itinerary with AI-powered travel planning enhanced with real-time information!
</div>
""", unsafe_allow_html=True)

# Sidebar for information and controls
with st.sidebar:
    # Inject custom CSS for welcome message
    st.markdown("""
        <style>
        .welcome-box {
            background-color: #f0f8ff;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-family: 'Segoe UI', sans-serif;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            animation: fadeIn 1s ease-in-out;
        }
        .welcome-box h3 {
            margin: 0;
            font-size: 1.4rem;
            color: #1f77b4;
            font-weight: 700;
        }
        .welcome-box p {
            margin-top: 5px;
            font-size: 1rem;
            color: #555;
        }
        @keyframes fadeIn {
            from {opacity: 0;}
            to {opacity: 1;}
        }
        </style>
        <div class='welcome-box'>
            <h3>Welcome to Raghav's AI Trip Planner</h3>
            <p>Plan your dream trip with ease and intelligence ✈️</p>
        </div>
    """, unsafe_allow_html=True)

    # Existing sidebar content
    st.markdown("### About This App")
    st.markdown("""
    <div class='info-box'>
    This app uses AI enhanced with RAG (Retrieval-Augmented Generation) 
    to create personalized travel itineraries with up-to-date information.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### How It Works")
    steps = [
        "1. Enter your travel preferences",
        "2. We search for current information",
        "3. AI creates your perfect itinerary",
        "4. Download and enjoy your trip!"
    ]
    for step in steps:
        st.markdown(f"📌 {step}")

    st.markdown("---")
    st.markdown("""
    <div style='background-color: #fcf8e3; border-left: 4px solid #f0ad4e; padding: 10px;'>
    <strong>Disclaimer:</strong> This itinerary is generated by an AI. 
    While we use real-time information, please verify details before your trip.
    </div>
    """, unsafe_allow_html=True)

    
    # # Show app status
    # st.markdown("---")
    # st.markdown("### App Status")
    # if st.session_state.generation_start_time:
    #     elapsed = time.time() - st.session_state.generation_start_time
    #     st.metric("Generation Time", f"{elapsed:.1f} seconds")
    
    # # Debug info (collapsible)
    # with st.expander("Debug Information"):
    #     if st.session_state.user_input:
    #         st.json(st.session_state.user_input)
    #     st.write("Session state keys:", list(st.session_state.keys()))

# User input form
with st.form("travel_form"):
    st.markdown('<div class="sub-header">Trip Details</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        source = st.text_input("Source City*", placeholder="e.g., Delhi, India", 
                              help="Your starting point for the journey")
        destination = st.text_input("Destination(s)*", placeholder="e.g., Paris, France",
                                  help="Where you want to travel to")
        start_date = st.date_input("Start Date*", 
                                  help="When your trip begins")
        end_date = st.date_input("End Date*", 
                                help="When your trip ends")
        num_people = st.number_input("Number of People*", min_value=1, value=1, step=1,
                                    help="How many people are traveling")
        
    with col2:
        age_group = st.selectbox("Average Age Group*", 
                               ["Solo Traveler", "18-25", "25-35", "35-50", "50+", "Family with Kids"],
                               help="Age range of travelers")
        
        budget = st.number_input("Total Budget (optional)", min_value=0, value=0, step=100,
                                help="Your total budget for the trip")
        currency = st.selectbox("Currency", ["USD", "INR", "EUR", "GBP"],
                               help="Preferred currency for cost estimates")
        
        if budget == 0:
            travel_style = st.radio("How do you prefer to travel?", 
                                  ("Budget-Friendly", "Moderate", "Lavish"),
                                  help="Your travel style preference")
        else:
            travel_style = f"Custom budget: {budget}"
            
        interests = st.multiselect("Interests (select all that apply)", 
                                 ["History & Culture", "Adventure & Sports", "Food & Wine", 
                                  "Nature & Wildlife", "Shopping", "Nightlife", "Relaxation"],
                                 help="Your interests to personalize the itinerary")
    
    # New fields for accommodation preferences
    st.markdown('<div class="sub-header">Accommodation Preferences</div>', unsafe_allow_html=True)
    acc_col1, acc_col2 = st.columns(2)
    with acc_col1:
        accommodation_type = st.multiselect("Preferred accommodation types",
                                          ["Hotel", "Hostel", "Apartment Rental", "Resort", "Homestay"],
                                          help="Types of accommodation you prefer")
    with acc_col2:
        accommodation_style = st.selectbox("Accommodation style",
                                         ["Any", "Budget", "Mid-range", "Luxury", "Boutique"],
                                         help="Style of accommodation you prefer")
    
    preferences = st.text_area("Any specific preferences? (e.g., must-visit places, dietary restrictions, 'no flights', etc.)", 
                             placeholder="e.g., I'm vegetarian, I want to avoid crowded places...",
                             help="Any special requirements or preferences")
    
    # New section for travel requirements
    st.markdown('<div class="sub-header">Travel Requirements</div>', unsafe_allow_html=True)
    req_col1, req_col2 = st.columns(2)
    with req_col1:
        internet_required = st.checkbox("Internet connectivity required",
                                      help="Do you need internet access during your trip?")
        sim_card_required = st.checkbox("Local SIM card needed",
                                      help="Do you need a local SIM card?")
    with req_col2:
        travel_insurance = st.checkbox("Interested in travel insurance",
                                     help="Are you interested in travel insurance?")
        special_assistance = st.checkbox("Require special assistance",
                                       help="Do you require any special assistance?")
    
    submitted = st.form_submit_button("🚀 Generate My Itinerary!", use_container_width=True)

# Check for cached itinerary before processing
def check_cache(user_input):
    cache_key = f"{user_input.get('source', '')}_{user_input.get('destination', '')}_{user_input.get('start_date', '')}_{user_input.get('end_date', '')}"
    cached_data = get_cached_itinerary(cache_key)
    return cached_data

if submitted:
    # Basic validation
    if not destination or not source:
        st.error("Please enter both source and destination.")
    elif start_date >= end_date:
        st.error("End date must be after start date.")
    else:
        # Calculate trip duration
        duration = (end_date - start_date).days
        
        # Check if trip duration is realistic for the distance
        # This is a simplified check - in a real app, you'd use a distance API
        is_international = True  # Simplified assumption
        min_recommended_days = 3 if is_international else 1
        
        if duration < min_recommended_days:
            st.warning(f"For a trip from {source} to {destination}, we recommend at least {min_recommended_days} days to fully enjoy the experience. Your current itinerary is only {duration} days.")
        # Store user input
        st.session_state.user_input = {
            "source": source,
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "num_people": num_people,
            "age_group": age_group,
            "budget": budget,
            "currency": currency,
            "travel_style": travel_style,
            "interests": interests,
            "preferences": preferences,
            "accommodation_type": accommodation_type,
            "accommodation_style": accommodation_style,
            "internet_required": internet_required,
            "sim_card_required": sim_card_required,
            "travel_insurance": travel_insurance,
            "special_assistance": special_assistance,
            "duration": duration
        }
        
        # Check cache first
        cache_key = f"{source}_{destination}_{start_date}_{end_date}"
        cached_itinerary = check_cache(st.session_state.user_input)
        
        if cached_itinerary:
            st.session_state.itinerary = cached_itinerary
            st.success("✅ Using cached itinerary from previous similar request!")
            logger.info(f"Using cached itinerary for {destination}")
        else:
            # Start timing
            st.session_state.generation_start_time = time.time()
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Searching for destination information...")
            progress_bar.progress(25)
            
            with st.spinner('🌍 Searching for current information about your destination...'):
                # Get current information about the destination
                destination_info = search_tool.get_destination_info(destination)
                st.session_state.destination_info = destination_info
            
            status_text.text("Processing information...")
            progress_bar.progress(50)
            
            with st.spinner('📚 Processing information and building knowledge base...'):
                # Process the information and add to knowledge base
                knowledge_processor.process_destination(destination, destination_info)
                st.session_state.knowledge_processed = True
            
            status_text.text("Finding relevant information...")
            progress_bar.progress(75)
            
            with st.spinner('🔍 Finding the most relevant information for your trip...'):
                # Get relevant information for the user's specific request
                relevant_info = knowledge_processor.get_relevant_info(st.session_state.user_input)
            
            status_text.text("Generating your itinerary...")
            progress_bar.progress(90)
            
            with st.spinner('🧠 Generating your personalized itinerary...'):
                # Generate the itinerary
                itinerary = itinerary_generator.generate_itinerary(
                    st.session_state.user_input, 
                    relevant_info
                )
                st.session_state.itinerary = itinerary
                
                # Cache the itinerary
                cache_itinerary(cache_key, itinerary)
            
            progress_bar.progress(100)
            status_text.empty()
            
            # Log generation time
            generation_time = time.time() - st.session_state.generation_start_time
            logger.info(f"Itinerary generated in {generation_time:.2f} seconds for {destination}")
            
            st.success("✅ Itinerary generated successfully!")
            st.balloons()

# Display the itinerary if it exists
if st.session_state.itinerary:
    st.markdown("---")
    st.markdown('<div class="sub-header">Your Personalized Itinerary</div>', unsafe_allow_html=True)
    
    # Create expandable sections for better organization
    with st.expander("View Full Itinerary", expanded=True):
        st.markdown(st.session_state.itinerary)
    
    # Add download buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # Text download
        itinerary_text = st.session_state.itinerary
        st.download_button(
            label="📄 Download as Text",
            data=itinerary_text,
            file_name=f"{st.session_state.user_input.get('destination', 'itinerary')}_plan.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        # PDF download
        pdf_file = create_pdf(
            st.session_state.itinerary, 
            st.session_state.user_input.get('destination', 'Destination'),
            st.session_state.user_input
        )
        with open(pdf_file, "rb") as file:
            st.download_button(
                label="📘 Download as PDF",
                data=file,
                file_name=f"{st.session_state.user_input.get('destination', 'itinerary')}_itinerary.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        # Clean up the temporary file
        os.unlink(pdf_file)

# Display intermediate steps if needed
if st.session_state.destination_info and not st.session_state.itinerary:
    with st.expander("Preview of information found"):
        st.text(st.session_state.destination_info[:2000] + "..." 
                if len(st.session_state.destination_info) > 2000 
                else st.session_state.destination_info)

# Add information about the process
with st.expander("How This Works"):
    st.markdown("""
    This app uses a technique called RAG (Retrieval-Augmented Generation):
    
    1. **Retrieval**: We search the web for current information about your destination
    2. **Processing**: We process this information and store it in a knowledge base
    3. **Augmentation**: We find the most relevant information for your specific request
    4. **Generation**: We use AI to create a personalized itinerary
    
    This approach combines the power of AI with real-time information for more accurate results.
    """)

# Add feedback section
st.markdown("---")
st.markdown('<div class="sub-header">Your Feedback</div>', unsafe_allow_html=True)
feedback = st.selectbox("How would you rate this itinerary?", 
                       ["", "⭐ Excellent", "👍 Good", "😐 Average", "👎 Poor"])
if feedback:
    feedback_text = st.text_area("Additional comments (optional)")
    if st.button("Submit Feedback"):
        # Log feedback
        logger.info(f"Feedback: {feedback}, Comments: {feedback_text}")
        st.success("Thank you for your feedback! It helps us improve the service.")

# Footer
st.markdown("---")
# Inject custom footer with styling
st.markdown("""
    <style>
    .custom-footer {
        text-align: center;
        color: #6c757d;
        margin-top: 3rem;
        font-family: 'Segoe UI', sans-serif;
        animation: fadeIn 1s ease-in-out;
    }
    .custom-footer h2 {
        margin: 0.2rem 0;
        font-size: 1.8rem;
        font-weight: 700;
        color: #343a40;
    }
    .custom-footer p {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 500;
        color: #6c757d;
    }
    @keyframes fadeIn {
        from {opacity: 0;}
        to {opacity: 1;}
    }
    </style>

    <div class='custom-footer'>
        <p>Made with ❤️</p>
        <h2>Raghav Nahar</h2>
        <p>AI Consultant</p>
    </div>
""", unsafe_allow_html=True)