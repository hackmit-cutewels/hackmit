from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import networkx as nx
from util import add_best_interest_matches, load_graph, save_graph, add_place_edge


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
    query: str

class AddPersonWithPlaceRequest(BaseModel):
    person_id: str
    latitude: float
    longitude: float

@app.post("/api/add_person_with_place")
async def add_person_with_place(request: AddPersonWithPlaceRequest):
    people_graph = load_graph(GRAPH_FILE)
    add_place_edge(
        graph=people_graph,
        person_id=request.person_id,
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
