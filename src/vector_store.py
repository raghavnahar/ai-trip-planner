import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os
from typing import List, Dict, Tuple

class VectorStore:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """
        Initialize the vector store with a sentence transformer model
        """
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []
        self.document_metadata = []
        
    def create_embeddings(self, texts: List[str], metadata: List[Dict] = None):
        """
        Create embeddings for a list of texts and store them in the vector index
        """
        if not texts:
            return
            
        # Create embeddings
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Initialize FAISS index if it doesn't exist
        if self.index is None:
            self.index = faiss.IndexFlatL2(embeddings.shape[1])
        
        # Add embeddings to index
        self.index.add(embeddings.astype(np.float32))
        
        # Store documents and metadata
        self.documents.extend(texts)
        if metadata:
            self.document_metadata.extend(metadata)
        else:
            self.document_metadata.extend([{}] * len(texts))
            
    def search(self, query: str, k: int = 5) -> List[Tuple[str, float, Dict]]:
        """
        Search for the most relevant documents to the query
        Returns a list of (document, similarity_score, metadata) tuples
        """
        if self.index is None or len(self.documents) == 0:
            return []
            
        # Create embedding for the query
        query_embedding = self.model.encode([query])
        
        # Search the index
        distances, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        # Format results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):  # Ensure index is valid
                results.append((
                    self.documents[idx],
                    1 - distances[0][i],  # Convert distance to similarity score
                    self.document_metadata[idx]
                ))
                
        return results
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for better retrieval
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
            
        return chunks
    
    def process_destination_info(self, destination: str, info_text: str) -> None:
        """
        Process destination information by chunking and creating embeddings
        """
        # Chunk the text
        chunks = self.chunk_text(info_text)
        
        # Create metadata for each chunk
        metadata = [{"destination": destination, "chunk_id": i} for i in range(len(chunks))]
        
        # Create embeddings
        self.create_embeddings(chunks, metadata)
        
    def save(self, filepath: str):
        """
        Save the vector store to disk
        """
        if self.index is None:
            return
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, filepath + ".index")
        
        # Save documents and metadata
        with open(filepath + ".pkl", "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "metadata": self.document_metadata
            }, f)
            
    def load(self, filepath: str):
        """
        Load the vector store from disk
        """
        try:
            # Load FAISS index
            self.index = faiss.read_index(filepath + ".index")
            
            # Load documents and metadata
            with open(filepath + ".pkl", "rb") as f:
                data = pickle.load(f)
                self.documents = data["documents"]
                self.document_metadata = data["metadata"]
                
        except Exception as e:
            print(f"Error loading vector store: {e}")
            self.index = None
            self.documents = []
            self.document_metadata = []