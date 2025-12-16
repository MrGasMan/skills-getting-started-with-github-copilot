"""
Tests for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    activities.clear()
    activities.update({
        "Soccer Team": {
            "description": "Join our competitive soccer team and play in local tournaments",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 6:00 PM",
            "max_participants": 25,
            "participants": ["alex@mergington.edu", "sam@mergington.edu"]
        },
        "Basketball Club": {
            "description": "Practice basketball skills and participate in inter-school games",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": []
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root redirects to the static index page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        
    def test_get_activities_includes_correct_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        soccer = data["Soccer Team"]
        assert "description" in soccer
        assert "schedule" in soccer
        assert "max_participants" in soccer
        assert "participants" in soccer
        assert soccer["max_participants"] == 25
        assert len(soccer["participants"]) == 2


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Basketball Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that duplicate signup returns 400"""
        email = "alex@mergington.edu"
        response = client.post(
            f"/activities/Soccer%20Team/signup?email={email}"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_multiple_participants(self, client):
        """Test adding multiple participants to an activity"""
        emails = ["student1@mergington.edu", "student2@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/Basketball%20Club/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all participants were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        participants = activities_data["Basketball Club"]["participants"]
        
        for email in emails:
            assert email in participants


class TestRemoveParticipant:
    """Tests for the DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_successful(self, client):
        """Test successful removal of a participant"""
        response = client.delete(
            "/activities/Soccer%20Team/participants/alex@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "alex@mergington.edu" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Soccer Team"]["participants"]
    
    def test_remove_participant_nonexistent_activity(self, client):
        """Test removing participant from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/participants/test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_remove_nonexistent_participant(self, client):
        """Test removing non-existent participant returns 404"""
        response = client.delete(
            "/activities/Soccer%20Team/participants/nonexistent@mergington.edu"
        )
        assert response.status_code == 404
        assert "Participant not found" in response.json()["detail"]
    
    def test_remove_last_participant(self, client):
        """Test removing the last participant from an activity"""
        # First, remove one participant
        client.delete("/activities/Soccer%20Team/participants/alex@mergington.edu")
        
        # Then remove the second one
        response = client.delete("/activities/Soccer%20Team/participants/sam@mergington.edu")
        assert response.status_code == 200
        
        # Verify no participants remain
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert len(activities_data["Soccer Team"]["participants"]) == 0


class TestActivityWorkflow:
    """Integration tests for complete workflows"""
    
    def test_signup_and_remove_workflow(self, client):
        """Test complete workflow of signing up and removing a participant"""
        email = "workflow@mergington.edu"
        activity = "Basketball Club"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        get_response = client.get("/activities")
        assert email in get_response.json()[activity]["participants"]
        
        # Remove
        delete_response = client.delete(
            f"/activities/{activity.replace(' ', '%20')}/participants/{email}"
        )
        assert delete_response.status_code == 200
        
        # Verify removal
        final_response = client.get("/activities")
        assert email not in final_response.json()[activity]["participants"]
