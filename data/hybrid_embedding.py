# Hybrid Search Engine using BM25 + TF-IDF Vectors
# Fast alternative to sentence transformers for document matching

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Any, Optional
import logging
import pickle
import os

class HybridSearchEngine:
    """
    Fast hybrid search engine combining BM25 (lexical) and TF-IDF vectors (semantic) search.
    Much faster than sentence transformers while still providing good semantic matching.
    """
    
    def __init__(self, max_features: int = 10000, ngram_range: Tuple[int, int] = (1, 2)):
        """
        Initialize the hybrid search engine.
        
        Args:
            max_features: Maximum number of TF-IDF features
            ngram_range: N-gram range for TF-IDF (1,2) means unigrams and bigrams
        """
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words='english',
            lowercase=True,
            strip_accents='unicode'
        )
        self.bm25 = None
        self.tfidf_matrix = None
        self.documents = []
        self.document_ids = []
        self.tokenized_docs = []
        self.is_fitted = False
        
    def preprocess_documents(self, documents: List[Dict[str, Any]], 
                           text_field: str = "text", 
                           id_field: str = "id") -> None:
        """
        Preprocess and index documents for both BM25 and TF-IDF search.
        
        Args:
            documents: List of document dictionaries
            text_field: Field name containing the text to search
            id_field: Field name containing the document ID
        """
        self.documents = documents
        texts = [doc[text_field] for doc in documents]
        self.document_ids = [str(doc[id_field]) for doc in documents]
        
        # Tokenize for BM25
        self.tokenized_docs = [self._tokenize(text) for text in texts]
        self.bm25 = BM25Okapi(self.tokenized_docs)
        
        # Generate TF-IDF matrix
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
        
        self.is_fitted = True
        logging.info(f"Indexed {len(documents)} documents with {self.tfidf_matrix.shape[1]} TF-IDF features")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - can be enhanced with more sophisticated methods."""
        import re
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return text.split()
    
    def find_best_matches(self, 
                         query: str, 
                         top_k: int = 10, 
                         bm25_weight: float = 0.4, 
                         tfidf_weight: float = 0.6) -> List[Dict[str, Any]]:
        """
        Find best matching documents using hybrid BM25 + TF-IDF search.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            bm25_weight: Weight for BM25 scores (lexical matching)
            tfidf_weight: Weight for TF-IDF similarity scores
            
        Returns:
            List of dictionaries containing matched documents with scores
        """
        if not self.is_fitted:
            raise ValueError("Documents must be preprocessed before searching")
        
        # BM25 search
        tokenized_query = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # TF-IDF search
        query_tfidf = self.tfidf_vectorizer.transform([query])
        tfidf_scores = cosine_similarity(query_tfidf, self.tfidf_matrix).flatten()
        
        # Normalize scores
        bm25_scores_norm = self._normalize_scores(bm25_scores)
        tfidf_scores_norm = self._normalize_scores(tfidf_scores)
        
        # Combine scores
        combined_scores = []
        for i, doc in enumerate(self.documents):
            doc_id = self.document_ids[i]
            bm25_score = bm25_scores_norm[i]
            tfidf_score = tfidf_scores_norm[i]
            
            combined_score = (bm25_weight * bm25_score + tfidf_weight * tfidf_score)
            
            combined_scores.append({
                'document': doc,
                'score': combined_score,
                'bm25_score': bm25_score,
                'tfidf_score': tfidf_score,
                'document_id': doc_id
            })
        
        # Sort by combined score and return top_k
        combined_scores.sort(key=lambda x: x['score'], reverse=True)
        return combined_scores[:top_k]
    
    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """Normalize scores to 0-1 range using min-max normalization."""
        if len(scores) == 0:
            return np.zeros_like(scores)
        
        min_score, max_score = np.min(scores), np.max(scores)
        if max_score == min_score:
            return np.ones_like(scores) * 0.5  # All scores equal
        return (scores - min_score) / (max_score - min_score)
    
    def save_index(self, filepath: str) -> None:
        """Save the trained model to disk for faster loading."""
        index_data = {
            'tfidf_vectorizer': self.tfidf_vectorizer,
            'bm25': self.bm25,
            'tfidf_matrix': self.tfidf_matrix,
            'documents': self.documents,
            'document_ids': self.document_ids,
            'tokenized_docs': self.tokenized_docs,
            'is_fitted': self.is_fitted
        }
        with open(filepath, 'wb') as f:
            pickle.dump(index_data, f)
        logging.info(f"Index saved to {filepath}")
    
    def load_index(self, filepath: str) -> None:
        """Load a pre-trained model from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Index file not found: {filepath}")
        
        with open(filepath, 'rb') as f:
            index_data = pickle.load(f)
        
        self.tfidf_vectorizer = index_data['tfidf_vectorizer']
        self.bm25 = index_data['bm25']
        self.tfidf_matrix = index_data['tfidf_matrix']
        self.documents = index_data['documents']
        self.document_ids = index_data['document_ids']
        self.tokenized_docs = index_data['tokenized_docs']
        self.is_fitted = index_data['is_fitted']
        
        logging.info(f"Index loaded from {filepath}")

# Global search engine instance
_global_search_engine = None

def get_search_engine() -> HybridSearchEngine:
    """Get or create the global search engine instance."""
    global _global_search_engine
    if _global_search_engine is None:
        _global_search_engine = HybridSearchEngine()
    return _global_search_engine

def find_best_matches(query: str, 
                     documents: Optional[List[Dict[str, Any]]] = None,
                     top_k: int = 10, 
                     bm25_weight: float = 0.4,
                     tfidf_weight: float = 0.6,
                     **kwargs) -> List[Dict[str, Any]]:
    """
    Replacement for the original find_best_matches method.
    Fast hybrid search using BM25 + TF-IDF.
    
    Args:
        query: Search query string
        documents: Optional list of documents to search (if not pre-indexed)
        top_k: Number of results to return
        bm25_weight: Weight for BM25 lexical matching (default 0.4)
        tfidf_weight: Weight for TF-IDF semantic matching (default 0.6)
        **kwargs: Additional arguments
        
    Returns:
        List of best matching documents with scores
    """
    search_engine = get_search_engine()
    
    # If documents provided, reindex (useful for dynamic document sets)
    if documents:
        search_engine.preprocess_documents(documents)
    
    return search_engine.find_best_matches(
        query=query,
        top_k=top_k,
        bm25_weight=bm25_weight,
        tfidf_weight=tfidf_weight
    )

def preprocess_document_corpus(documents: List[Dict[str, Any]], 
                              text_field: str = "text",
                              id_field: str = "id") -> None:
    """
    Preprocess a corpus of documents for efficient searching.
    Call this once when your application starts or when documents change.
    
    Args:
        documents: List of document dictionaries
        text_field: Field containing the searchable text
        id_field: Field containing unique document IDs
    """
    search_engine = get_search_engine()
    search_engine.preprocess_documents(documents, text_field, id_field)

def save_search_index(filepath: str) -> None:
    """Save the current search index to disk."""
    search_engine = get_search_engine()
    search_engine.save_index(filepath)

def load_search_index(filepath: str) -> None:
    """Load a search index from disk."""
    search_engine = get_search_engine()
    search_engine.load_index(filepath)