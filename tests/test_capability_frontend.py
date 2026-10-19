from pathlib import Path


def test_control_center_renders_project_scoped_capability_registry_as_non_authorizing():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text()
    assert 'id="capabilities"' in html
    assert '"/v1/projects/"+encodeURIComponent(project.value)+"/capabilities"' in html
    assert '"/v1/projects/"+encodeURIComponent(project.value)+"/capability-evaluations"' in html
    assert 'capability.execution_authorized' not in html
    assert '"Ejecución autorizada: no"' in html
    assert "capability.capability_id+\" · \"+capability.version" in html
    assert 'headers:{"X-Agent-Token":readerToken}' in html
    assert '"X-CEO-Token"' not in html
