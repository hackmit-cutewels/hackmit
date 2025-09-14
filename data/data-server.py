from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import networkx as nx
from util import add_best_interest_matches, load_graph, save_graph, add_place_edge
from fastapi import Query
from itertools import combinations

GRAPH_FILE = 'graph.json'
TOPICS_FILE = 'interests.txt'

app = FastAPI()

# Allow requests from your Next.js frontend (running on localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the graph data for a user
@app.get("/api/graph_data")
def get_graph_data(user_id: Optional[str] = None):
    people_graph = load_graph(GRAPH_FILE)

    if not user_id:
        return {"nodes": [], "edges": []}

    if user_id not in people_graph.nodes():
        return {"nodes": [], "edges": [], "error": f"User '{user_id}' not found in graph"}

    neighbors = set(people_graph.neighbors(user_id))
    interest_nodes = [
        n for n in neighbors
        if people_graph.nodes[n].get("type") == "interest"
    ]

    person_nodes = set()
    for interest in interest_nodes:
        for person in people_graph.neighbors(interest):
            if person == user_id:
                continue
            node_data = people_graph.nodes[person]
            if node_data.get("type") == "person" and node_data.get("phone_number"):
                person_nodes.add(person)

    node_ids = set([user_id]) | set(interest_nodes) | person_nodes
    nodes = []
    for n in node_ids:
        node_data = people_graph.nodes[n]
        node = {
            "id": n,
            "type": node_data.get("type", "unknown"),
            "label": n
        }
        if "phone_number" in node_data:
            node["phone_number"] = node_data["phone_number"]
        nodes.append(node)

    edges = []
    for interest in interest_nodes:
        if people_graph.has_edge(user_id, interest):
            edges.append({"source": user_id, "target": interest})
        if people_graph.is_directed() and people_graph.has_edge(interest, user_id):
            edges.append({"source": interest, "target": user_id})

    for interest in interest_nodes:
        for person in people_graph.neighbors(interest):
            if person in person_nodes:
                if people_graph.has_edge(interest, person):
                    edges.append({"source": interest, "target": person})
                if people_graph.is_directed() and people_graph.has_edge(person, interest):
                    edges.append({"source": person, "target": interest})

    return {"nodes": nodes, "edges": edges}

# Request/response models
class AddPersonRequest(BaseModel):
    person_id: str
    phone_number: Optional[str]
    query: str

class AddPersonWithPlaceRequest(BaseModel):
    person_id: str
    phone_number: Optional[str]
    latitude: float
    longitude: float

@app.post("/api/add_person_with_place")
async def add_person_with_place(request: AddPersonWithPlaceRequest):
    people_graph = load_graph(GRAPH_FILE)
    add_place_edge(
        graph=people_graph,
        person_id=request.person_id,
        phone_number = request.phone_number,
        latitude=request.latitude,
        longitude=request.longitude
    )
    save_graph(people_graph, GRAPH_FILE)

@app.post("/api/add_person_with_interest")
async def add_person_with_interest(request: AddPersonRequest):
    people_graph = load_graph(GRAPH_FILE)
    try:
        add_best_interest_matches(
            graph=people_graph,
            person_id=request.person_id,
            query=request.query,
            phone_number=request.phone_number,
            topics_file_path=TOPICS_FILE,
            top_n=3,
            score_threshold=0.4
        )
        save_graph(people_graph, GRAPH_FILE)
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topics file not found: {TOPICS_FILE}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def load_people_tags(graph_file: str) -> dict[str, set[str]]:
    G = load_graph(graph_file)
    return {
        p: {nbr for nbr in G.neighbors(p) if G.nodes[nbr].get("type") == "interest"}
        for p, a in G.nodes(data=True) if a.get("type") == "person"
    }

def calculate_jaccard_coefficient(set1: set, set2: set) -> float:
    """Calculate Jaccard coefficient manually."""
    intersection = set1 & set2
    union = set1 | set2
    if len(union) == 0:
        return 0.0
    return len(intersection) / len(union)

@app.get("/pairs_with_common_interest")
def pairs(threshold: float = Query(0.2, ge=0.0, le=1.0),
          graph_file: str = Query(GRAPH_FILE)):
    pt = load_people_tags(graph_file)
    people = sorted(pt)
    
    results = []
    if len(people) >= 2:
        for person1, person2 in combinations(people, 2):
            interests1 = pt[person1]
            interests2 = pt[person2]
            
            jaccard = calculate_jaccard_coefficient(interests1, interests2)
            if jaccard >= threshold:
                shared_interests = interests1 & interests2
                results.append({
                    "person1": person1,
                    "person2": person2,
                    "person1_interests": sorted(interests1),
                    "person2_interests": sorted(interests2),
                    "shared_interests": sorted(shared_interests),
                    "jaccard": round(jaccard, 6),
                })
    
    return {"threshold": threshold, "count": len(results), "pairs": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=1234)
