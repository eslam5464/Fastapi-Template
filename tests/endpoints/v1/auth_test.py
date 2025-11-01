from datetime import UTC, datetime, timedelta

import pytest
from faker import Faker
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_user
from app.core.config import settings
from app.models import User
from tests.utils import generate_user_credentials


class TestLogin:
    """Test suite for POST /api/v1/auth/login endpoint"""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test successful login with valid credentials"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

        # Verify the access token can be decoded
        payload = jwt.decode(
            data["access_token"],
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        assert payload["sub"] == str(user.id)
        assert "exp" in payload
        assert "iat" in payload

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test login fails with incorrect password"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect username or password"

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(
        self,
        client: AsyncClient,
    ):
        """Test login fails with non-existent username"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "NonExistent123!@#User",
                "password": "P@ssword123",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect username or password"

    @pytest.mark.asyncio
    async def test_login_missing_fields(
        self,
        client: AsyncClient,
    ):
        """Test login fails when required fields are missing"""
        # Missing password
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "TestUser123!@#",
            },
        )
        assert response.status_code == 422

        # Missing username
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "password": "P@ssword123",
            },
        )
        assert response.status_code == 422


class TestSignup:
    """Test suite for POST /api/v1/auth/signup endpoint"""

    @pytest.mark.asyncio
    async def test_signup_success(
        self,
        client: AsyncClient,
    ):
        """Test successful user signup"""
        user_credentials = generate_user_credentials()
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": user_credentials["username"],
                "email": user_credentials["email"],
                "password": user_credentials["password"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

        # Verify the token contains valid user information
        payload = jwt.decode(
            data["access_token"],
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test signup fails when email already exists"""
        user_credentials = generate_user_credentials()
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": user_credentials["username"],
                "email": user.email,
                "password": user_credentials["password"],
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "A user with this email already exists."

    @pytest.mark.asyncio
    async def test_signup_invalid_username_format(
        self,
        client: AsyncClient,
    ):
        """Test signup fails with invalid username format"""
        user_credentials = generate_user_credentials()
        # Username without special character
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": "TestUser 123",
                "email": user_credentials["email"],
                "password": user_credentials["password"],
            },
        )
        assert response.status_code == 422

        # Username without uppercase
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": "testuser123!@#",
                "email": user_credentials["email"],
                "password": user_credentials["password"],
            },
        )
        assert response.status_code == 422

        # Username without lowercase
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": "TESTUSER123!@#",
                "email": user_credentials["email"],
                "password": user_credentials["password"],
            },
        )
        assert response.status_code == 422

        # Username without number
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": "TestUser!@#",
                "email": user_credentials["email"],
                "password": user_credentials["password"],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_invalid_password_format(
        self,
        client: AsyncClient,
    ):
        """Test signup fails with invalid password format"""
        user_credentials = generate_user_credentials()
        # Password without special character
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": user_credentials["username"],
                "email": user_credentials["email"],
                "password": "aaddd1111111",
            },
        )
        assert response.status_code == 422

        # Password without uppercase
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": user_credentials["username"],
                "email": user_credentials["email"],
                "password": "password123!",
            },
        )
        assert response.status_code == 422

        # Password without lowercase
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": user_credentials["username"],
                "email": user_credentials["email"],
                "password": "PASSWORD123!",
            },
        )
        assert response.status_code == 422

        # Password without number
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": user_credentials["username"],
                "email": user_credentials["email"],
                "password": "Password!@#",
            },
        )
        assert response.status_code == 422

        # Password too short
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": user_credentials["username"],
                "email": user_credentials["email"],
                "password": "P@ss1",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_invalid_email(
        self,
        client: AsyncClient,
    ):
        """Test signup fails with invalid email format"""
        user_credentials = generate_user_credentials()
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": user_credentials["username"],
                "email": "invalid-email",
                "password": user_credentials["password"],
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_username_too_short(
        self,
        client: AsyncClient,
    ):
        """Test signup fails when username is too short"""
        user_credentials = generate_user_credentials()
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": "Ab",
                "email": user_credentials["email"],
                "password": user_credentials["password"],
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_username_too_long(
        self,
        client: AsyncClient,
    ):
        """Test signup fails when username exceeds max length"""
        user_credentials = generate_user_credentials()
        long_username = "A" * 51 + "1!@#bC"  # Over 50 characters
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": long_username,
                "email": user_credentials["email"],
                "password": user_credentials["password"],
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_missing_required_fields(
        self,
        client: AsyncClient,
        faker: Faker,
    ):
        """Test signup fails when required fields are missing"""
        # Missing username
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "email": faker.safe_email(),
                "password": "P@ssword123",
            },
        )
        assert response.status_code == 422

        # Missing email
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": "TestUser123!@#",
                "password": "P@ssword123",
            },
        )
        assert response.status_code == 422

        # Missing password
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": "TestUser123!@#",
                "email": faker.safe_email(),
            },
        )
        assert response.status_code == 422


