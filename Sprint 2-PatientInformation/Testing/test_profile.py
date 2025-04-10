import unittest
from login import app  # Import your actual app here

class ProfileTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()  # Set up the Flask test client
        self.app.testing = True  # Enable testing mode

        # Register a test user
        self.app.post('/register', data=dict(
            first_name="John",
            last_name="Doe",
            email="testuser@example.com",
            password="testpass123"
        ))

        # Log in the test user
        self.app.post('/login', data=dict(
            email="testuser@example.com",
            password="testpass123"
        ))

    def test_update_profile_success(self):
        """Test successfully updating the profile."""
        response = self.app.post('/profile', data=dict(
            first_name="John",
            last_name="Doe",
            email="newemail@example.com",  # Valid email
            password="newpass123"
        ))
        self.assertIn('/dashboard', response.headers['Location'])  # Check redirection to dashboard

    def test_update_profile_invalid_email(self):
        """Test updating the profile with an invalid email format."""
        response = self.app.post('/profile', data=dict(
            first_name="John",
            last_name="Doe",
            email="invalid-email",  # Invalid email format
            password="newpass123"
        ))
        self.assertEqual(response.status_code, 400)  # Expect a 400 status code for invalid email

    def test_update_profile_empty_fields(self):
        """Test updating the profile with missing required fields."""
        response = self.app.post('/profile', data=dict(
            first_name="",  # Empty first name
            last_name="Doe",
            email="newemail@example.com",
            password="newpass123"
        ))
        self.assertEqual(response.status_code, 400)  # Expect a 400 status code for missing fields

    def test_update_profile_password_too_short(self):
        """Test updating the profile with a short password."""
        response = self.app.post('/profile', data=dict(
            first_name="John",
            last_name="Doe",
            email="newemail@example.com",
            password="short"  # Invalid password (too short)
        ))
        self.assertEqual(response.status_code, 400)  # Expect a 400 status code for short password

if __name__ == '__main__':
    unittest.main()
