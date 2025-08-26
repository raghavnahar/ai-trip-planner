# 🧭 AI Trip Planner Pro

**AI Trip Planner Pro** is a smart, end-to-end travel planning assistant powered by open-source LLMs and real-time web search. It generates personalized itineraries based on user preferences, budget, travel dates, group size, and destination — complete with transport suggestions, hotel options, local food, pre-booking alerts, and packing checklists.

---

## 🌐 Live Demo  
👉 [Plan your trip now!!!](https://huggingface.co/spaces/raghavnahar/ai-trip-planner-pro)  

---

## 🚀 Features

- 🌍 **Multi-city itinerary generation** with round-trip planning
- 💰 **Budget-aware suggestions** or style-based planning (budget, moderate, lavish)
- 🧓 **Age-based recommendations** for activities and pace
- 🧳 **Packing checklist** tailored to destination and season
- 🏨 **Stay options** across budget tiers with neighborhood fit
- 🍽️ **Must-try food & local specialties**
- 🎟️ **Pre-booking alerts** for attractions with ticket prices
- 🚆 **Transport suggestions** with sample timings and fares
- 💱 **Cost estimates** in INR and USD
- 🌐 **Live web search** for fresh travel info (DuckDuckGo + BeautifulSoup)
- 📄 **PDF export** of final itinerary
- ✅ **Validation checks** for dates, feasibility, and real locations

---

## 🧠 Tech Stack

- **Streamlit** — UI framework
- **Hugging Face Inference API** — LLM access 
- **duckduckgo-search** — RAG-lite web search
- **BeautifulSoup** — HTML parsing
- **Geopy + Nominatim** — location validation and distance estimation
- **FPDF** — PDF generation
- **Python-dotenv** — secret management

---

## 📦 Installation

```bash
git clone https://github.com/your-username/ai-trip-planner-pro.git
cd ai-trip-planner-pro
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 🔐 Secrets
Create a .env file in the root directory:
```
HF_TOKEN=your_huggingface_token
HF_MODEL_ID=mistralai/Mistral-7B-Instruct-v0.2
```

## ▶️ Run Locally
```
streamlit run src/app.py
```

---

## 💡 Future Enhancements
- LangChain integration for advanced RAG
- Gemini or LLaMA model support
- Booking APIs (flights, hotels)
- Multi-user session history
- Voice input and itinerary narration

---

## 🙌 Credits
Built with care ❤️ by **Raghav Nahar - AI Consultant**
Powered by Hugging Face, Streamlit, and open-source travel data.

## 📌 Customization  

- ✏️ Update **`index.html`** to change text and content.  
- 🖼️ Replace the profile image and project images inside **`assets/images/`**.  
- 🎨 Modify colors, fonts, and layout in **`style.css`**.  
- ⚡ Adjust interactions and animations in **`script.js`**.  

## 📫 Connect With Me  

- 🌍 **Portfolio**: [Portfolio Website](https://raghavnahar.github.io/portfolio-website/)  
- 💼 **LinkedIn**: [Raghav Nahar](https://www.linkedin.com/in/raghav-nahar-4b7475150/)  
- 📧 **Email**: [nahar16raghav@gmail.com](mailto:nahar16raghav@gmail.com)
- 🤗 **Hugging Face**: [raghavnahar](https://huggingface.co/raghavnahar)

---

## 📄 License  

This project is open-source under the [MIT License](LICENSE).
