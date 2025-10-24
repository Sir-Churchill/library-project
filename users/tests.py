from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

REGISTER_URL = reverse("users:register")
TOKEN_URL = reverse("users:token_obtain_pair")
TOKEN_REFRESH_URL = reverse("users:token_refresh")
ME_URL = reverse("users:me")


class CustomUserManagerTests(TestCase):
    """Test the CustomUserManager"""

    def test_create_user_with_email(self):
        """Test creating a user with an email is successful"""
        email = "test@example.com"
        password = "testpass123"
        user = User.objects.create_user(email=email, password=password)

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_with_normalized_email(self):
        """Test email is normalized for new users"""
        sample_emails = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@Example.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.COM", "TEST3@example.com"],
        ]

        for email, expected in sample_emails:
            user = User.objects.create_user(email, "sample123")
            self.assertEqual(user.email, expected)

    def test_create_user_without_email_raises_error(self):
        """Test that creating a user without an email raises a ValueError"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(email="", password="testpass123")

        self.assertIn("The Email must be set", str(context.exception))

    def test_create_superuser(self):
        """Test creating a superuser"""
        email = "admin@example.com"
        password = "testpass123"
        user = User.objects.create_superuser(email=email, password=password)

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser_with_is_staff_false_raises_error(self):
        """Test creating superuser with is_staff=False raises error"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(
                email="admin@example.com", password="test123", is_staff=False
            )

        self.assertIn("Superuser must have is_staff=True", str(context.exception))

    def test_create_superuser_with_is_superuser_false_raises_error(self):
        """Test creating superuser with is_superuser=False raises error"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(
                email="admin@example.com", password="test123", is_superuser=False
            )

        self.assertIn("Superuser must have is_superuser=True", str(context.exception))


class CustomerModelTests(TestCase):
    """Test the Customer model"""

    def test_customer_has_no_username_field(self):
        """Test that Customer model doesn't use username"""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.assertIsNone(user.username)

    def test_email_is_unique(self):
        """Test that email must be unique"""
        email = "test@example.com"
        User.objects.create_user(email=email, password="testpass123")

        with self.assertRaises(Exception):
            User.objects.create_user(email=email, password="anotherpass123")

    def test_username_field_is_email(self):
        """Test that USERNAME_FIELD is set to email"""
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_required_fields_is_empty(self):
        """Test that REQUIRED_FIELDS is empty"""
        self.assertEqual(User.REQUIRED_FIELDS, [])


