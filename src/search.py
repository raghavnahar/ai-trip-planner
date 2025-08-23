import requests
from ddgs import DDGS
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import time
import random
import json
from datetime import datetime, timedelta
import os

class WebSearch:
    def __init__(self):
        self.ddgs = DDGS()
        # List of realistic user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
        ]
        self.cache_file = "data/search_cache.json"
        self.cache = self.load_cache()
        # Domains to avoid (known to block scraping)
        self.blocked_domains = [
            "tripadvisor.com", "expedia.com", "booking.com", 
            "travelweekly.com", "hotels.com"
        ]
    
    def load_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {}
    
    def save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def get_cached_content(self, url: str):
        """Get cached content if it exists and is not expired"""
        if url in self.cache:
            cached_data = self.cache[url]
            # Check if cache is still valid (24 hours)
            if datetime.now().timestamp() - cached_data['timestamp'] < 86400:
                return cached_data['content']
        return None
    
    def cache_content(self, url: str, content: str):
        """Cache content with current timestamp"""
        self.cache[url] = {
            'content': content,
            'timestamp': datetime.now().timestamp()
        }
        self.save_cache()
    
    def get_random_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def is_blocked_domain(self, url: str) -> bool:
        """Check if URL is from a blocked domain"""
        return any(domain in url for domain in self.blocked_domains)
    
    def search_destination(self, destination: str, max_results: int = 10) -> List[Dict]:
        """
        Search for information about a travel destination
        Returns a list of search results with titles, URLs, and snippets
        """
        try:
            # Add delay before searching
            time.sleep(random.uniform(1, 3))
            
            results = self.ddgs.text(
                f"{destination} travel guide 2024 attractions hotels restaurants",
                max_results=max_results
            )
            
            # Filter out blocked domains
            filtered_results = []
            for result in results:
                if not self.is_blocked_domain(result['href']):
                    filtered_results.append(result)
                else:
                    print(f"Skipping blocked domain: {result['href']}")
            
            return list(filtered_results)
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_page_content_with_retry(self, url: str, max_retries: int = 2) -> str:
        """
        Fetch content with retry mechanism and exponential backoff
        """
        for attempt in range(max_retries):
            try:
                # Add variable delay between requests
                if attempt > 0:
                    wait_time = (2 ** attempt) + random.random()
                    print(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
                
                headers = self.get_random_headers()
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    element.decompose()
                    
                # Get text content
                text = soup.get_text()
                
                # Clean up the text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text[:4000]  # Limit to first 4000 characters
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print(f"403 Forbidden error on attempt {attempt + 1}. Skipping...")
                    return ""
                elif e.response.status_code == 429:
                    wait_time = (2 ** attempt) + random.random()
                    print(f"Rate limited. Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"HTTP error {e.response.status_code} on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return ""
            except requests.exceptions.Timeout:
                print(f"Timeout error on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    return ""
            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return ""
        
        return ""
    
    def get_page_content(self, url: str) -> str:
        """
        Fetch and extract the main content from a web page with caching
        """
        # Check cache first
        cached_content = self.get_cached_content(url)
        if cached_content:
            print(f"Using cached content for {url}")
            return cached_content
            
        print(f"Fetching content from {url}")
        content = self.get_page_content_with_retry(url)
        
        if content:
            # Cache the content
            self.cache_content(url, content)
        
        return content
    
    def get_destination_info(self, destination: str) -> str:
        """
        Get comprehensive information about a destination by searching and
        extracting content from multiple sources
        """
        print(f"Searching for information about {destination}...")
        
        # Try multiple search queries to get diverse information
        search_queries = [
            f"{destination} travel guide 2024",
            f"{destination} attractions hotels restaurants",
            f"{destination} tourism official website",
            f"{destination} travel blog",
            f"things to do in {destination}",
            f"{destination} local food culture"
        ]
        
        all_content = ""
        successful_fetches = 0
        max_sources = 3  # Limit the number of sources to process
        
        for query in search_queries:
            if successful_fetches >= max_sources:
                break
                
            try:
                # Add delay between different search queries
                time.sleep(random.uniform(2, 4))
                
                search_results = self.ddgs.text(query, max_results=3)
                
                for result in search_results:
                    if successful_fetches >= max_sources:
                        break
                    
                    # Skip blocked domains
                    if self.is_blocked_domain(result['href']):
                        print(f"Skipping blocked domain: {result['href']}")
                        continue
                        
                    content = self.get_page_content(result['href'])
                    if content:
                        all_content += f"--- Source: {result['title']} ---\n{content}\n\n"
                        successful_fetches += 1
                        print(f"Successfully fetched content from {result['href']}")
                    
                    # Respectful delay between requests
                    time.sleep(random.uniform(3, 5))
                    
            except Exception as e:
                print(f"Error with query {query}: {e}")
                continue
        
        # If we couldn't fetch any content, provide a fallback message
        if not all_content:
            all_content = f"Could not retrieve current information about {destination}. Using general knowledge."
            print(all_content)
            
        return all_content

# Test the class
if __name__ == "__main__":
    search = WebSearch()
    test_destination = "Paris"
    info = search.get_destination_info(test_destination)
    print(f"Retrieved information about {test_destination}:")
    print(info[:1000] + "..." if len(info) > 1000 else info)