"""
Tests for the Mergington High School Activities FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities data before each test."""
    # Store original activities
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Reset activities after test
    activities.clear()
    activities.update(original_activities)


class TestActivitiesEndpoints:
    """Test class for activities-related endpoints."""

    def test_get_activities(self, client):
        """Test getting all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Check that we get a dictionary of activities
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check structure of first activity
        first_activity = list(data.values())[0]
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
        assert isinstance(first_activity["participants"], list)

    def test_root_redirects_to_static(self, client):
        """Test that root path redirects to static files."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestSignupEndpoint:
    """Test class for signup functionality."""

    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity."""
        activity_name = "Chess Club"
        email = "test@mergington.edu"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == f"Signed up {email} for {activity_name}"
        
        # Verify the participant was added
        assert email in activities[activity_name]["participants"]

    def test_signup_for_nonexistent_activity(self, client, reset_activities):
        """Test signup for an activity that doesn't exist."""
        activity_name = "Nonexistent Activity"
        email = "test@mergington.edu"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test signing up the same participant twice."""
        activity_name = "Chess Club"
        email = "test@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert data["detail"] == "Student already signed up for this activity"

    def test_signup_with_existing_participant(self, client, reset_activities):
        """Test signup when participant already exists in the activity."""
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(f"/activities/{activity_name}/signup?email={existing_email}")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"


class TestUnregisterEndpoint:
    """Test class for unregister functionality."""

    def test_unregister_from_activity_success(self, client, reset_activities):
        """Test successful unregistration from an activity."""
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already registered
        
        # Verify participant is initially registered
        assert email in activities[activity_name]["participants"]
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == f"Unregistered {email} from {activity_name}"
        
        # Verify the participant was removed
        assert email not in activities[activity_name]["participants"]

    def test_unregister_from_nonexistent_activity(self, client, reset_activities):
        """Test unregistration from an activity that doesn't exist."""
        activity_name = "Nonexistent Activity"
        email = "test@mergington.edu"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_unregister_nonexistent_participant(self, client, reset_activities):
        """Test unregistering a participant who isn't registered."""
        activity_name = "Chess Club"
        email = "notregistered@mergington.edu"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is not registered for this activity"


class TestIntegrationScenarios:
    """Test class for integration scenarios."""

    def test_signup_and_unregister_flow(self, client, reset_activities):
        """Test the complete flow of signup and unregister."""
        activity_name = "Programming Class"
        email = "integration_test@mergington.edu"
        
        # Initial state - participant should not be registered
        assert email not in activities[activity_name]["participants"]
        
        # Step 1: Sign up
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        assert email in activities[activity_name]["participants"]
        
        # Step 2: Unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200
        assert email not in activities[activity_name]["participants"]

    def test_multiple_participants_same_activity(self, client, reset_activities):
        """Test multiple participants can sign up for the same activity."""
        activity_name = "Gym Class"
        emails = ["test1@mergington.edu", "test2@mergington.edu", "test3@mergington.edu"]
        
        # Sign up all participants
        for email in emails:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200
            assert email in activities[activity_name]["participants"]
        
        # Verify all are registered
        for email in emails:
            assert email in activities[activity_name]["participants"]
        
        # Unregister one participant
        response = client.delete(f"/activities/{activity_name}/unregister?email={emails[0]}")
        assert response.status_code == 200
        assert emails[0] not in activities[activity_name]["participants"]
        
        # Verify others are still registered
        for email in emails[1:]:
            assert email in activities[activity_name]["participants"]

    def test_activity_data_integrity(self, client, reset_activities):
        """Test that activity data remains consistent after operations."""
        # Get initial activities data
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        
        activity_name = "Art Club"
        email = "integrity_test@mergington.edu"
        
        # Perform signup
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Get updated activities data
        updated_response = client.get("/activities")
        updated_data = updated_response.json()
        
        # Verify only the participants list changed
        for name, details in initial_data.items():
            if name == activity_name:
                # For the test activity, participants should have one more entry
                assert len(updated_data[name]["participants"]) == len(details["participants"]) + 1
                assert email in updated_data[name]["participants"]
            else:
                # For other activities, data should be unchanged
                assert updated_data[name] == details