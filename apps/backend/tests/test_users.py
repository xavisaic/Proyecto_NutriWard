from app.core.config import settings


def authenticate(client, role: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{role}@nutriward.local",
            "password": settings.demo_user_password,
        },
    )
    assert response.status_code == 200


def test_administrator_and_manager_can_list_users(client) -> None:
    for role in ("administrador", "jefatura"):
        authenticate(client, role)
        response = client.get("/api/v1/users?offset=0&limit=2")
        assert response.status_code == 200
        assert response.json()["total"] == 4
        assert len(response.json()["items"]) == 2
        client.cookies.clear()


def test_operational_roles_cannot_list_users(client) -> None:
    for role in ("nutricionista", "alimentacion"):
        authenticate(client, role)
        response = client.get("/api/v1/users")
        assert response.status_code == 403
        client.cookies.clear()


def test_users_endpoint_requires_authentication(client) -> None:
    assert client.get("/api/v1/users").status_code == 401
