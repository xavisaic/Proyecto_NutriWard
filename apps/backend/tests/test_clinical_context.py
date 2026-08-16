import uuid
from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.core.config import settings
from app.models.admission import Admission
from app.models.audit_log import AuditLog


def authenticate(client, role: str = "nutricionista") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": f"{role}@nutriward.local", "password": settings.demo_user_password},
    )
    assert response.status_code == 200
    return response.json()


def active_admission(db_session) -> Admission:
    row = db_session.exec(select(Admission).where(Admission.status == "active")).first()
    assert row is not None
    return row


def headers(auth: dict) -> dict:
    return {"X-CSRF-Token": auth["csrf_token"]}


def test_permissions_openapi_and_empty_context(client, db_session) -> None:
    admission = active_admission(db_session)
    url = f"/api/v1/admissions/{admission.id}/clinical-context"
    assert client.get(url).status_code == 401
    for role in ("administrador", "alimentacion"):
        client.cookies.clear()
        authenticate(client, role)
        assert client.get(url).status_code == 403
    client.cookies.clear()
    authenticate(client)
    result = client.get(url)
    assert result.status_code == 200
    assert result.json()["episode_history"] is None
    assert result.json()["diagnoses"] == []
    assert result.json()["conditions"] == []
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/admissions/{admission_id}/clinical-context" in paths
    assert "/api/v1/patients/{patient_id}/conditions" in paths
    assert "/api/v1/admissions/{admission_id}/diagnoses" in paths
    assert "/api/v1/admissions/{admission_id}/clinical-history" in paths


