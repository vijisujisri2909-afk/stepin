from django.contrib.auth.models import User
from django.test import TestCase


class AccountLoginTests(TestCase):
    def test_login_with_email_and_password_redirects_to_home(self):
        email = "login-check@example.com"
        password = "A-safe-test-password-23!"
        User.objects.create_user(username=email, email=email, password=password)

        response = self.client.post(
            "/account/login/",
            {"email": email, "password": password},
        )

        self.assertRedirects(response, "/")
        self.assertTrue(
            self.client.session.get("_auth_user_id"),
            "A successful login should establish an authenticated session.",
        )

    def test_login_with_invalid_credentials_shows_message(self):
        response = self.client.post(
            "/account/login/",
            {"email": "missing@example.com", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The email or password is incorrect.")

    def test_registered_account_can_log_in(self):
        email = "new-account@example.com"
        password = "Another-safe-test-password-48!"
        registration = self.client.post(
            "/account/register/",
            {
                "name": "New Account",
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )
        self.assertRedirects(registration, "/")

        self.client.logout()
        login_response = self.client.post(
            "/account/login/",
            {"email": email, "password": password},
        )

        self.assertRedirects(login_response, "/")
        self.assertTrue(self.client.session.get("_auth_user_id"))

# Create your tests here.
