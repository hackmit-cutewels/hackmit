from hybrid_embedding import find_best_matches as hybrid_find_best_matches
import networkx as nx 
import json
from networkx.readwrite import json_graph
from typing import Optional

GRAPH_FILE = 'graph.json'
TOPICS_FILE = 'interests.txt'

# ===== Basic Query Functionality (used in vis.py)
def get_interests_for_person(graph: nx.Graph, person_id: str) -> list[str]:
    """Returns a list of interests connected to a specific person."""
    if person_id not in graph:
        return []
    # graph.neighbors(node) returns an iterator of all connected nodes
    return [node for node in graph.neighbors(person_id) if graph.nodes[node].get('type') == 'interest']

def get_people_for_interest(graph: nx.Graph, interest: str) -> list[str]:
    """Returns a list of people connected to a specific interest."""
    if interest not in graph:
        return []
    return [node for node in graph.neighbors(interest) if graph.nodes[node].get('type') == 'person']

# =====



def find_best_matches(query: str, topics_file_path: str, top_n: int = 3, score_threshold: float = 0.5) -> list[dict]:
    """
    Finds the best matching topics for a given query from a list of topics in a file.
    Now using fast hybrid BM25 + TF-IDF search instead of sentence transformers.

    Args:
        query (str): The input string to match.
        topics_file_path (str): The path to the .txt file containing topics.
        top_n (int): The maximum number of top matches to return.
        score_threshold (float): The minimum similarity score for a topic to be considered a match.

    Returns:
        list[dict]: A list of dictionaries, where each dict contains a 'topic' and its 'score'.
                    Returns an empty list if no matches are found above the threshold.
    """
    # 1. Read topics from the file
    try:
        with open(topics_file_path, 'r') as f:
            topics = [line.strip() for line in f if line.strip()]
        if not topics:
            raise ValueError("Topics file is empty or contains no valid topics.")
    except FileNotFoundError:
        print(f"Error: Topics file not found at '{topics_file_path}'")
        return []
    
    # 2. Convert topics to the document format expected by hybrid search
    documents = []
    for i, topic in enumerate(topics):
        documents.append({
            "id": i,
            "text": topic
        })
    
    # 3. Use hybrid BM25 + TF-IDF search for matching
    try:
        hybrid_results = hybrid_find_best_matches(
            query=query,
            documents=documents,
            top_k=min(top_n, len(topics)),
            bm25_weight=0.4,  # Good balance for topic matching
            tfidf_weight=0.6
        )
        
        # 4. Convert results to the expected format and apply score threshold
        matches = []
        for result in hybrid_results:
            if result['score'] >= score_threshold:
                matches.append({
                    "topic": result['document']['text'],
                    "score": result['score']
                })
        
        return matches
        
    except Exception as e:
        print(f"Error during hybrid search: {e}")
        return []

def load_graph(file_path: str) -> nx.Graph:
    """Loads a graph from a JSON file. If the file doesn't exist, returns a new empty graph."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return json_graph.node_link_graph(data)
    except FileNotFoundError:
        print(f"Graph file not found. Creating a new graph.")
        return nx.Graph()

def save_graph(graph: nx.Graph, file_path: str):
    """Saves a graph to a JSON file."""
    data = json_graph.node_link_data(graph)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Graph saved to {file_path}")

def add_interest_edge(graph: nx.Graph, person_id: str, phone_number: Optional[str], interest: str):
    """
    Adds nodes and an edge between a person and an interest.
    Assigns a 'type' attribute to each node for easier identification.
    """
    # networkx handles node creation automatically if they don't exist
    graph.add_node(person_id, type='person', phone_number=phone_number)
    graph.add_node(interest, type='interest')
    
    # Add the edge connecting the person to their interest
    graph.add_edge(person_id, interest)
    print(f"Added edge: {person_id} -> {interest}")

def add_place_edge(graph: nx.Graph, phone_number: Optional[str], person_id: str, latitude: float, longitude: float):
    """
    Adds a node and an edge between a person and a place.
    Assigns a 'type' attribute to each node for easier identification.
    """
    graph.add_node(person_id, type='person', phone_number=phone_number)
    graph.add_node((latitude, longitude), type='place') 
    
    # Add the edge connecting the person to the place
    graph.add_edge(person_id, (latitude, longitude))
    print(f"Added edge: {person_id} -> {latitude}, {longitude}")

def add_best_interest_matches(graph: nx.Graph, person_id: str, phone_number: str, query: str, topics_file_path: str, **kwargs):
    """
    Finds the best matching interests for a query and adds them as edges to the person's node.
    
    Args:
        graph (nx.Graph): The graph to modify.
        person_id (str): The ID of the person.
        query (str): The search string describing an interest.
        topics_file_path (str): Path to the list of topics.
        **kwargs: Optional arguments for find_best_matches (e.g., top_n=5, score_threshold=0.4).
    """
    print(f"\nFinding matches for '{person_id}' with query: '{query}'")
    matches = find_best_matches(query, topics_file_path, **kwargs)
    
    if not matches:
        print("No matches found above the score threshold.")
        return

    for match in matches:
        interest_topic = match['topic']
        add_interest_edge(graph, person_id, phone_number, interest_topic)

# --- Example Usage ---
if __name__ == "__main__":
    people_graph = load_graph(GRAPH_FILE)
    print(f"Initial nodes: {people_graph.nodes()}")
    add_interest_edge(people_graph, 'user_01', None, 'Classic Literature')
    add_best_interest_matches(
        graph=people_graph,
        person_id='user_02',
        phone_number='123-456-7890',
        query="learning about ancient empires and battles",
        topics_file_path=TOPICS_FILE,
        top_n=1,
        score_threshold=0.5
    )
    add_best_interest_matches(
        graph=people_graph,
        person_id='user_01',
        phone_number='098-765-4321',
        query="physics of stars and galaxies",
        topics_file_path=TOPICS_FILE,
        top_n=3,
        score_threshold=0.4
    )
    print("\n--- Final Graph State ---")
    print("All nodes:", people_graph.nodes(data=True))
    print("All edges:", people_graph.edges())
    if 'user_01' in people_graph:
        print("Interests for user_01:", list(people_graph.neighbors('user_01')))
    save_graph(people_graph, GRAPH_FILE)
