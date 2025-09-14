from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import networkx as nx
from util import add_best_interest_matches, load_graph, save_graph, add_place_edge
from fastapi import Query
from itertools import combinations
from networkx.algorithms.link_prediction import jaccard_coefficient


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
# Returns all direct neighbors of the user with node type "interest"
# and only those nodes of type "person" where phone_number is not None that share at least one interest with the user
# If no user_id is provided, returns the empty graph:

@app.get("/api/graph_data")
def get_graph_data(user_id: Optional[str] = None):
    people_graph = load_graph(GRAPH_FILE)

    if not user_id:
        # No user_id: return empty graph
        return {"nodes": [], "edges": []}

    if user_id not in people_graph.nodes():
        return {"nodes": [], "edges": [], "error": f"User '{user_id}' not found in graph"}

    # Get all direct neighbors of the user
    neighbors = set(people_graph.neighbors(user_id))

    # Interests: direct neighbors of type "interest"
    interest_nodes = [
        n for n in neighbors
        if people_graph.nodes[n].get("type") == "interest"
    ]

    # For each interest, find people (with phone_number) who share that interest (excluding the user)
    person_nodes = set()
    for interest in interest_nodes:
        for person in people_graph.neighbors(interest):
            if person == user_id:
                continue
            node_data = people_graph.nodes[person]
            if node_data.get("type") == "person" and node_data.get("phone_number"):
                person_nodes.add(person)

    # Build node list: user, their interests, and matching people
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

    # Build edge list: only edges between user and their interests, and between those interests and matching people
    edges = []
    # Edges from user to their interests
    for interest in interest_nodes:
        if people_graph.has_edge(user_id, interest):
            edges.append({"source": user_id, "target": interest})
        if people_graph.is_directed() and people_graph.has_edge(interest, user_id):
            edges.append({"source": interest, "target": user_id})
    # Edges from interests to matching people
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
    """
    Add a person with their interests to the graph.
    
    - **person_id**: Unique identifier for the person
    - **query**: Interest query (e.g., "physics of stars and galaxies")
    """
    try:
        # Call the function with predefined parameters
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

# helper for pairs_with_common_interest
def load_people_tags(graph_file: str) -> dict[str, set[str]]:
    G = load_graph(graph_file)
    return {
        p: {nbr for nbr in G.neighbors(p) if G.nodes[nbr].get("type") == "interest"}
        for p, a in G.nodes(data=True) if a.get("type") == "person"
    }

@app.get("/pairs_with_common_interest")
def pairs(threshold: float = Query(0.2, ge=0.0, le=1.0),
          graph_file: str = Query(GRAPH_FILE)):
    pt = load_people_tags(graph_file)
    people = sorted(pt)
    tags = sorted({t for ts in pt.values() for t in ts})
    B = nx.Graph()
    B.add_nodes_from(people, bipartite="people")
    B.add_nodes_from(tags, bipartite="tags")
    for p, ts in pt.items():
        for t in ts:
            B.add_edge(p, t)
    results = []
    if len(people) >= 2:
        for u, v, s in jaccard_coefficient(B, combinations(people, 2)):
            s = float(s)
            if s >= threshold:
                t1, t2 = pt[u], pt[v]
                results.append({
                    "person1": u,
                    "person2": v,
                    "person1_interests": sorted(t1),
                    "person2_interests": sorted(t2),
                    "shared_interests": sorted(t1 & t2),
                    "jaccard": round(s, 6),
                })
    return {"threshold": threshold, "count": len(results), "pairs": results}



    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=1234)
