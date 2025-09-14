from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import networkx as nx
from networkx.algorithms.link_prediction import jaccard_coefficient
from util import add_best_interest_matches, load_graph, save_graph, add_place_edge
from fastapi import Query
from itertools import combinations
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
def get_pairs_nearby_place(jaccard_threshold: float = Query(0.2, ge=0.0, le=1.0),
    meters_threshold: float = Query(10000, ge=0.0, le=10000.0)):


    pt = load_people_tags(GRAPH_FILE)
    G = load_graph(GRAPH_FILE)
    people = sorted(pt)
    
    results = []
    if len(people) >= 2:
        for u, v in combinations(people, 2):
            interests1 = pt[u]
            interests2 = pt[v]
            
            jaccard = calculate_jaccard_coefficient(interests1, interests2)
            if jaccard >= jaccard_threshold:
                shared_interests = interests1 & interests2

                tmp_res = []
                places_u = {nbr for nbr in G.neighbors(u) if G.nodes[nbr].get("type") == "place"}
                places_v = {nbr for nbr in G.neighbors(v) if G.nodes[nbr].get("type") == "place"}
                for place_u in places_u:
                    for place_v in places_v:
                        distance = lat_lon_to_meters(place_u[0], place_u[1], place_v[0], place_v[1])
                        if distance <= meters_threshold:
                            tmp_res.append({
                                "nearby_place_person_1_latlong": place_u,
                                "nearby_place_person_2_latlong": place_v,
                                "distance_meters": round(distance, 2)
                            })
                if not tmp_res:
                    continue

                results.append({
                    "person1": u,
                    "person2": v ,
                    "description": f"Shared interests: {', '.join(sorted(shared_interests))}, Distance: {', '.join([str(r['distance_meters']) + 'm' for r in tmp_res])}, Places: {', '.join([str(r['nearby_place_person_1_latlong']) + ' & ' + str(r['nearby_place_person_2_latlong']) for r in tmp_res])}",
                })
    
    return {"pairs": results}

MODEL = "claude-3-5-sonnet-20240620"   # pick your Claude 3.x model

def llm_interest_similarity(
    interests_a: Iterable[str],
    interests_b: Iterable[str],
    model: str = MODEL,
    temperature: float = 0.0,
) -> Tuple[float, str]:
    """
    Ask the LLM to score how similar two interest sets are.
    Returns (score in [0,1], short explanation).
    """
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    A = sorted({str(x).strip() for x in interests_a})
    B = sorted({str(x).strip() for x in interests_b})

    prompt = f"""
You will rate how similar two people's interests are.

Output:
Return ONLY JSON with keys "score" (float 0..1) and "explanation" (short).

Guidelines:
- 1.0 if sets are essentially identical.
- ~0.8 for many exact overlaps or very closely related themes.
- ~0.5 for a few overlaps or strong thematic relatedness.
- ~0.2 for weak relations.
- 0.0 if unrelated.
- Heavily weight exact matches; with zero exact matches, rarely exceed 0.7.
- Use 3 decimal places for "score".

A = {A}
B = {B}

Return JSON ONLY, like:
{{"score": 0.000, "explanation": "brief reason"}}
""".strip()

    msg = client.messages.create(
        model=model,
        max_tokens=300,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract text content and parse JSON
    text = "".join(
        block.text for block in msg.content
        if getattr(block, "type", None) == "text"
    ).strip()

    data = json.loads(text)  # let this raise if not valid JSON
    score = float(data.get("score", 0.0))

    # clamp to [0,1]
    score = max(0.0, min(1.0, score))
    why = str(data.get("explanation", "")).strip()
    return score, why




@app.get("/pairs_with_common_interest")
def get_pairs_with_common_interest(threshold: float = Query(0.2, ge=0.0, le=1.0),
          graph_file: str = Query(GRAPH_FILE)):
    pt = load_people_tags(graph_file)
    people = sorted(pt)

    results = []
    if len(people) >= 2:
        for person1, person2 in combinations(people, 2):
            t1, t2 = pt[person1], pt[person2]

            # exact Jaccard
            jaccard = calculate_jaccard_coefficient(t1, t2)

            # LLM score (fallback to Jaccard on any error)
            try:
                llm_score, why = llm_interest_similarity(t1, t2)
            except Exception:
                llm_score, why = jaccard, "fallback=jaccard"

            avg_score = (jaccard + llm_score) / 2.0

            if avg_score >= threshold:
                results.append({
                    "person1": person1,
                    "person2": person2,
                    "description": f"Shared interests: {', '.join(sorted(shared_interests))}",
                })

    results.sort(key=lambda x: (-x["average"], -x["jaccard"], x["person1"], x["person2"]))
    return {"threshold": threshold, "count": len(results), "pairs": results}

@app.get("/get_pairs")
def get_pairs():
    return {"pairs": get_pairs_nearby_place()["pairs"] + get_pairs_with_common_interest()["pairs"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=1234)