class UserSerializerTests(TestCase):
    """Test the UserSerializer"""

    def test_serialize_user(self):
        """Test serializing a user"""
        from users.serializers import UserSerializer

        user = User.objects.create_user(
            email="test@example.com", password="testpass123", is_staff=False
        )

        serializer = UserSerializer(user)
        data = serializer.data

        self.assertEqual(data["email"], user.email)
        self.assertEqual(data["is_staff"], False)
        self.assertIn("id", data)
        self.assertNotIn("password", data)  # Password should not be in output

    def test_create_user_with_serializer(self):
        """Test creating a user with the serializer"""
        from users.serializers import UserSerializer

        payload = {
            "email": "test@example.com",
            "password": "testpass123",
        }

        serializer = UserSerializer(data=payload)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()

        self.assertEqual(user.email, payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", serializer.data)

    def test_password_min_length_validation(self):
        """Test that password must be at least 8 characters"""
        from users.serializers import UserSerializer

        payload = {
            "email": "test@example.com",
            "password": "short",
        }

        serializer = UserSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_update_user_password(self):
        """Test updating a user's password"""
        from users.serializers import UserSerializer

        user = User.objects.create_user(
            email="test@example.com", password="oldpassword123"
        )

        payload = {"password": "newpassword123"}
        serializer = UserSerializer(user, data=payload, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_user = serializer.save()

        self.assertTrue(updated_user.check_password(payload["password"]))
        self.assertFalse(updated_user.check_password("oldpassword123"))

    def test_update_user_email(self):
        """Test updating a user's email"""
        from users.serializers import UserSerializer

        user = User.objects.create_user(email="old@example.com", password="testpass123")

        payload = {"email": "new@example.com"}
        serializer = UserSerializer(user, data=payload, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_user = serializer.save()

        self.assertEqual(updated_user.email, "new@example.com")

    def test_is_staff_is_read_only(self):
        """Test that is_staff field is read-only"""
        from users.serializers import UserSerializer

        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "is_staff": True,  # Should be ignored
        }

        serializer = UserSerializer(data=payload)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()

        self.assertFalse(user.is_staff)  # Should remain False


class PublicUserApiTests(APITestCase):
    """Test the public (unauthenticated) user API"""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful"""
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
        }

        response = self.client.post(REGISTER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", response.data)

    def test_user_with_email_exists_error(self):
        """Test error returned if user with email exists"""
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
        }
        User.objects.create_user(**payload)

        response = self.client.post(REGISTER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test an error is returned if password less than 8 chars"""
        payload = {
            "email": "test@example.com",
            "password": "pw",
        }

        response = self.client.post(REGISTER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = User.objects.filter(email=payload["email"]).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test generating token for valid credentials"""
        user_details = {
            "email": "test@example.com",
            "password": "testpass123",
        }
        User.objects.create_user(**user_details)

        payload = {
            "email": user_details["email"],
            "password": user_details["password"],
        }
        response = self.client.post(TOKEN_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_create_token_bad_credentials(self):
        """Test returns error if credentials invalid"""
        User.objects.create_user(email="test@example.com", password="goodpass123")

        payload = {"email": "test@example.com", "password": "badpass"}
        response = self.client.post(TOKEN_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def test_create_token_blank_password(self):
        """Test posting a blank password returns an error"""
        payload = {"email": "test@example.com", "password": ""}
        response = self.client.post(TOKEN_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("access", response.data)

    def test_refresh_token(self):
        """Test refreshing JWT token"""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        refresh = RefreshToken.for_user(user)

        payload = {"refresh": str(refresh)}
        response = self.client.post(TOKEN_REFRESH_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_token_invalid(self):
        """Test refreshing with invalid token fails"""
        payload = {"refresh": "invalidtoken"}
        response = self.client.post(TOKEN_REFRESH_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_user_unauthorized(self):
        """Test that authentication is required for users"""
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(APITestCase):
    """Test API requests that require authentication"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user"""
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertIn("id", response.data)
        self.assertNotIn("password", response.data)

    def test_post_me_not_allowed(self):
        """Test POST is not allowed on the me endpoint"""
        response = self.client.post(ME_URL, {})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile_not_allowed(self):
        """Test updating the user profile for authenticated user is not allowed"""
        # ManageUserView is RetrieveAPIView, so PUT/PATCH should not be allowed
        payload = {"email": "newemail@example.com"}

        response = self.client.patch(ME_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.put(ME_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class UserAuthenticationTests(APITestCase):
    """Test user authentication flows"""

    def setUp(self):
        self.client = APIClient()

    def test_full_registration_and_login_flow(self):
        """Test complete user registration and login flow"""
        # Register a new user
        register_payload = {
            "email": "newuser@example.com",
            "password": "newpass123",
        }
        register_response = self.client.post(REGISTER_URL, register_payload)
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        # Login with the new user
        login_payload = {
            "email": "newuser@example.com",
            "password": "newpass123",
        }
        token_response = self.client.post(TOKEN_URL, login_payload)
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)
        self.assertIn("refresh", token_response.data)

        # Access protected endpoint with token
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token_response.data["access"]}'
        )
        me_response = self.client.get(ME_URL)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], "newuser@example.com")

    def test_token_refresh_flow(self):
        """Test refreshing access token"""
        # Create user and get initial tokens
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        refresh = RefreshToken.for_user(user)

        # Use refresh token to get new access token
        payload = {"refresh": str(refresh)}
        response = self.client.post(TOKEN_REFRESH_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        # Use new access token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        me_response = self.client.get(ME_URL)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)

    def test_invalid_token_access_denied(self):
        """Test that invalid token is rejected"""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalidtoken")
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_token_access_denied(self):
        """Test that request without token is rejected"""
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
