from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ExtractedSubject

client = TestClient(app)


def test_curriculum_import_endpoint(monkeypatch) -> None:
    mocked_subjects = [
        ExtractedSubject(
            semester=1,
            course_code='CS101',
            course_name='Programming Fundamentals',
            course_type='Core',
            l=3,
            t=1,
            p=0,
            tcp=4,
            credits=4.0,
        ),
        ExtractedSubject(
            semester=1,
            course_code='MA101',
            course_name='Engineering Mathematics',
            course_type='Core',
            l=3,
            t=1,
            p=0,
            tcp=4,
            credits=4.0,
        ),
    ]

    monkeypatch.setattr('app.main.extract_subjects_from_pdf', lambda _: mocked_subjects)

    response = client.post('/curriculum/import', params={'tenant_id': 'tenant-a'}, content=b'%PDF-1.4 test', headers={'content-type': 'application/pdf'})
    assert response.status_code == 200

    payload = response.json()
    assert payload['tenant_id'] == 'tenant-a'
    assert payload['extracted_count'] == 2
    assert payload['persisted_count'] == 2
    assert payload['subjects'][0]['semester'] == 1
    assert payload['subjects'][0]['l'] == 3
    assert payload['semesters'][0]['total_credits'] == 8.0


def test_curriculum_import_rejects_non_pdf() -> None:
    response = client.post('/curriculum/import', params={'tenant_id': 'tenant-a'}, content=b'not pdf', headers={'content-type': 'text/plain'})
    assert response.status_code == 400
