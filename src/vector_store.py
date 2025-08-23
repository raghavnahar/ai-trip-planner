import numpy as np
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex
import pickle
import os
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """
        Initialize the vector store with a sentence transformer model
        """
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []
        self.document_metadata = []
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.is_built = False
        
    def create_embeddings(self, texts: List[str], metadata: List[Dict] = None):
        """
        Create embeddings for a list of texts and store them in the vector index
        """
        if not texts:
            return
            
        # Create embeddings
        embeddings = self.model.encode(texts, show_progress_bar=False)
        
        # Initialize Annoy index if it doesn't exist
        if self.index is None:
            self.index = AnnoyIndex(self.dimension, 'angular')
            self.is_built = False
        
        # Store current length before adding new documents
        start_index = len(self.documents)
        
        # Add embeddings to index
        for i, embedding in enumerate(embeddings):
            self.index.add_item(start_index + i, embedding.astype(np.float32))
        
        # Store documents and metadata
        self.documents.extend(texts)
        if metadata:
            self.document_metadata.extend(metadata)
        else:
            self.document_metadata.extend([{}] * len(texts))
            
    def build_index(self):
        """
        Build the index after adding all items
        """
        if self.index is not None and not self.is_built and len(self.documents) > 0:
            self.index.build(10)  # 10 trees for good accuracy
            self.is_built = True
            logger.info("Annoy index built successfully")
        
    def search(self, query: str, k: int = 5) -> List[Tuple[str, float, Dict]]:
        """
        Search for the most relevant documents to the query
        Returns a list of (document, similarity_score, metadata) tuples
        """
        if self.index is None or len(self.documents) == 0 or not self.is_built:
            return []
            
        try:
            # Create embedding for the query
            query_embedding = self.model.encode([query])[0].astype(np.float32)
            
            # Search the index
            indices, distances = self.index.get_nns_by_vector(query_embedding, k, include_distances=True)
            
            # Convert angular distance to cosine similarity (cosine_sim = 1 - (angular_distance^2)/2)
            similarities = [1 - (d ** 2) / 2 for d in distances]
            
            # Format results
            results = []
            for i, idx in enumerate(indices):
                if idx < len(self.documents):  # Ensure index is valid
                    results.append((
                        self.documents[idx],
                        similarities[i],
                        self.document_metadata[idx]
                    ))
                    
            return results
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []
    
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
        
        # Build the index
        self.build_index()
        
    def save(self, filepath: str):
        """
        Save the vector store to disk
        """
        if self.index is None or not self.is_built:
            return
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save Annoy index
        self.index.save(filepath + ".ann")
        
        # Save documents and metadata
        with open(filepath + ".pkl", "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "metadata": self.document_metadata,
                "dimension": self.dimension
            }, f)
            
    def load(self, filepath: str):
        """
        Load the vector store from disk
        """
        try:
            # Load documents and metadata first to get dimension
            with open(filepath + ".pkl", "rb") as f:
                data = pickle.load(f)
                self.documents = data["documents"]
                self.document_metadata = data["metadata"]
                self.dimension = data.get("dimension", 384)
            
            # Load Annoy index
            self.index = AnnoyIndex(self.dimension, 'angular')
            self.index.load(filepath + ".ann")
            self.is_built = True
            
            logger.info("Vector store loaded successfully")
                
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            self.index = None
            self.documents = []
            self.document_metadata = []
            self.is_built = False