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
            {'section': 'CSE-A', 'day': 'Monday', 'period': 1, 'course_code': 'CS301', 'course_name': 'AI', 'semester': 5, 'l_hours': 3, 't_hours': 1, 'p_hours': 0, 'tcp': 4, 'course_type': 'T', 'is_elective': False, 'requires_lab': False, 'room': 'R101', 'faculty_id': 'F1'},
            {'section': 'CSE-B', 'day': 'Monday', 'period': 1, 'course_code': 'CS302', 'course_name': 'ML', 'semester': 5, 'l_hours': 3, 't_hours': 1, 'p_hours': 0, 'tcp': 4, 'course_type': 'OE', 'is_elective': True, 'requires_lab': False, 'room': 'R101', 'faculty_id': 'F1'},
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
        'subjects': [
            {'course_code': 'MA201', 'course_name': 'Math', 'semester': 3, 'l_hours': 3, 't_hours': 1, 'p_hours': 0, 'tcp': 4, 'course_type': 'T', 'is_elective': False, 'requires_lab': False},
            {'course_code': 'CS301', 'course_name': 'AI', 'semester': 5, 'l_hours': 3, 't_hours': 0, 'p_hours': 2, 'tcp': 5, 'course_type': 'LIT', 'is_elective': True, 'requires_lab': True},
        ],
        'rooms': ['R101', 'R102'],
        'faculty_ids': ['F1', 'F2'],
    }
    generate_response = client.post('/timetables/generate', json=generate_payload)
    assert generate_response.status_code == 200
    generated = generate_response.json()
    assert 'score_breakdown' in generated
    assert 'diagnostics' in generated
    assert generated['score_breakdown']['final_score'] >= 0

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
        'timetable': generated['timetable'],
    }
    quality_response = client.post('/timetables/quality', json=quality_payload)
    assert quality_response.status_code == 200
    assert quality_response.json()['overall_quality'] >= 0


def test_civil_three_section_shared_electives_and_rotating_labs() -> None:
    payload = {
        'tenant_id': 'civil-1',
        'sections': ['CIVIL-A', 'CIVIL-B', 'CIVIL-C'],
        'courses': ['Structural Analysis', 'Surveying'],
        'rooms': ['CR-201', 'CR-202', 'LAB-301', 'LAB-302'],
        'faculty_ids': ['CF1', 'CF2', 'CF3', 'CF4'],
        'section_subject_plan': [
            {
                'section': 'CIVIL-A',
                'subject_blocks': [
                    {'subject': 'Geotechnical Lab', 'required_periods': 1, 'is_lab': True},
                    {'subject': 'Hydrology', 'required_periods': 1, 'is_lab': False},
                    {'subject': 'Bridge Elective', 'required_periods': 1, 'is_lab': False},
                ],
            },
            {
                'section': 'CIVIL-B',
                'subject_blocks': [
                    {'subject': 'Concrete Lab', 'required_periods': 1, 'is_lab': True},
                    {'subject': 'Hydrology', 'required_periods': 1, 'is_lab': False},
                    {'subject': 'Bridge Elective', 'required_periods': 1, 'is_lab': False},
                ],
            },
            {
                'section': 'CIVIL-C',
                'subject_blocks': [
                    {'subject': 'Transportation Lab', 'required_periods': 1, 'is_lab': True},
                    {'subject': 'Hydrology', 'required_periods': 1, 'is_lab': False},
                    {'subject': 'Bridge Elective', 'required_periods': 1, 'is_lab': False},
                ],
            },
        ],
        'elective_groups': [
            {
                'group_id': 'EL-CIVIL-1',
                'subject': 'Bridge Elective',
                'sections': ['CIVIL-A', 'CIVIL-B', 'CIVIL-C'],
                'faculty_ids': ['CEF1', 'CEF2', 'CEF3'],
                'room_ids': ['CR-201', 'CR-202', 'LAB-301'],
            }
        ],
    }

    response = client.post('/timetables/generate', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['generated'] is True
    assert data['conflict_count'] == 0

    timetable = data['timetable']
    electives = [entry for entry in timetable if entry['course'] == 'Bridge Elective']
    assert len(electives) == 3
    elective_slots = {(entry['day'], entry['period']) for entry in electives}
    assert len(elective_slots) == 1

    labs = [entry for entry in timetable if 'Lab' in entry['course']]
    assert len(labs) == 3
    assert len({entry['room'] for entry in labs}) >= 2

    faculty_slots = {(entry['faculty_id'], entry['day'], entry['period']) for entry in timetable}
    assert len(faculty_slots) == len(timetable)


def test_elective_group_api_and_sync_violation_detection() -> None:
    create_response = client.post(
        '/elective-groups',
        json={
            'group_id': 'EL-CIVIL-2',
            'subject': 'Water Resources Elective',
            'sections': ['CIVIL-A', 'CIVIL-B'],
            'faculty_ids': ['CF10', 'CF11'],
            'room_ids': ['CR-201', 'CR-202'],
        },
    )
    assert create_response.status_code == 200

    list_response = client.get('/elective-groups', params={'section': 'CIVIL-A'})
    assert list_response.status_code == 200
    assert any(item['group_id'] == 'EL-CIVIL-2' for item in list_response.json())

    validate_response = client.post(
        '/timetables/validate',
        json={
            'tenant_id': 'civil-1',
            'elective_groups': [
                {
                    'group_id': 'EL-CIVIL-2',
                    'subject': 'Water Resources Elective',
                    'sections': ['CIVIL-A', 'CIVIL-B'],
                    'faculty_ids': ['CF10', 'CF11'],
                    'room_ids': ['CR-201', 'CR-202'],
                }
            ],
            'timetable': [
                {
                    'section': 'CIVIL-A',
                    'day': 'Tuesday',
                    'period': 2,
                    'course': 'Water Resources Elective',
                    'room': 'CR-201',
                    'faculty_id': 'CF10',
                },
                {
                    'section': 'CIVIL-B',
                    'day': 'Wednesday',
                    'period': 2,
                    'course': 'Water Resources Elective',
                    'room': 'CR-202',
                    'faculty_id': 'CF11',
                },
            ],
        },
    )
    assert validate_response.status_code == 200
    messages = [item['message'] for item in validate_response.json()['conflicts']]
    assert any('not synchronized' in message for message in messages)
