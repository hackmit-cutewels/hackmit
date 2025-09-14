#!/usr/bin/env python3

"""
Test script to verify the updated hybrid embedding functionality in util.py
"""

from util import find_best_matches
import time

def test_find_best_matches():
    """Test the updated find_best_matches function"""
    print("Testing updated find_best_matches with hybrid BM25 + TF-IDF...")
    
    test_queries = [
        "learning about ancient empires and battles",
        "physics of stars and galaxies", 
        "cooking and food preparation",
        "programming and software development",
        "music and musical instruments"
    ]
    
    topics_file = "interests.txt"
    
    for query in test_queries:
        print(f"\n=== Query: '{query}' ===")
        
        start_time = time.time()
        matches = find_best_matches(
            query=query,
            topics_file_path=topics_file,
            top_n=5,
            score_threshold=0.3
        )
        end_time = time.time()
        
        print(f"Found {len(matches)} matches in {end_time - start_time:.4f} seconds:")
        for match in matches:
            print(f"  - {match['topic']} (score: {match['score']:.3f})")

if __name__ == "__main__":
    test_find_best_matches()
