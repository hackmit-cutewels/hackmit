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
            # Only show users who have phone numbers
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

@app.get("/api/interests_list")
def get_interests_list(user_id: Optional[str] = None):
    """Get interests for a user and people sharing each interest"""
    people_graph = load_graph(GRAPH_FILE)
    
    if not user_id:
        return {"interests": []}
    
    if user_id not in people_graph.nodes():
        return {"interests": [], "error": f"User '{user_id}' not found in graph"}
    
    # Get user's interests
    user_interests = []
    for neighbor in people_graph.neighbors(user_id):
        if people_graph.nodes[neighbor].get("type") == "interest":
            # Find all people who share this interest
            people_sharing = []
            for person in people_graph.neighbors(neighbor):
                if person != user_id and people_graph.nodes[person].get("type") == "person":
                    person_data = people_graph.nodes[person]
                    # Only show users who have phone numbers
                    if person_data.get("phone_number"):
                        people_sharing.append({
                            "phone_number": person_data.get("phone_number")
                        })
            
            user_interests.append({
                "interest": neighbor,
                "people_sharing": people_sharing,
                "count": len(people_sharing)
            })
    
    # Sort by count of people sharing (most popular first)
    user_interests.sort(key=lambda x: x["count"], reverse=True)
    
    return {"interests": user_interests}

@app.post("/get_pairs_nearby_place")
async def get_pairs_nearby_place(request: GetPairsNearbyPlaceRequest):
    pt = load_people_tags(GRAPH_FILE)
    G = load_graph(GRAPH_FILE)
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
            if s >= request.jaccard_threshold:
                tmp_res = []
                t1, t2 = pt[u], pt[v]
                places_u = {nbr for nbr in G.neighbors(u) if G.nodes[nbr].get("type") == "place"}
                places_v = {nbr for nbr in G.neighbors(v) if G.nodes[nbr].get("type") == "place"}
                for place_u in places_u:
                    for place_v in places_v:
                        distance = lat_lon_to_meters(place_u[0], place_u[1], place_v[0], place_v[1])
                        if distance <= request.meters_threshold:
                            tmp_res.append({
                                "nearby_place_person_1_latlong": place_u,
                                "nearby_place_person_2_latlong": place_v,
                                "distance_meters": round(distance, 2)
                            })
                if not tmp_res:
                    continue

                results.append({
                    "person1": u,
                    "person2": v,
                    "person1_interests": sorted(t1),
                    "person2_interests": sorted(t2),
                    "shared_interests": sorted(t1 & t2),
                    "jaccard": round(s, 6),
                    "place_information": tmp_res,
                    "description" : "People with similar interests and nearby places."
                })

    return { "pairs" : results}

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
