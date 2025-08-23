from vector_store import VectorStore
import os

class KnowledgeProcessor:
    def __init__(self):
        self.vector_store = VectorStore()
        self.data_dir = "data/vector_stores"
        
    def process_destination(self, destination: str, info_text: str) -> None:
        """
        Process information about a destination and add it to the knowledge base
        """
        print(f"Processing information about {destination}...")
        self.vector_store.process_destination_info(destination, info_text)
        
    def get_relevant_info(self, user_input: dict, k: int = 8) -> str:
        """
        Get relevant information from the knowledge base for multiple aspects of travel
        """
        destination = user_input.get("destination", "")
        source = user_input.get("source", "")
        interests = user_input.get("interests", [])
        preferences = user_input.get("preferences", "")
        accommodation_style = user_input.get("accommodation_style", "")
        accommodation_type = user_input.get("accommodation_type", [])
        
        # Create multiple queries to get comprehensive information
        queries = [
            f"best attractions in {destination}",
            f"hotels accommodation in {destination} {accommodation_style}",
            f"local food restaurants in {destination}",
            f"transportation options from {source} to {destination}",
            f"transportation options in {destination}",
            f"cultural tips for {destination}",
            f"current events in {destination} 2024",
            f"entry requirements for {destination}",
            f"visa requirements for {destination}"
        ]
        
        # Add interest-specific queries
        for interest in interests:
            queries.append(f"{interest} in {destination}")
            
        # Add accommodation type queries
        for acc_type in accommodation_type:
            queries.append(f"{acc_type} in {destination}")
            
        # Add preference-specific queries if any
        if preferences:
            queries.append(f"{preferences} in {destination}")
        
        # Get results for all queries
        all_results = []
        for query in queries:
            results = self.vector_store.search(query, 3)  # Get top 3 for each query
            for doc, score, metadata in results:
                # Avoid duplicate content and ensure good relevance
                if doc not in all_results and score > 0.6:  # Minimum similarity threshold
                    all_results.append(doc)
            
        # Limit the total information to avoid overwhelming the AI
        return "\n\n".join(all_results[:15])  # Return up to 15 chunks
    
    def save_knowledge(self, destination: str):
        """
        Save the knowledge base for a destination
        """
        filepath = os.path.join(self.data_dir, f"{destination.lower().replace(' ', '_')}")
        self.vector_store.save(filepath)
        
    def load_knowledge(self, destination: str):
        """
        Load the knowledge base for a destination
        """
        filepath = os.path.join(self.data_dir, f"{destination.lower().replace(' ', '_')}")
        self.vector_store.load(filepath)