def test_versioned_episode_history_preserves_previous_narratives_and_privacy(
    client, db_session
) -> None:
    admission = active_admission(db_session)
    history_url = f"/api/v1/admissions/{admission.id}/clinical-history"
    payload = {
        "narrative": (
            "Paciente con cinco días de menor ingesta y vómitos.\n\n"
            "Consulta por compromiso progresivo del estado general."
        ),
        "event_start_date": (admission.admitted_at.date() - timedelta(days=5)).isoformat(),
        "source": "combined",
    }
    assert client.post(history_url, json=payload).status_code == 401
    for role in ("administrador", "alimentacion"):
        client.cookies.clear()
        authenticate(client, role)
        assert client.post(history_url, json=payload).status_code == 403

    client.cookies.clear()
    auth = authenticate(client)
    clinical_headers = headers(auth)
    assert client.post(history_url, json=payload).status_code == 403
    invalid_date = client.post(
        history_url,
        json={**payload, "event_start_date": "2999-01-01"},
        headers=clinical_headers,
    )
    assert invalid_date.status_code == 422
    created = client.post(history_url, json=payload, headers=clinical_headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["current"]["version"] == 1
    assert body["current"]["narrative"] == payload["narrative"]
    assert body["current"]["author_name"] == "Nutricionista Demo"
    assert len(body["versions"]) == 1

    duplicate = client.post(history_url, json=payload, headers=clinical_headers)
    assert duplicate.status_code == 409
    updated_payload = {
        "version": 1,
        "narrative": (
            "Paciente con cinco días de menor ingesta y vómitos.\n\n"
            "Ingresa luego de presentar intolerancia completa a la vía oral."
        ),
        "event_start_date": payload["event_start_date"],
        "source": "clinical_record",
        "change_reason": "Se incorpora información de la epicrisis de urgencia.",
    }
    updated = client.patch(
        history_url, json=updated_payload, headers=clinical_headers
    )
    assert updated.status_code == 200, updated.text
    updated_body = updated.json()
    assert updated_body["current"]["version"] == 2
    assert len(updated_body["versions"]) == 2
    assert updated_body["versions"][0]["narrative"] == payload["narrative"]
    assert updated_body["versions"][1]["narrative"] == updated_payload["narrative"]

    stale = client.patch(
        history_url, json=updated_payload, headers=clinical_headers
    )
    assert stale.status_code == 409
    context = client.get(
        f"/api/v1/admissions/{admission.id}/clinical-context"
    ).json()
    assert context["episode_history"]["current"]["version"] == 2

    audits = db_session.exec(
        select(AuditLog).where(
            AuditLog.admission_id == admission.id,
            AuditLog.entity_type == "admission_clinical_history_version",
        )
    ).all()
    assert [event.action for event in audits] == [
        "admission_clinical_history_created",
        "admission_clinical_history_updated",
    ]
    for event in audits:
        serialized = f"{event.before_state}{event.after_state}"
        assert "Paciente con" not in serialized
        assert "epicrisis" not in serialized


def test_bulk_create_deduplication_and_longitudinal_scope(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    clinical_headers = headers(auth)
    conditions = client.post(
        f"/api/v1/patients/{admission.patient_id}/conditions",
        headers=clinical_headers,
        json={"items": [
            {"condition_name": "Hipertensión arterial", "source": "trakcare_manual"},
            {
                "condition_name": "Diabetes mellitus tipo 2",
                "source": "clinical_record",
                "code_system": "CIE-10",
                "code": "E11",
            },
        ]},
    )
    assert conditions.status_code == 201, conditions.text
    assert len(conditions.json()) == 2
    assert conditions.json()[0]["history"][0]["reason"] == "Registro inicial del antecedente."

    diagnoses = client.post(
        f"/api/v1/admissions/{admission.id}/diagnoses",
        headers=clinical_headers,
        json={"items": [
            {
                "diagnosis_name": "Neumonía adquirida en la comunidad",
                "source": "care_team",
                "diagnosis_type": "principal",
            },
            {"diagnosis_name": "Insuficiencia renal aguda", "source": "clinical_record", "present_on_admission": False},
        ]},
    )
    assert diagnoses.status_code == 201, diagnoses.text
    context = client.get(f"/api/v1/admissions/{admission.id}/clinical-context").json()
    assert {item["condition_name"] for item in context["conditions"]} == {
        "Hipertensión arterial", "Diabetes mellitus tipo 2"
    }
    assert {item["diagnosis_name"] for item in context["diagnoses"]} == {
        "Neumonía adquirida en la comunidad", "Insuficiencia renal aguda"
    }

    duplicate = client.post(
        f"/api/v1/patients/{admission.patient_id}/conditions",
        headers=clinical_headers,
        json={"items": [{"condition_name": "  hipertensión   arterial ", "source": "patient"}]},
    )
    assert duplicate.status_code == 409
    within_batch = client.post(
        f"/api/v1/admissions/{admission.id}/diagnoses",
        headers=clinical_headers,
        json={"items": [
            {"diagnosis_name": "Sepsis", "source": "care_team"},
            {"diagnosis_name": " sepsis ", "source": "clinical_record"},
        ]},
    )
    assert within_batch.status_code == 409

    old_admission = Admission(
        patient_id=admission.patient_id,
        admission_identifier=f"ADM-HIST-{uuid.uuid4().hex[:6]}",
        status="discharged",
        admitted_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 5, tzinfo=timezone.utc),
    )
    db_session.add(old_admission)
    db_session.commit()
    historical_context = client.get(f"/api/v1/admissions/{old_admission.id}/clinical-context").json()
    assert len(historical_context["conditions"]) == 2
    assert historical_context["diagnoses"] == []


def test_free_status_updates_history_conflicts_and_no_delete(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    clinical_headers = headers(auth)
    condition = client.post(
        f"/api/v1/patients/{admission.patient_id}/conditions",
        headers=clinical_headers,
        json={"items": [{"condition_name": "Dislipidemia", "source": "patient"}]},
    ).json()[0]
    updated_condition = client.patch(
        f"/api/v1/patient-conditions/{condition['id']}/status",
        headers=clinical_headers,
        json={
            "version": 1,
            "clinical_status": "remission",
            "verification_status": "confirmed",
            "reason": "Actualizado durante la anamnesis.",
            "source": "patient",
        },
    )
    assert updated_condition.status_code == 200, updated_condition.text
    assert updated_condition.json()["version"] == 2
    assert len(updated_condition.json()["history"]) == 2
    stale = client.patch(
        f"/api/v1/patient-conditions/{condition['id']}/status",
        headers=clinical_headers,
        json={
            "version": 1,
            "clinical_status": "active",
            "verification_status": "confirmed",
            "reason": "Intento con versión obsoleta.",
            "source": "patient",
        },
    )
    assert stale.status_code == 409

    diagnosis = client.post(
        f"/api/v1/admissions/{admission.id}/diagnoses",
        headers=clinical_headers,
        json={"items": [{"diagnosis_name": "Sepsis", "source": "care_team"}]},
    ).json()[0]
    resolved = client.patch(
        f"/api/v1/admission-diagnoses/{diagnosis['id']}/status",
        headers=clinical_headers,
        json={
            "version": 1,
            "clinical_status": "resolved",
            "verification_status": "confirmed",
            "reason": "Resolución informada por equipo tratante.",
            "source": "care_team",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["resolved_at"] is not None
    reactivated = client.patch(
        f"/api/v1/admission-diagnoses/{diagnosis['id']}/status",
        headers=clinical_headers,
        json={
            "version": 2,
            "clinical_status": "active",
            "verification_status": "confirmed",
            "reason": "Reactivado por nueva evolución clínica.",
            "source": "clinical_record",
        },
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["resolved_at"] is None
    assert len(reactivated.json()["history"]) == 3
    delete_response = client.delete(
        f"/api/v1/admission-diagnoses/{diagnosis['id']}", headers=clinical_headers
    )
    assert delete_response.status_code in (404, 405)

    audits = db_session.exec(select(AuditLog).where(AuditLog.entity_id == uuid.UUID(diagnosis["id"]))).all()
    assert [event.action for event in audits] == [
        "admission_diagnosis_created", "admission_diagnosis_status_changed", "admission_diagnosis_status_changed"
    ]
    assert all("diagnosis_name" not in (event.after_state or {}) for event in audits)


def test_historical_admission_is_read_only_and_csrf_is_required(client, db_session) -> None:
    active = active_admission(db_session)
    old = Admission(
        patient_id=active.patient_id,
        admission_identifier=f"ADM-HIST-{uuid.uuid4().hex[:6]}",
        status="discharged",
        admitted_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
        ended_at=datetime(2025, 2, 2, tzinfo=timezone.utc),
    )
    db_session.add(old)
    db_session.commit()
    auth = authenticate(client)
    payload = {"items": [{"diagnosis_name": "Diagnóstico histórico", "source": "clinical_record"}]}
    assert client.post(f"/api/v1/admissions/{active.id}/diagnoses", json=payload).status_code == 403
    historical = client.post(
        f"/api/v1/admissions/{old.id}/diagnoses", json=payload, headers=headers(auth)
    )
    assert historical.status_code == 409
    history = client.post(
        f"/api/v1/admissions/{old.id}/clinical-history",
        json={
            "narrative": "Historia retrospectiva que no debe guardarse.",
            "source": "clinical_record",
        },
        headers=headers(auth),
    )
    assert history.status_code == 409
