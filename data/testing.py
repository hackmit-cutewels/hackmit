from util import add_best_interest_matches, load_graph, save_graph, add_interest_edge

GRAPH_FILE = 'graph.json'
TOPICS_FILE = 'interests.txt'

def create_comprehensive_example():
    """Create a comprehensive example showing people with and without phone numbers"""
    people_graph = load_graph(GRAPH_FILE)
    print("=== COMPREHENSIVE GRAPH EXAMPLE ===\n")
    print(f"Initial nodes: {people_graph.nodes()}")
    
    # Add some people with phone numbers
    print("\n1. Adding people WITH phone numbers:")
    add_best_interest_matches(
        graph=people_graph,
        person_id='alice_tech',
        phone_number='555-0001',
        query="Computer programming and software development",
        topics_file_path=TOPICS_FILE,
        top_n=3,
        score_threshold=0.4
    )
    
    add_best_interest_matches(
        graph=people_graph,
        person_id='bob_sports',
        phone_number='555-0002',
        query="Football and competitive sports",
        topics_file_path=TOPICS_FILE,
        top_n=2,
        score_threshold=0.4
    )
    
    add_best_interest_matches(
        graph=people_graph,
        person_id='charlie_gaming',
        phone_number='555-0003',
        query="Video games and gaming culture",
        topics_file_path=TOPICS_FILE,
        top_n=2,
        score_threshold=0.4
    )
    
    # Add some people WITHOUT phone numbers (these won't show up in API responses)
    print("\n2. Adding people WITHOUT phone numbers (won't appear in API):")
    add_best_interest_matches(
        graph=people_graph,
        person_id='diana_art',
        phone_number=None,  # No phone number
        query="Art and creative expression",
        topics_file_path=TOPICS_FILE,
        top_n=2,
        score_threshold=0.4
    )
    
    add_best_interest_matches(
        graph=people_graph,
        person_id='eve_music',
        phone_number=None,  # No phone number
        query="Music and musical instruments",
        topics_file_path=TOPICS_FILE,
        top_n=2,
        score_threshold=0.4
    )
    
    # Add a person with some shared interests but no phone
    add_best_interest_matches(
        graph=people_graph,
        person_id='frank_programming',
        phone_number=None,  # No phone number - shares interests with alice_tech
        query="Programming and computer science",
        topics_file_path=TOPICS_FILE,
        top_n=2,
        score_threshold=0.4
    )
    
    # Add a person with phone number who shares interests
    add_best_interest_matches(
        graph=people_graph,
        person_id='grace_gaming',
        phone_number='555-0004',
        query="Video gaming and esports",
        topics_file_path=TOPICS_FILE,
        top_n=2,
        score_threshold=0.4
    )
    
    # Manually add some direct interest connections to show more relationships
    print("\n3. Adding some direct interest connections:")
    add_interest_edge(people_graph, 'alice_tech', '555-0001', 'Robotics')
    add_interest_edge(people_graph, 'bob_sports', '555-0002', 'Hiking')
    add_interest_edge(people_graph, 'diana_art', None, 'Learning')  # No phone
    add_interest_edge(people_graph, 'eve_music', None, 'Models')    # No phone
    
    print("\n=== FINAL GRAPH STATE ===")
    print("All nodes:", people_graph.nodes(data=True))
    print("\nAll edges:", people_graph.edges())
    
    # Show which people have phone numbers
    print("\n=== PEOPLE WITH PHONE NUMBERS (will appear in API) ===")
    for node, data in people_graph.nodes(data=True):
        if data.get('type') == 'person' and data.get('phone_number'):
            print(f"- {node}: {data['phone_number']}")
    
    print("\n=== PEOPLE WITHOUT PHONE NUMBERS (won't appear in API) ===")
    for node, data in people_graph.nodes(data=True):
        if data.get('type') == 'person' and not data.get('phone_number'):
            print(f"- {node}: No phone number")
    
    # Show interests for each person
    print("\n=== INTERESTS BY PERSON ===")
    for node, data in people_graph.nodes(data=True):
        if data.get('type') == 'person':
            interests = [n for n in people_graph.neighbors(node) if people_graph.nodes[n].get('type') == 'interest']
            phone_status = "with phone" if data.get('phone_number') else "NO PHONE"
            print(f"- {node} ({phone_status}): {interests}")
    
    save_graph(people_graph, GRAPH_FILE)
    return people_graph

def test_smart_suggestions():
    """Test the smart suggestions system with demo data"""
    from util import get_smart_interest_suggestions
    
    print("\n=== TESTING SMART SUGGESTIONS ===\n")
    
    # Load the graph
    people_graph = load_graph(GRAPH_FILE)
    
    # Test suggestions for each user with phone numbers
    test_users = ['alice_tech', 'bob_sports', 'charlie_gaming', 'grace_gaming']
    
    for user in test_users:
        if user in people_graph.nodes():
            print(f"\n--- Suggestions for {user} ---")
            suggestions = get_smart_interest_suggestions(
                graph=people_graph,
                person_id=user,
                topics_file_path=TOPICS_FILE,
                top_n=5
            )
            
            if suggestions:
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"{i}. {suggestion['interest']}")
                    print(f"   Score: {suggestion['combined_score']:.3f} (Confidence: {suggestion['confidence']:.3f})")
                    print(f"   Reason: {suggestion['reason']}")
                    if suggestion['similar_users']:
                        print(f"   Similar users: {', '.join(suggestion['similar_users'])}")
                    print()
            else:
                print("No suggestions available")
        else:
            print(f"User {user} not found in graph")

if __name__ == "__main__":
    # Create demo data and test suggestions
    print("Creating comprehensive demo data...")
    people_graph = create_comprehensive_example()
    
    print("\nTesting smart suggestions...")
    test_smart_suggestions()
    
    print("\n=== DEMO READY ===")
    print("You can now test the suggestions in the frontend!")
    print("Try logging in as: alice_tech, bob_sports, charlie_gaming, or grace_gaming")
    