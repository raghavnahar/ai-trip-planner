import os
from dotenv import load_dotenv
from typing import Dict, Any, List
import time
from huggingface_hub import InferenceClient
import requests
import logging
from utils.caching import cache_itinerary, get_cached_itinerary
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import random

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

class ItineraryGenerator:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        # Initialize InferenceClient with token and longer timeout
        self.client = InferenceClient(token=self.hf_token, timeout=60)
        
        # List of models to try, in order of preference with retry counts
        self.models = [
            {"name": "mistralai/Mixtral-8x7B-Instruct-v0.1", "retries": 2, "delay": 5},
            {"name": "mistralai/Mistral-7B-Instruct-v0.2", "retries": 2, "delay": 3},
            {"name": "HuggingFaceH4/zephyr-7b-beta", "retries": 2, "delay": 2},
            {"name": "google/flan-t5-xxl", "retries": 1, "delay": 1}  # Smaller model as last resort
        ]
        
        # Initialize geolocator for distance calculations
        self.geolocator = Nominatim(user_agent="travel_itinerary_app")
        
    def _get_city_coordinates(self, city_name):
        """Get coordinates for a city name"""
        try:
            location = self.geolocator.geocode(city_name)
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            logger.error(f"Error getting coordinates for {city_name}: {e}")
        return None
    
    def _calculate_distance(self, source, destination):
        """Calculate distance between two cities"""
        src_coords = self._get_city_coordinates(source)
        dest_coords = self._get_city_coordinates(destination)
        
        if src_coords and dest_coords:
            return geodesic(src_coords, dest_coords).kilometers
        return None
    
    def _get_transportation_recommendations(self, source, destination, budget, currency, duration):
        """Generate transportation recommendations based on distance and budget"""
        distance = self._calculate_distance(source, destination)
        
        if not distance:
            return "Could not calculate distance. Please research transportation options."
        
        # Currency conversion rates (simplified)
        conversion_rates = {
            "USD": 1,
            "INR": 75,
            "EUR": 0.85,
            "GBP": 0.75
        }
        
        rate = conversion_rates.get(currency, 1)
        
        # Budget categories
        budget_level = "low"
        if budget > 0:
            daily_budget = budget / duration if duration > 0 else budget
            if daily_budget > 200 * rate:
                budget_level = "high"
            elif daily_budget > 100 * rate:
                budget_level = "medium"
        
        recommendations = []
        
        # Flight recommendations
        if distance > 500:  # Long distance - recommend flights
            flight_price = distance * 0.5 * rate  # Simplified pricing model
            if budget_level == "high":
                flight_type = "Business Class"
                flight_price *= 2
            elif budget_level == "medium":
                flight_type = "Economy Class"
            else:
                flight_type = "Budget Airlines"
                flight_price *= 0.7
                
            recommendations.append({
                "type": "Flight",
                "class": flight_type,
                "approx_price": f"{flight_price:.0f} {currency}",
                "duration": f"{distance / 800:.1f} hours",  # Assuming 800 km/h average speed
                "recommendation": "Recommended for long distances"
            })
        
        # Train recommendations (for medium distances)
        if 200 < distance < 1000:
            train_price = distance * 0.2 * rate  # Simplified pricing model
            if budget_level == "high":
                train_class = "First Class"
                train_price *= 1.5
            else:
                train_class = "Standard Class"
                
            recommendations.append({
                "type": "Train",
                "class": train_class,
                "approx_price": f"{train_price:.0f} {currency}",
                "duration": f"{distance / 100:.1f} hours",  # Assuming 100 km/h average speed
                "recommendation": "Scenic and comfortable option"
            })
        
        # Bus recommendations (for short to medium distances)
        if distance < 800:
            bus_price = distance * 0.1 * rate  # Simplified pricing model
            recommendations.append({
                "type": "Bus",
                "class": "Standard",
                "approx_price": f"{bus_price:.0f} {currency}",
                "duration": f"{distance / 60:.1f} hours",  # Assuming 60 km/h average speed
                "recommendation": "Most economical option"
            })
        
        # Format the recommendations
        if not recommendations:
            return "No transportation recommendations available. Please research options for your route."
        
        result = "**Transportation Options:**\n\n"
        for i, option in enumerate(recommendations, 1):
            result += f"{i}. **{option['type']}** ({option['class']})\n"
            result += f"   - Approx. Price: {option['approx_price']}\n"
            result += f"   - Approx. Duration: {option['duration']}\n"
            result += f"   - Recommendation: {option['recommendation']}\n\n"
        
        # Add general advice
        result += "**Note:** Prices and durations are estimates. Actual prices may vary based on season, booking time, and other factors. Book in advance for better deals.\n\n"
        
        return result
    
    def _get_duration_recommendation(self, source, destination, duration):
        """Provide recommendations based on trip duration"""
        distance = self._calculate_distance(source, destination)
        
        if not distance:
            return ""
        
        # Determine if it's an international trip (simplified)
        is_international = distance > 500  # Arbitrary threshold
        
        if is_international:
            min_recommended_days = 5
            if duration < min_recommended_days:
                return f"**Important Recommendation:** For an international trip from {source} to {destination}, we recommend at least {min_recommended_days} days to account for travel time and jet lag. Your current trip of {duration} days may not provide enough time to fully enjoy the experience.\n\n"
        else:
            min_recommended_days = 2
            if duration < min_recommended_days:
                return f"**Recommendation:** For a trip from {source} to {destination}, we recommend at least {min_recommended_days} days to properly experience the destination. Your current trip of {duration} days may feel rushed.\n\n"
        
        return ""
    
    def generate_chat_messages(self, user_input: Dict[str, Any], relevant_info: str) -> List[Dict[str, str]]:
        """
        Create chat messages for the conversational API
        """
        try:
            # Extract user inputs
            source = user_input.get("source", "")
            destination = user_input.get("destination", "")
            start_date = user_input.get("start_date", "")
            end_date = user_input.get("end_date", "")
            num_people = user_input.get("num_people", 1)
            age_group = user_input.get("age_group", "")
            budget = user_input.get("budget", 0)
            currency = user_input.get("currency", "USD")
            travel_style = user_input.get("travel_style", "")
            interests = user_input.get("interests", [])
            preferences = user_input.get("preferences", "")
            accommodation_type = user_input.get("accommodation_type", [])
            accommodation_style = user_input.get("accommodation_style", "")
            internet_required = user_input.get("internet_required", False)
            sim_card_required = user_input.get("sim_card_required", False)
            travel_insurance = user_input.get("travel_insurance", False)
            special_assistance = user_input.get("special_assistance", False)
            duration = user_input.get("duration", 1)
        
        # Generate transportation recommendations
            transport_info = self._get_transportation_recommendations(source, destination, budget, currency, duration)
            duration_recommendation = self._get_duration_recommendation(source, destination, duration)
            
            # Create the system prompt
            system_prompt = """You are an expert travel planner with deep knowledge of every destination in the world. 
    Your task is to create a highly detailed, practical, and personalized travel itinerary 
    based on the user's inputs and the current information provided."""

            # Create the user prompt
            user_prompt = f"""
    **USER REQUEST:**
    - Source: {source}
    - Destination: {destination}
    - Travel Dates: {start_date} to {end_date}
    - Number of People: {num_people}
    - Age Group: {age_group}
    - Budget: {budget if budget > 0 else travel_style} ({currency})
    - Interests: {', '.join(interests) if interests else 'Not specified'}
    - Accommodation Preferences: {', '.join(accommodation_type) if accommodation_type else 'Any'} - {accommodation_style}
    - Special Preferences: {preferences if preferences else 'None'}
    - Requirements: 
      * Internet: {"Yes" if internet_required else "No"}
      * Local SIM: {"Yes" if sim_card_required else "No"}
      * Travel Insurance: {"Yes" if travel_insurance else "No"}
      * Special Assistance: {"Yes" if special_assistance else "No"}
      **TRANSPORTATION INFORMATION:**
{transport_info}

**DURATION RECOMMENDATION:**
{duration_recommendation}

    **CURRENT INFORMATION ABOUT {destination.upper()}:**
    {relevant_info[:3000]}  # Truncate to avoid token limits

    **INSTRUCTIONS:**
    Create a comprehensive day-by-day itinerary that includes ALL of the following sections:

    1. **Trip Overview**: Summary of the entire trip from {source} to {destination} and back. Suggest the recommended travel option
     based on users choice of budget, along with transport details like timings and fare of flights, buses or trains whish ever
     is more suitable for the traveller's preferences

    2. **Detailed Itinerary** with day-by-day breakdown including:
       - Transportation details from {source} to {destination} and back with specific timings and fares
       - Specific times, activities, and transportation methods within the destination
       - Must-visit places with entry requirements and ticket prices (if any)
       - Pre-booking requirements for attractions, shows, or activities

    3. **Accommodation Options**: Provide 2-3 different accommodation options matching:
       - The user's preferences: {accommodation_style} style, {', '.join(accommodation_type) if accommodation_type else 'any type'}
       - The user's budget: {budget if budget > 0 else travel_style}
       - Include approximate prices in {currency}

    4. **Estimated Cost Breakdown** in {currency}:
       - Transportation (to/from and within destination)
       - Accommodation (with different options)
       - Food & drinks
       - Activities & entrance fees
       - Miscellaneous expenses
       - **TOTAL ESTIMATED COST** (clearly highlighted)

    5. **Practical Information**:
       - Transportation options with contact numbers if available
       - Nearest airports/railway stations to {destination}
       - Internet and connectivity options
       - Essential items to pack
       - Local customs and etiquette
       - Emergency contact numbers

    6. **Pre-Booking Requirements**:
       - List attractions that require advance booking
       - Include booking websites and approximate costs
       - Note any visa requirements if international travel

    Focus on creating an enjoyable experience that matches the user's preferences and interests.
    Provide specific, practical information that will help the user prepare for their trip.
    """
            
            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        except Exception as e:
            logger.error(f"Error generating chat messages: {str(e)}")
            raise
    
    def generate_itinerary(self, user_input: Dict[str, Any], relevant_info: str) -> str:
        """
        Generate an itinerary using available models with robust fallback system
        """
        try:
            messages = self.generate_chat_messages(user_input, relevant_info)
            
            # Try each model in order with retries
            for model_config in self.models:
                model_name = model_config["name"]
                max_retries = model_config["retries"]
                retry_delay = model_config["delay"]
                
                for attempt in range(max_retries + 1):  # +1 for the initial attempt
                    result = self._try_chat_completion(model_name, messages)
                    
                    if result and not any(error in result for error in ["Error", "timed out", "loading"]):
                        logger.info(f"Successfully generated itinerary using {model_name}")
                        return result
                    
                    logger.warning(f"Attempt {attempt + 1} for {model_name} failed: {result}")
                    
                    # If this wasn't the last attempt, wait before retrying
                    if attempt < max_retries:
                        wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                
                logger.info(f"All attempts for {model_name} failed. Moving to next model.")
                time.sleep(1)  # Brief pause before trying next model
            
            # Fallback to a simple response if all models fail
            logger.error("All model attempts failed. Using fallback itinerary.")
            return self._generate_fallback_itinerary(user_input)
        except Exception as e:
            logger.error(f"Error in generate_itinerary: {str(e)}")
            return self._generate_fallback_itinerary(user_input)
    
    def _try_chat_completion(self, model: str, messages: List[Dict[str, str]]) -> str:
        """
        Try to generate a response using chat completions API
        """
        try:
            # Use the chat completions API
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            
            # Extract the response content
            if response and response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                return "No response generated from the model."
            
        except Exception as e:
            # Check for specific error types
            error_msg = str(e).lower()
            if "unauthorized" in error_msg or "401" in error_msg:
                logger.error(f"Authentication error with {model}: {str(e)}")
                return "Error: Invalid Hugging Face token. Please check your .env file."
            elif "not found" in error_msg or "404" in error_msg:
                logger.error(f"Model not found: {model} - {str(e)}")
                return f"Error: Model {model} not found or access denied. You may need to accept terms on the model page."
            elif "loading" in error_msg or "503" in error_msg:
                logger.warning(f"Model loading: {model} - {str(e)}")
                return f"Model {model} is currently loading. Please try again in a few moments."
            elif "timeout" in error_msg or "timed out" in error_msg:
                logger.warning(f"Timeout with {model}: {str(e)}")
                return f"Request to {model} timed out. Please try again."
            else:
                logger.error(f"Unexpected error with {model}: {str(e)}")
                return f"Unexpected error with {model}: {str(e)}"
    
    def _generate_fallback_itinerary(self, user_input: Dict[str, Any]) -> str:
        """
        Generate a simple fallback itinerary when AI models fail
        """
        try:
            source = user_input.get("source", "your location")
            destination = user_input.get("destination", "your destination")
            currency = user_input.get("currency", "USD")
            days = 3  # Default number of days
            
            try:
                if user_input.get("start_date") and user_input.get("end_date"):
                    date1 = user_input["start_date"]
                    date2 = user_input["end_date"]
                    if hasattr(date1, 'day') and hasattr(date2, 'day'):
                        days = (date2 - date1).days
                        if days <= 0:
                            days = 3
            except:
                days = 3
                
            # Currency conversion rates (simplified for example)
            conversion_rates = {
                "USD": 1,
                "INR": 75,
                "EUR": 0.85,
                "GBP": 0.75
            }
            
            rate = conversion_rates.get(currency, 1)

            # Calculate budget per day
            daily_budget = budget / duration if budget > 0 and duration > 0 else 100 * rate
            
            # Generate transportation recommendations
            transport_info = self._get_transportation_recommendations(source, destination, budget, currency, duration)
            duration_recommendation = self._get_duration_recommendation(source, destination, duration)
            
            # Determine accommodation style based on budget
            if daily_budget > 200 * rate:
                acc_style = "Luxury"
                acc_price_range = f"{int(150 * rate)}-{int(400 * rate)}"
            elif daily_budget > 100 * rate:
                acc_style = "Mid-range"
                acc_price_range = f"{int(80 * rate)}-{int(150 * rate)}"
            else:
                acc_style = "Budget"
                acc_price_range = f"{int(20 * rate)}-{int(50 * rate)}"
            
            return f"""
{duration_recommendation}

**Trip Overview:**
A {duration}-day trip from {source} to {destination} and back, focusing on major attractions and local experiences.

{transport_info}

**Estimated Total Cost in {currency}:** 
Costs vary based on travel style and preferences. Budget approximately:
- Transportation (round trip): {int(200 * duration * rate)} - {int(500 * duration * rate)} {currency}
- Accommodation: {int(50 * duration * rate)} - {int(200 * duration * rate)} {currency} per person
- Food: {int(30 * duration * rate)} - {int(100 * duration * rate)} {currency} per person
- Activities: {int(20 * duration * rate)} - {int(100 * duration * rate)} {currency} per person
- Miscellaneous: {int(20 * duration * rate)} - {int(50 * duration * rate)} {currency} per person

**TOTAL ESTIMATED COST: {int(320 * duration * rate)} - {int(950 * duration * rate)} {currency} per person**

    **Accommodation Options:**
    1. Budget Option: Hostels or budget hotels ({int(20 * days * rate)}-{int(50 * days * rate)} {currency})
    2. Mid-range Option: 3-star hotels or apartments ({int(80 * days * rate)}-{int(150 * days * rate)} {currency})
    3. Luxury Option: 4-5 star hotels or resorts ({int(200 * days * rate)}-{int(400 * days * rate)} {currency})

    **Daily Itinerary:**

    **Day 1: Travel from {source} to {destination}**
    - **Morning:** Depart from {source}
    - **Afternoon:** Arrive in {destination}, check into accommodation
    - **Evening:** Explore the local area around your accommodation

    **Day 2: Major Attractions**
    - **Morning:** Visit the most famous landmarks
    - **Afternoon:** Explore museums or cultural sites
    - **Evening:** Experience local nightlife or entertainment

    **Day 3: Local Experiences & Return to {source}**
    - **Morning:** Try local cuisine and visit markets
    - **Afternoon:** Last-minute shopping or sightseeing
    - **Evening:** Return to {source}

    **Pre-Booking Requirements:**
    - Check if any major attractions require advance booking
    - Research visa requirements if traveling internationally
    - Consider booking popular restaurants in advance

    **Essential Items to Pack:**
    - Travel documents (ID, tickets, reservations)
    - Appropriate clothing for the destination's climate
    - Chargers and power adapters
    - Basic first aid kit
    - {"Local SIM card or international roaming plan" if user_input.get("sim_card_required", False) else "Consider connectivity options"}

    **Transportation Options:**
    - Research flights/trains from {source} to {destination}
    - Look into local transportation (metro, buses, taxis)
    - Consider ride-sharing services at your destination

    *Note: This is a generic itinerary. For personalized recommendations, please try again later or check official tourism websites.*
    """
        except Exception as e:
            logger.error(f"Error in fallback itinerary generation: {str(e)}")
            return "We apologize, but we're experiencing technical difficulties. Please try again later or contact support if the problem persists."
    
    def extract_user_input(self, form_data: Dict) -> Dict[str, Any]:
        
        """
        Extract and format user input from the form data
        """
        
            # Calculate duration
        duration = 1
        if form_data.get("start_date") and form_data.get("end_date"):
            try:
                duration = (form_data["end_date"] - form_data["start_date"]).days
                if duration <= 0:
                    duration = 1
            except:
                duration = 1
            return {
                "source": form_data.get("source", ""),
                "destination": form_data.get("destination", ""),
                "start_date": form_data.get("start_date", ""),
                "end_date": form_data.get("end_date", ""),
                "num_people": form_data.get("num_people", 1),
                "age_group": form_data.get("age_group", ""),
                "budget": form_data.get("budget", 0),
                "currency": form_data.get("currency", "USD"),
                "travel_style": form_data.get("travel_style", ""),
                "interests": form_data.get("interests", []),
                "preferences": form_data.get("preferences", ""),
                "accommodation_type": form_data.get("accommodation_type", []),
                "accommodation_style": form_data.get("accommodation_style", ""),
                "internet_required": form_data.get("internet_required", False),
                "sim_card_required": form_data.get("sim_card_required", False),
                "travel_insurance": form_data.get("travel_insurance", False),
                "special_assistance": form_data.get("special_assistance", False)
            }