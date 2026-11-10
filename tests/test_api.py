"""API integration tests using Starlette / FastAPI TestClient."""
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["total_restaurants"] > 0
    assert "cost_p33" in data
    assert "cost_p66" in data


def test_locations_and_cuisines():
    loc_res = client.get("/api/locations")
    assert loc_res.status_code == 200
    assert isinstance(loc_res.json(), list)
    assert len(loc_res.json()) > 0

    cui_res = client.get("/api/cuisines")
    assert cui_res.status_code == 200
    assert isinstance(cui_res.json(), list)
    assert len(cui_res.json()) > 0


def test_recommend_happy_path():
    payload = {
        "location": "Banashankari",
        "budget": "medium",
        "cuisine": "North Indian",
        "min_rating": 3.5,
        "additional_preferences": "family dining with table booking",
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0

    top = data["recommendations"][0]
    # Check 5 required display fields
    assert "name" in top and top["name"]
    assert "cuisine" in top and top["cuisine"]
    assert "rating" in top and top["rating"] >= 3.5
    assert "estimated_cost" in top and top["estimated_cost"] > 0
    assert "explanation" in top and len(top["explanation"]) > 0


def test_recommend_zero_matches_relax_filters():
    payload = {
        "location": "NowhereLandXYZ",
        "budget": "low",
        "cuisine": "UnknownCuisine",
        "min_rating": 4.9,
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) == 0
    assert data["message"] is not None
    assert "No restaurants found" in data["message"]
