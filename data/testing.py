from util import add_best_interest_matches,load_graph,save_graph

GRAPH_FILE = 'graph.json'
TOPICS_FILE = 'interests.txt'

people_graph = load_graph(GRAPH_FILE)
print(f"Initial nodes: {people_graph.nodes()}")
add_best_interest_matches(
        graph=people_graph,
        person_id='user_02',
        query="Computer programming",
        topics_file_path=TOPICS_FILE,
        top_n=1,
        score_threshold=0.5
)
print("\n--- Final Graph State ---")
print("All nodes:", people_graph.nodes(data=True))
print("All edges:", people_graph.edges())
save_graph(people_graph, GRAPH_FILE)