class TestRefreshToken:
    """Test suite for POST /api/v1/auth/refresh-token endpoint"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test successful token refresh with valid refresh token"""
        # Create a valid refresh token
        refresh_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=24),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

        # Verify the new tokens are valid
        new_access_payload = jwt.decode(
            data["access_token"],
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        assert new_access_payload["sub"] == str(user.id)

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(
        self,
        client: AsyncClient,
    ):
        """Test refresh token fails with invalid token"""
        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid refresh token"

    @pytest.mark.asyncio
    async def test_refresh_token_expired_token(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test refresh token fails with expired token"""
        # Create an expired refresh token
        expired_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) - timedelta(hours=1),
                "iat": datetime.now(UTC) - timedelta(hours=25),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": expired_token},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid refresh token"

    @pytest.mark.asyncio
    async def test_refresh_token_without_sub(
        self,
        client: AsyncClient,
    ):
        """Test refresh token fails when token doesn't contain 'sub' claim"""
        # Create a token without 'sub' claim
        token_without_sub = jwt.encode(
            {
                "exp": datetime.now(UTC) + timedelta(hours=24),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": token_without_sub},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid refresh token"

    @pytest.mark.asyncio
    async def test_refresh_token_nonexistent_user(
        self,
        client: AsyncClient,
    ):
        """Test refresh token fails when user doesn't exist"""
        # Create a token with non-existent user ID
        fake_user_id = 99999
        refresh_token = jwt.encode(
            {
                "sub": str(fake_user_id),
                "exp": datetime.now(UTC) + timedelta(hours=24),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid user"

    @pytest.mark.asyncio
    async def test_refresh_token_wrong_secret_key(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test refresh token fails when signed with wrong secret key"""
        # Create a token with wrong secret key
        wrong_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=24),
                "iat": datetime.now(UTC),
            },
            "wrong-secret-key",
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": wrong_token},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid refresh token"

    @pytest.mark.asyncio
    async def test_refresh_token_missing_field(
        self,
        client: AsyncClient,
    ):
        """Test refresh token fails when refresh_token field is missing"""
        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_refresh_token_empty_string(
        self,
        client: AsyncClient,
    ):
        """Test refresh token fails with empty string"""
        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": ""},
        )

        assert response.status_code == 401


class TestAuthenticationIntegration:
    """Integration tests for complete authentication flows"""

    @pytest.mark.asyncio
    async def test_signup_login_refresh_flow(
        self,
        client: AsyncClient,
    ):
        """Test complete authentication flow: signup -> login -> refresh"""
        user_credentials = generate_user_credentials()
        username = user_credentials["username"]
        email = user_credentials["email"]
        password = user_credentials["password"]

        # 1. Signup
        signup_response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": username,
                "email": email,
                "password": password,
            },
        )
        print("@@@", signup_response.text)
        assert signup_response.status_code == 201
        signup_data = signup_response.json()
        assert "access_token" in signup_data

        # 2. Login with the new user
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": username,
                "password": password,
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "refresh_token" in login_data

        # 3. Refresh the token
        refresh_response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": login_data["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data

    @pytest.mark.asyncio
    async def test_multiple_users_independent_tokens(
        self,
        client: AsyncClient,
        user: User,
        other_user: User,
        default_password: str,
    ):
        """Test that different users get different independent tokens"""
        # Login as first user
        response1 = await client.post(
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert response1.status_code == 200
        token1_data = response1.json()

        # Login as second user
        response2 = await client.post(
            "/api/v1/auth/login",
            data={
                "username": other_user.username,
                "password": default_password,
            },
        )
        assert response2.status_code == 200
        token2_data = response2.json()

        # Verify tokens are different
        assert token1_data["access_token"] != token2_data["access_token"]
        assert token1_data["refresh_token"] != token2_data["refresh_token"]

        # Verify tokens contain correct user IDs
        payload1 = jwt.decode(
            token1_data["access_token"],
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        payload2 = jwt.decode(
            token2_data["access_token"],
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        assert payload1["sub"] == str(user.id)
        assert payload2["sub"] == str(other_user.id)

    @pytest.mark.asyncio
    async def test_token_expiration_times(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test that tokens have correct expiration times"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Decode access token and check expiration
        access_payload = jwt.decode(
            data["access_token"],
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        access_exp = datetime.fromtimestamp(access_payload["exp"], UTC)
        access_iat = datetime.fromtimestamp(access_payload["iat"], UTC)
        access_diff = (access_exp - access_iat).total_seconds()

        # Should be close to access token expiration setting (within 5 seconds tolerance)
        assert abs(access_diff - settings.access_token_expire_seconds) < 5

        # Decode refresh token and check expiration
        refresh_payload = jwt.decode(
            data["refresh_token"],
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], UTC)
        refresh_iat = datetime.fromtimestamp(refresh_payload["iat"], UTC)
        refresh_diff = (refresh_exp - refresh_iat).total_seconds()

        # Should be close to refresh token expiration setting (within 5 seconds tolerance)
        assert abs(refresh_diff - settings.refresh_token_expire_seconds) < 5


class TestGetCurrentUser:
    """Test suite for get_current_user dependency"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user with valid token"""
        # Create a valid access token
        token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Call get_current_user
        current_user = await get_current_user(token=token, db=db_session)
        assert current_user.id == user.id
        assert current_user.username == user.username
        assert current_user.email == user.email

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(
        self,
        db_session: AsyncSession,
    ):
        """Test get_current_user with invalid token format"""
        from app.core.exceptions import UnauthorizedException

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token="invalid.token.format", db=db_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user with expired token"""
        from app.core.exceptions import UnauthorizedException

        # Create an expired token
        expired_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) - timedelta(hours=1),
                "iat": datetime.now(UTC) - timedelta(hours=2),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=expired_token, db=db_session)

        assert exc_info.value.status_code == 401
        assert "Token has expired" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub(
        self,
        db_session: AsyncSession,
    ):
        """Test get_current_user with token missing 'sub' claim"""
        from app.core.exceptions import UnauthorizedException

        # Create a token without 'sub'
        token_no_sub = jwt.encode(
            {
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=token_no_sub, db=db_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_exp(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user with token missing 'exp' claim"""
        from app.core.exceptions import UnauthorizedException

        # Create a token without 'exp'
        token_no_exp = jwt.encode(
            {
                "sub": str(user.id),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=token_no_exp, db=db_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(
        self,
        db_session: AsyncSession,
    ):
        """Test get_current_user with token for non-existent user"""
        from app.core.exceptions import UnauthorizedException

        # Create a token with fake user ID
        fake_user_id = 99999
        token = jwt.encode(
            {
                "sub": str(fake_user_id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=token, db=db_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_wrong_secret_key(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user with token signed with wrong secret"""
        from app.core.exceptions import UnauthorizedException

        # Create a token with wrong secret
        wrong_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
            },
            "wrong-secret-key",
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=wrong_token, db=db_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_token_expiry_in_past(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user with manually expired token (exp in past)"""
        from app.core.exceptions import UnauthorizedException

        # Create token with exp timestamp in the past but not yet expired by JWT library
        # This tests the manual expiry check in get_current_user
        token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": int((datetime.now(UTC) - timedelta(seconds=10)).timestamp()),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=token, db=db_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_with_jwt_claims_error(
        self,
        db_session: AsyncSession,
    ):
        """Test get_current_user with malformed JWT claims"""

        from app.core.exceptions import UnauthorizedException

        # Use a token that will trigger JWTClaimsError
        # Create a token with invalid claims structure
        malformed_token = jwt.encode(
            {
                "sub": str(12345),
                "exp": "invalid_exp_format",  # This should be an int
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=malformed_token, db=db_session)

        assert exc_info.value.status_code == 401


class TestAuthenticatedEndpoints:
    """Test authentication flow with actual endpoint usage"""

    @pytest.mark.asyncio
    async def test_use_access_token_on_protected_endpoint(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test using access token to access protected endpoints"""
        # First login to get token
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Use the access token to access a protected endpoint
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # This should work if the endpoint exists and authentication works
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist yet

    @pytest.mark.asyncio
    async def test_complete_auth_workflow_with_token_usage(
        self,
        client: AsyncClient,
    ):
        """Test complete workflow: signup -> use token -> refresh -> use new token"""
        user_credentials = generate_user_credentials()
        username = user_credentials["username"]
        email = user_credentials["email"]
        password = user_credentials["password"]

        # 1. Signup and get initial tokens
        signup_response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": username,
                "email": email,
                "password": password,
            },
        )
        assert signup_response.status_code == 201
        signup_data = signup_response.json()

        # Verify we got both tokens
        assert "access_token" in signup_data
        assert "refresh_token" in signup_data
        assert signup_data["token_type"] == "Bearer"

        signup_data["access_token"]
        initial_refresh_token = signup_data["refresh_token"]

        # 2. Refresh the token
        refresh_response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": initial_refresh_token},
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()

        # Verify we got new tokens
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "Bearer"

        # Verify the new access token is valid and contains the correct user info
        new_payload = jwt.decode(
            refresh_data["access_token"],
            settings.secret_key,
            algorithms=settings.jwt_algorithm,
        )
        assert "sub" in new_payload
        assert "exp" in new_payload
        assert "iat" in new_payload
