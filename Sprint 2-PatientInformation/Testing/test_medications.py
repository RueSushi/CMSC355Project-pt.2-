import unittest
from login import app  

class TestMedications(unittest.TestCase):
    def setUp(self):
        # Setup your app and test client
        self.app = app.test_client()
        self.app.testing = True

        # Register a test user (you can modify this if needed)
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

    def test_medications_page(self):
        # Now that the user is logged in, you can access the medications page
        response = self.app.get('/medications')
        self.assertEqual(response.status_code, 200)  # Should now get a 200 response

    def test_add_medication(self):
        response = self.app.post('/medications', data=dict(
            medication="Aspirin",
            frequency="once_a_day",
            start_date="2025-04-10"
        ))
        self.assertIn("Medication 'Aspirin' added with once_a_day frequency starting on 2025-04-10.", response.data.decode())


if __name__ == '__main__':
    unittest.main()

