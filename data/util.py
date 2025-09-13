from sentence_transformers import SentenceTransformer, util
import torch

def find_best_matches(query: str, topics_file_path: str, top_n: int = 3, score_threshold: float = 0.5) -> list[dict]:
    """
    Finds the best matching topics for a given query from a list of topics in a file.

    Args:
        query (str): The input string to match.
        topics_file_path (str): The path to the .txt file containing topics.
        top_n (int): The maximum number of top matches to return.
        score_threshold (float): The minimum similarity score for a topic to be considered a match.

    Returns:
        list[dict]: A list of dictionaries, where each dict contains a 'topic' and its 'score'.
                    Returns an empty list if no matches are found above the threshold. (At most 3 and score always at least 0.4)
    """
    # 1. Load the model (this will be cached after the first run)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 2. Read topics from the file
    try:
        with open(topics_file_path, 'r') as f:
            topics = [line.strip() for line in f if line.strip()]
        if not topics:
            raise ValueError("Topics file is empty or contains no valid topics.")
    except FileNotFoundError:
        print(f"Error: Topics file not found at '{topics_file_path}'")
        return []
    
    # 3. Generate embeddings for all topics and the query
    topic_embeddings = model.encode(topics, convert_to_tensor=True)
    query_embedding = model.encode(query, convert_to_tensor=True)

    # 4. Compute cosine similarity between the query and all topics
    cosine_scores = util.cos_sim(query_embedding, topic_embeddings)[0]

    # 5. Find the top_n best matches
    # We use torch.topk to get the highest k scores and their indices
    top_results = torch.topk(cosine_scores, k=min(top_n, len(topics)))

    matches = []
    for score, idx in zip(top_results[0], top_results[1]):
        if score.item() >= score_threshold:
            matches.append({
                "topic": topics[idx],
                "score": score.item()
            })
    
    return matches

# --- Example Usage ---
if __name__ == "__main__":
    file_path = 'interests.txt'
    
    # This query is semantically close to multiple topics in our list
    input_string = "the study of matter, energy, and the universe"
    
    # Get the top 3 matches with a minimum score of 0.4
    best_matches = find_best_matches(
        query=input_string, 
        topics_file_path=file_path, 
        top_n=3, 
        score_threshold=0.4
    )
    
    print(f"Query: '{input_string}'\n")

    if best_matches:
        print("Found the following matches:")
        for match in best_matches:
            print(f"  - Topic: {match['topic']} (Score: {match['score']})")
    else:
        print("No sufficiently good matches were found.")


