from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import networkx as nx
from util import add_best_interest_matches, load_graph, save_graph, add_place_edge
from fastapi import Query
from itertools import combinations
from networkx.algorithms.link_prediction import jaccard_coefficient
from geopy.distance import geodesic


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


@app.get("/api/graph_data")
def get_graph_data():
    people_graph = load_graph(GRAPH_FILE)
    
    # Convert nodes to JSON-serializable format
    nodes = []
    for node_id, node_data in people_graph.nodes(data=True):
        node = {
            "id": node_id,
            "type": node_data.get("type", "unknown"),
            "label": node_id  # Use the node_id as label, or customize as needed
        }
        # Add any additional node attributes if they exist
        if "name" in node_data:
            node["name"] = node_data["name"]
        if "description" in node_data:
            node["description"] = node_data["description"]
        nodes.append(node)
    
    # Convert edges to JSON-serializable format
    edges = []
    for source, target, edge_data in people_graph.edges(data=True):
        edge = {
            "source": source,
            "target": target
        }
        # Add edge attributes if they exist
        if "relationship" in edge_data:
            edge["relationship"] = edge_data["relationship"]
        if "weight" in edge_data:
            edge["weight"] = edge_data["weight"]
        edges.append(edge)
    
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

class GetPairsNearbyPlaceRequest(BaseModel):
    jaccard_threshold: float = Query(0.2, ge=0.0, le=1.0)
    meters_threshold: float = Query(10000, ge=0.0, le=10000.0)
    person_id: str

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

def lat_lon_to_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Convert latitude and longitude differences to meters using geopy.
    
    Args:
        lat1, lon1: First point (latitude, longitude) in degrees
        lat2, lon2: Second point (latitude, longitude) in degrees
    
    Returns:
        Distance in meters
    """
    point1 = (lat1, lon1)
    point2 = (lat2, lon2)
    return geodesic(point1, point2).meters

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
@app.get("/get_pairs")
async def pairs(threshold: float = Query(0.2, ge=0.0, le=1.0),
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
