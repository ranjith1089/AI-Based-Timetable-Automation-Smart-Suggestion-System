from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_user_create_and_list() -> None:
    payload = {
        'user_id': 'u1',
        'tenant_id': 't1',
        'name': 'Coordinator',
        'email': 'coord@example.com',
        'role': 'TIMETABLE_COORDINATOR',
    }
    create_response = client.post('/users', json=payload)
    assert create_response.status_code == 200

    list_response = client.get('/users')
    assert list_response.status_code == 200
    users = list_response.json()
    assert any(user['email'] == payload['email'] for user in users)


def test_generate_timetable() -> None:
    payload = {
        'tenant_id': 't1',
        'sections': ['CSE-A', 'CSE-B'],
        'courses': ['Math', 'AI'],
        'rooms': ['R101', 'R102'],
    }
    response = client.post('/timetables/generate', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['generated'] is True
    assert data['conflict_count'] == 0
    assert len(data['timetable']) == 2
