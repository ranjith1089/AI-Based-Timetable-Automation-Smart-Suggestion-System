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


def test_constraint_create_and_list() -> None:
    rule = {
        'rule_id': 'R1',
        'tenant_id': 't1',
        'name': 'No Faculty Clash',
        'category': 'HARD',
        'weight': 80,
        'enabled': True,
        'params': {'type': 'faculty_clash'},
    }
    create_response = client.post('/constraints', json=rule)
    assert create_response.status_code == 200

    list_response = client.get('/constraints', params={'tenant_id': 't1'})
    assert list_response.status_code == 200
    assert any(item['name'] == 'No Faculty Clash' for item in list_response.json())


def test_validate_conflict_and_suggestions() -> None:
    payload = {
        'tenant_id': 't1',
        'timetable': [
            {'section': 'CSE-A', 'day': 'Monday', 'period': 1, 'course': 'AI', 'room': 'R101', 'faculty_id': 'F1'},
            {'section': 'CSE-B', 'day': 'Monday', 'period': 1, 'course': 'ML', 'room': 'R101', 'faculty_id': 'F1'},
        ],
    }
    validate_response = client.post('/timetables/validate', json=payload)
    assert validate_response.status_code == 200
    assert validate_response.json()['conflict_count'] > 0

    suggestion_response = client.post('/timetables/suggestions', json=payload)
    assert suggestion_response.status_code == 200
    assert len(suggestion_response.json()['suggestions']) >= 1


def test_generate_simulation_emergency_quality() -> None:
    generate_payload = {
        'tenant_id': 't1',
        'sections': ['CSE-A', 'CSE-B'],
        'courses': ['Math', 'AI'],
        'rooms': ['R101', 'R102'],
        'faculty_ids': ['F1', 'F2'],
    }
    generate_response = client.post('/timetables/generate', json=generate_payload)
    assert generate_response.status_code == 200
    body = generate_response.json()
    assert body['version'] == 1
    assert body['generation_config']['working_days'] == 5
    assert any(slot['day'] == 'Friday' for slot in body['timetable'])

    simulation_payload = {
        'tenant_id': 't1',
        'scenario_name': 'Faculty Leave Test',
        'scenario_type': 'FACULTY_LEAVE',
        'payload': {'faculty_id': 'F1'},
    }
    sim_response = client.post('/simulations', json=simulation_payload)
    assert sim_response.status_code == 200
    assert sim_response.json()['estimated_quality_score'] > 0

    emergency_payload = {
        'tenant_id': 't1',
        'reason': 'Sudden leave',
        'affected_faculty_id': 'F1',
        'section': 'CSE-A',
    }
    emergency_response = client.post('/reschedule/emergency', json=emergency_payload)
    assert emergency_response.status_code == 200
    assert emergency_response.json()['handled'] is True

    quality_payload = {
        'tenant_id': 't1',
        'timetable': generate_response.json()['timetable'],
    }
    quality_response = client.post('/timetables/quality', json=quality_payload)
    assert quality_response.status_code == 200
    assert quality_response.json()['overall_quality'] >= 0



def test_generate_with_custom_configuration_and_validation() -> None:
    generate_payload = {
        'tenant_id': 't2',
        'sections': ['ECE-A'],
        'courses': ['DSP', 'Signals'],
        'rooms': ['L1'],
        'faculty_ids': ['F10'],
        'working_days': 4,
        'hours_per_day': 5,
        'extra_hours': 2,
        'saturday_enabled': True,
        'saturday_hours': 3,
        'lab_continuous_hours': 3,
    }
    generate_response = client.post('/timetables/generate', json=generate_payload)
    assert generate_response.status_code == 200
    data = generate_response.json()
    assert data['generation_config']['saturday_enabled'] is True
    assert data['generation_config']['saturday_hours'] == 3

    day_slot_count = len(data['timetable'])
    assert day_slot_count == (4 * 5) + 3 + 2

    invalid_payload = {
        'tenant_id': 't2',
        'sections': ['ECE-A'],
        'courses': ['DSP'],
        'rooms': ['L1'],
        'faculty_ids': ['F10'],
        'saturday_enabled': False,
        'saturday_hours': 2,
    }
    invalid_response = client.post('/timetables/generate', json=invalid_payload)
    assert invalid_response.status_code == 422
