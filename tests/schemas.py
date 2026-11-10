from typing import TypedDict

from faker import Faker


class UserCredentials(TypedDict):
    username: str
    password: str
    email: str


def generate_user_credentials() -> UserCredentials:
    """
    Generate random user credentials (username and password)
    Returns:
        UserCredentials: Generated username and password
    """
    faker = Faker()
    username = faker.password(length=10, upper_case=True, lower_case=True, digits=True, special_chars=False)
    password = faker.password(length=12, special_chars=False, digits=True, upper_case=True, lower_case=True) + "@%&"
    email = faker.unique.safe_email()
    return UserCredentials(username=username, password=password, email=email)
