from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import networkx as nx
from util import add_best_interest_matches,load_graph,save_graph


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
    # Create a sample graph
    G = nx.star_graph(4)
    # Convert to a JSON-serializable format
    nodes = [{"id": node, "label": f"Node {node}"} for node in G.nodes()]
    edges = [{"from": u, "to": v} for u, v in G.edges()]
    return {"nodes": nodes, "edges": edges}


# Request/response models
class AddPersonRequest(BaseModel):
    person_id: str
    query: str

class AddPersonResponse(BaseModel):
    success: bool
    message: str
    person_id: str

@app.post("/api/add_person_with_interest", response_model=AddPersonResponse)
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
        
        return AddPersonResponse(
            success=True,
            message="Person added with interests successfully",
            person_id=request.person_id
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topics file not found: {TOPICS_FILE}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=1234)
