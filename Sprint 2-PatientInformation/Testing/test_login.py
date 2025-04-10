import unittest
from login import app, save_users, load_users  # Fixed import statement
from flask import Flask
from flask.testing import FlaskClient

# Custom test runner to change "ok" to "PASS"
class CustomTestRunner(unittest.TextTestRunner):
    def _makeResult(self):
        result = super()._makeResult()
        result.failfast = False  # Disable failfast (optional)
        return result

    def run(self, test):
        result = super().run(test)
        # Change "ok" to "PASS" for passing tests
        for test, outcome in zip(result.testsRun, result.errors):
            if outcome == []:
                print(f"{test} ... PASS")
            else:
                print(f"{test} ... FAIL")
        return result

# Define a test case class for Positive Test Cases
class FlaskPositiveTestCase(unittest.TestCase):
    def setUp(self):
        """Setup the Flask test client and other setup operations."""
        self.app = app.test_client()
        self.app.testing = True

    def test_register_success(self):
        """Test successful user registration."""
        response = self.app.post('/register', data={
            'email': 'newuser@example.com',
            'password': 'ValidPass1!'
        })
        self.assertEqual(response.status_code, 302)  # Expect redirection after successful registration
        self.assertIn('/login', response.headers['Location'])  # Check that it redirects to login

    def test_login_success(self):
        """Test successful login."""
        self.app.post('/register', data={
            'email': 'testuser@example.com',
            'password': 'ValidPass1!'
        })
        response = self.app.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'ValidPass1!'
        })
        self.assertEqual(response.status_code, 302)  # Expect redirection
        self.assertIn('/dashboard', response.headers['Location'])  # Check redirection to dashboard

    def test_dashboard_access_with_login(self):
        """Test accessing the dashboard after login."""
        self.app.post('/register', data={
            'email': 'testuser@example.com',
            'password': 'ValidPass1!'
        })
        self.app.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'ValidPass1!'
        })
        response = self.app.get('/dashboard')
        self.assertEqual(response.status_code, 200)  # Dashboard should be accessible

    def test_logout(self):
        """Test logging out successfully."""
        self.app.post('/register', data={
            'email': 'testuser@example.com',
            'password': 'ValidPass1!'
        })
        self.app.post('/login', data={
            'email': 'testuser@example.com',
            'password': 'ValidPass1!'
        })
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)  # Expect redirection
        self.assertIn('/', response.headers['Location'])  # Check redirect to home page

# Define a test case class for Negative Test Cases
class FlaskNegativeTestCase(unittest.TestCase):
    def setUp(self):
        """Setup the Flask test client and other setup operations."""
        self.app = app.test_client()
        self.app.testing = True

    def test_register_invalid_email(self):
        """Test invalid email format."""
        response = self.app.post('/register', data={
            'email': 'invalid_email',
            'password': 'ValidPass1!'
        })
        self.assertEqual(response.status_code, 200)  # Expect no redirection
        self.assertIn(b"Invalid email format!", response.data)

    def test_register_existing_email(self):
        """Test registering with an already existing email."""
        self.app.post('/register', data={
            'email': 'test@example.com',
            'password': 'ValidPass1!'
        })
        response = self.app.post('/register', data={
            'email': 'test@example.com',
            'password': 'AnotherPass1!'
        })
        self.assertEqual(response.status_code, 200)  # Expect no redirection
        self.assertIn(b"Email already registered!", response.data)

    def test_login_wrong_password(self):
        """Test login with the wrong password."""
        self.app.post('/register', data={
            'email': 'test@example.com',
            'password': 'ValidPass1!'
        })
        response = self.app.post('/login', data={
            'email': 'test@example.com',
            'password': 'WrongPass'
        })
        self.assertEqual(response.status_code, 302)  # Expect redirection
        self.assertIn('/', response.headers['Location'])  # Check redirection to home page

    def test_login_unregistered_email(self):
        """Test login with an unregistered email."""
        response = self.app.post('/login', data={
            'email': 'unregistered@example.com',
            'password': 'SomePass1!'
        })
        self.assertEqual(response.status_code, 302)  # Expect redirection
        self.assertIn('/', response.headers['Location'])  # Check redirection to home page

    def test_dashboard_access_without_login(self):
        """Test if a user can access the dashboard without logging in."""
        response = self.app.get('/dashboard')
        self.assertEqual(response.status_code, 302)  # Expect redirection to login page

    def test_logout_without_login(self):
        """Test logging out without being logged in."""
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)  # Expect redirection
        self.assertIn('/', response.headers['Location'])  # Check redirection to home page

# If running the tests as a script
if __name__ == '__main__':
    unittest.main(testRunner=CustomTestRunner())
