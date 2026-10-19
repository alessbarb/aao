from pathlib import Path

from fastapi.testclient import TestClient

from aao.work_management_api import app


def test_control_center_served_at_root():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "AAO Control Center" in response.text
    assert "Consola de Operaciones Organizativas" in response.text


def test_control_center_navigation_and_views_present():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()

    # Navigation tabs
    assert 'role="tablist"' in html
    assert 'data-tab="tab-kanban"' in html
    assert 'data-tab="tab-tasks"' in html
    assert 'data-tab="tab-agents"' in html
    assert 'data-tab="tab-capabilities"' in html
    assert 'data-tab="tab-proposals"' in html
    assert 'data-tab="tab-executions"' in html
    assert 'data-tab="tab-evidence"' in html

    # Tab panels
    assert 'id="tab-kanban"' in html
    assert 'id="tab-tasks"' in html
    assert 'id="tab-agents"' in html
    assert 'id="tab-capabilities"' in html
    assert 'id="tab-proposals"' in html
    assert 'id="tab-executions"' in html
    assert 'id="tab-evidence"' in html


def test_control_center_kanban_six_lifecycle_states():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    assert 'id="board"' in html
    assert 'const states = ["INBOX", "READY", "IN_PROGRESS", "IN_REVIEW", "VERIFIED", "DONE"];' in html
    assert 'INBOX: "Entrada"' in html
    assert 'READY: "Preparado"' in html
    assert 'IN_PROGRESS: "En curso"' in html
    assert 'IN_REVIEW: "Revisión"' in html
    assert 'VERIFIED: "Verificado"' in html
    assert 'DONE: "Completado"' in html


def test_control_center_agents_and_identity_management():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    assert '"/v1/principals/me"' in html
    assert 'id="agents-table-body"' in html
    assert 'id="session-badge"' in html
    assert 'id="session-agent-id"' in html
    assert 'Identidad y Principales del Proyecto' in html
    assert 'Sesión Actual' in html


def test_control_center_skills_and_capabilities_as_first_class_citizens():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    assert 'id="capabilities"' in html
    assert 'id="filter-cap-type"' in html
    assert 'value="agent_skill">Habilidades de Agente (Skills)<' in html
    assert 'Habilidad (Skill)' in html
    assert 'capability.capability_type === "agent_skill"' in html
    assert '"Ejecución autorizada: no"' in html
    assert 'capability.execution_authorized' not in html
    assert '"Riesgos y límites: "' in html
    assert '"Pruebas y evidencia: "' in html
    assert '"Procedencia: "+JSON.stringify(capability.provenance)' in html


def test_control_center_code_proposals_transparency():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    assert 'id="proposals-table-body"' in html
    assert 'Propuestas de Código (Patch Proposals)' in html
    assert 'p.base_sha' in html
    assert 'p.patch_sha256' in html
    assert 'p.changed_paths' in html
    assert 'p.validations' in html
    assert 'v.candidate_tree' in html
    assert 'No disponible (aislado)' in html


def test_control_center_executions_and_logs():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    assert 'id="executions-table-body"' in html
    assert 'Ejecuciones Técnicas (Execution Queue)' in html
    assert 'e.worker_id' in html
    assert 'res.candidate_sha' in html
    assert 'res.stdout' in html
    assert 'res.stderr' in html


def test_control_center_audits_and_evidence():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    assert 'id="evidence-table-body"' in html
    assert 'Evidencias de Integridad y Dictámenes de Auditoría' in html
    assert 'rev.reviewer_id' in html
    assert 'rev.decision' in html
    assert 'rev.sha_bound' in html
    assert 'rev.candidate_sha' in html


def test_control_center_ephemeral_security_controls():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    # Memory-only token
    assert 'let readerToken = null;' in html
    assert 'function clearReaderSession()' in html
    assert 'id="disconnect"' in html
    assert 'headers:{"X-Agent-Token":readerToken}' in html
    assert '"X-CEO-Token"' not in html
    assert 'localStorage' not in html
    assert 'sessionStorage' not in html


def test_control_center_task_detail_modal_inspector():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    assert 'id="drawer-overlay"' in html
    assert 'id="drawer-acceptance-criteria"' in html
    assert 'id="drawer-evidence-list"' in html
    assert 'id="drawer-executions-list"' in html
    assert 'id="drawer-reviews-list"' in html
    assert 'id="drawer-proposals-list"' in html
    assert 'aria-modal="true"' in html
    assert 'role="dialog"' in html
