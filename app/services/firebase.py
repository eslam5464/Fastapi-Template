import asyncio
from dataclasses import dataclass, field

import firebase_admin
from firebase_admin import App, auth, credentials, messaging
from firebase_admin.auth import ListUsersPage, UserNotFoundError, UserRecord
from firebase_admin.credentials import Certificate
from firebase_admin.exceptions import FirebaseError
from loguru import logger

from app.core.config import settings
from app.schemas.firebase import FirebaseServiceAccount


@dataclass
class Firebase:
    _default_app: App | None = field(init=False, default=None)
    _app_certificate: Certificate | None = field(init=False, default=None)

    def __init__(self, service_account: FirebaseServiceAccount | None = None):
        """
        Initialize Firebase app

        Args:
            service_account (FirebaseServiceAccount | None): Firebase service account credentials.
        """
        try:
            firebase_admin.get_app()
            app_exists = True
        except ValueError:
            app_exists = False

        try:
            if app_exists is False:
                if service_account is None:
                    service_account = settings.firebase_credentials

                self._app_certificate = credentials.Certificate(service_account.model_dump())
                self._default_app = firebase_admin.initialize_app(
                    credential=self._app_certificate,
                )
        except IOError as err:
            logger.critical("Error initializing Firebase app, certificate file not found")
            logger.debug(str(err))
            raise err
        except ValueError as err:
            logger.critical("Error initializing Firebase app")
            logger.debug(str(err))
            raise err
        except Exception as err:
            logger.critical("Error initializing Firebase app, unknown error")
            logger.debug(str(err))
            raise err

    @property
    def app(self) -> App:
        """
        Get the default Firebase app instance.

        Returns:
            App: The default Firebase app instance.

        Raises:
            ValueError: If the Firebase app is not initialized.
        """
        if self._default_app is None:
            logger.error("Firebase app not initialized")
            raise ValueError("Firebase app not initialized")

        return self._default_app

    async def get_user_by_id(self, user_id: str) -> UserRecord:
        """
        Fetch user by ID

        Args:
            user_id (str): The user ID to fetch

        Returns:
            UserRecord: The user record for the given ID

        Raises:
            ValueError: If user_id is malformed
            ConnectionAbortedError: If the user is not found
            ConnectionError: If there is an error getting the user
        """

        def _get_user():
            return auth.get_user(
                uid=user_id,
                app=self._default_app,
            )

        try:
            return await asyncio.to_thread(_get_user)
        except ValueError as err:
            logger.error("Error getting user by ID, user ID is malformed")
            logger.debug(str(err))
            raise err
        except UserNotFoundError as err:
            logger.error("Error getting user by ID, User not found")
            logger.debug(str(err))
            raise ConnectionAbortedError("User not found")
        except FirebaseError as err:
            logger.error("Error getting user by ID")
            logger.debug(str(err))
            raise ConnectionError("Unknown error getting user by ID")

    async def get_user_by_email(self, email: str) -> UserRecord:
        """
        Fetch user by email address

        Args:
            email (str): The email address to fetch

        Returns:
            UserRecord: The user record for the given email

        Raises:
            ValueError: If email is malformed
            ConnectionAbortedError: If the user is not found
            ConnectionError: If there is an error getting the user
        """

        def _get_user():
            return auth.get_user_by_email(
                email=email,
                app=self._default_app,
            )

        try:
            return await asyncio.to_thread(_get_user)
        except ValueError as err:
            logger.error("Error getting user by email, email is malformed")
            logger.debug(str(err))
            raise err
        except UserNotFoundError as err:
            logger.error("Error getting user by email, User not found")
            logger.debug(str(err))
            raise ConnectionAbortedError("User not found")
        except FirebaseError as err:
            logger.error("Error getting user by email")
            logger.debug(str(err))
            raise ConnectionError("Unknown error getting user by email")

    async def get_user_by_phone_number(self, phone_number: str) -> UserRecord:
        """
        Fetch user by phone number

        Args:
            phone_number (str): The phone number to fetch

        Returns:
            UserRecord: The user record for the given phone number

        Raises:
            ValueError: If phone number is malformed
            ConnectionAbortedError: If the user is not found
            ConnectionError: If there is an error getting the user
        """

        def _get_user():
            return auth.get_user_by_phone_number(
                phone_number=phone_number,
                app=self._default_app,
            )

        try:
            return await asyncio.to_thread(_get_user)
        except ValueError as err:
            logger.error("Error getting user by phone number, phone number is malformed")
            logger.debug(str(err))
            raise err
        except UserNotFoundError as err:
            logger.error("Error getting user by phone number, User not found")
            logger.debug(str(err))
            raise ConnectionAbortedError("User not found")
        except FirebaseError as err:
            logger.error("Error getting user by phone number")
            logger.debug(str(err))
            raise ConnectionError("Unknown error getting user by phone number")

    async def get_all_users(self, max_results: int = 1000) -> ListUsersPage:
        """
        Fetch all users

        Args:
            max_results (int): Maximum number of users to fetch

        Returns:
            ListUsersPage: An iterable page of user records

        Raises:
            ValueError: If max_results is malformed
            ConnectionError: If there is an error getting all users
        """

        def _list_users():
            return auth.list_users(app=self._default_app, max_results=max_results)

        try:
            return await asyncio.to_thread(_list_users)
        except ValueError as err:
            logger.error("Error getting all users, max_results is malformed")
            logger.debug(str(err))
            raise err
        except FirebaseError as err:
            logger.error("Error getting all users")
            logger.debug(str(err))
            raise ConnectionError("Unknown error getting all users")

    async def create_custom_id_token(
        self, uid: str, additional_claims: dict | None = None
    ) -> bytes:
        """
        Create a custom ID token for a user

        Args:
            uid (str): The user ID for whom to create the token
            additional_claims (dict | None): Additional claims to include in the token

        Returns:
            bytes: The created custom ID token

        Raises:
            ValueError: If UID is malformed
            ConnectionError: If there is an error creating the custom ID token
        """

        def _create_token():
            return auth.create_custom_token(
                uid=uid,
                developer_claims=additional_claims,
                app=self._default_app,
            )

        try:
            return await asyncio.to_thread(_create_token)
        except ValueError as err:
            logger.error("Error creating custom ID token, UID is malformed")
            logger.debug(str(err))
            raise err
        except FirebaseError as err:
            logger.error("Error creating custom ID token")
            logger.debug(str(err))
            raise ConnectionError("Unknown error creating custom ID token")

    async def verify_id_token(self, id_token: str) -> dict:
        """
        Verify ID token

        Args:
            id_token (str): The ID token to verify

        Returns:
            dict: The decoded token claims

        Raises:
            ValueError: If ID token is malformed
            ConnectionError: If there is an error verifying the ID token
            ConnectionAbortedError: If the ID token has expired or been revoked
        """

        def _verify_token():
            return auth.verify_id_token(
                id_token=id_token,
                app=self._default_app,
            )

        try:
            return await asyncio.to_thread(_verify_token)
        except ValueError as err:
            logger.error("Error verifying ID token, ID token is malformed")
            logger.debug(str(err))
            raise err
        except auth.RevokedIdTokenError as err:
            logger.error("Error verifying ID token, ID token has been revoked")
            logger.debug(str(err))
            raise ConnectionAbortedError("ID token has been revoked")
        except auth.ExpiredIdTokenError as err:
            logger.error("Error verifying ID token, ID token has expired")
            logger.debug(str(err))
            raise ConnectionAbortedError("ID token has expired")
        except auth.InvalidIdTokenError as err:
            logger.error("Error verifying ID token, Invalid ID token")
            logger.debug(str(err))
            raise ConnectionAbortedError("Invalid ID token")
        except FirebaseError as err:
            logger.error("Unknown error verifying ID token")
            logger.debug(str(err))
            raise ConnectionError("Error verifying ID token")

    async def validate_fcm_token(self, registration_token: str):
        """
        validate FCM token (Firebase Cloud Messaging token / device token)

        Args:
            registration_token (str): The FCM token to validate

        Returns:
            bool: True if the token is valid, False otherwise
        """

        def _validate_token():
            return messaging.send(
                messaging.Message(token=registration_token, data={"test": "validation"}),
                dry_run=True,
                app=self._default_app,
            )

        try:
            await asyncio.to_thread(_validate_token)
            return True
        except FirebaseError as err:
            logger.error("Firebase error validating token")
            logger.debug(str(err))
            return False
        except ValueError as err:
            logger.error("Token is malformed")
            logger.debug(str(err))
            return False
        except Exception as e:
            logger.error(f"Error validating token")
            logger.debug(str(e))
            return False

    async def notify_a_device(
        self,
        device_token: str,
        title: str,
        content: str,
    ) -> bool:
        """
        Send notification to a specific device

        Args:
            device_token (str): The device token to send the notification to
            title (str): The title of the notification
            content (str): The content of the notification

        Returns:
            bool: True if the notification was sent successfully, False otherwise

        Raises:
            Exception: If there is an error sending the notification
        """

        def _send_notification():
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=content,
                ),
                token=device_token,
            )
            return messaging.send(
                message=message,
                app=self._default_app,
            )

        try:
            response = await asyncio.to_thread(_send_notification)
            logger.info(f"Push notification sent successfully: {response}")
            return True
        except Exception as e:
            logger.error(f"Error sending push notification")
            logger.debug(str(e))
            return False

    async def notify_multiple_devices(
        self,
        device_tokens: list[str],
        title: str,
        content: str,
    ) -> int:
        """
        Send notification to multiple devices, returns count of successful deliveries

        Args:
            device_tokens (list[str]): List of device tokens to send the notification to
            title (str): The title of the notification
            content (str): The content of the notification

        Returns:
            int: Count of successful notifications sent
        """
        success_count = 0

        for tokens_chunk_index in range(0, len(device_tokens), 500):
            tokens_chunk = device_tokens[tokens_chunk_index : tokens_chunk_index + 500]

            def _send_multicast():
                message = messaging.MulticastMessage(
                    notification=messaging.Notification(
                        title=title,
                        body=content,
                    ),
                    tokens=tokens_chunk,
                )
                return messaging.send_each_for_multicast(
                    multicast_message=message,
                    app=self._default_app,
                )

            try:
                response: messaging.BatchResponse = await asyncio.to_thread(_send_multicast)
                success_count += response.success_count

                for result in response.responses:
                    if result.success is False:
                        result: messaging.SendResponse
                        logger.error(
                            "Failed to send push notification to device token "
                            f"{result.message_id}: {result.exception}"
                        )
            except FirebaseError as err:
                logger.error("Firebase error sending push notification to multiple devices")
                logger.debug(str(err))
            except ValueError as err:
                logger.error("Error sending push notification to multiple devices")
                logger.debug(str(err))
            except Exception as e:
                logger.error("Unknown error sending push notification to multiple devices")
                logger.debug(str(e))

        return success_count
