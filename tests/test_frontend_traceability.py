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
