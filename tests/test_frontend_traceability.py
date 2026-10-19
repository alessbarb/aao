from fastapi.testclient import TestClient

from aao.work_management_api import app


def test_work_detail_ui_reports_local_sha_link_without_claiming_remote_validation():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    page = response.text
    assert 'run.result.candidate_sha===data.pull_request.candidate_sha' in page
    assert "hay una ejecución exitosa registrada para el mismo SHA" in page
    assert "no consta una ejecución exitosa para el SHA guardado" in page
    assert "Estado remoto de la PR: no verificado por AAO" in page
    assert "no certifica que el SHA siga siendo el HEAD remoto" in page


def test_control_center_has_explicit_ephemeral_development_authentication():
    with TestClient(app) as client:
        response = client.get("/")

    page = response.text
    assert '<form id="auth-panel"' in page
    assert 'id="auth-token" name="token" type="password"' in page
    assert 'id="disconnect" type="button"' in page
    assert 'id="auth-panel" class="auth-panel"' in page
    assert "Autenticación requerida para consultar el núcleo local." in page
    assert "Introduce una credencial de desarrollo para consultar los datos reales de PostgreSQL." in page
    assert 'loadProjects().catch(err=>{projectSelect.replaceChildren()' not in page
    assert "solo se conserva en la memoria de esta pestaña" in page
    assert "window.prompt" not in page
    assert "localStorage" not in page
    assert "sessionStorage" not in page
