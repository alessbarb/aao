    "use strict";
    const states = ["INBOX", "READY", "IN_PROGRESS", "IN_REVIEW", "VERIFIED", "DONE"];
    const labels = {
      INBOX: "Entrada",
      READY: "Preparado",
      IN_PROGRESS: "En curso",
      IN_REVIEW: "Revisión",
      VERIFIED: "Verificado",
      DONE: "Completado"
    };

    const project = document.querySelector("#project");
    const board = document.querySelector("#board");
    const message = document.querySelector("#message");
    const capabilities = document.querySelector("#capabilities");
    const evaluations = document.querySelector("#capability-evaluations");
    const authPanel = document.querySelector("#auth-panel");
    const authForm = document.querySelector("#auth-form");
    const authTokenInput = document.querySelector("#auth-token");
    const sessionBadge = document.querySelector("#session-badge");
    const sessionAgentId = document.querySelector("#session-agent-id");
    const disconnectBtn = document.querySelector("#disconnect");
    const reloadBtn = document.querySelector("#reload");

    // Drawer elements
    const drawerOverlay = document.querySelector("#drawer-overlay");
    const drawerClose = document.querySelector("#drawer-close");
    const drawerTitle = document.querySelector("#drawer-title");
    const drawerTaskId = document.querySelector("#drawer-task-id");
    const drawerTaskStatus = document.querySelector("#drawer-task-status");
    const drawerAcceptance = document.querySelector("#drawer-acceptance-criteria");
    const drawerEvidence = document.querySelector("#drawer-evidence-list");
    const drawerExecutions = document.querySelector("#drawer-executions-list");
    const drawerReviews = document.querySelector("#drawer-reviews-list");
    const drawerProposals = document.querySelector("#drawer-proposals-list");

    // Project reader credential stays in tab memory (never in browser persistent storage).
    let readerToken = null;
    let currentPrincipal = null;
    let currentWorkItems = [];
    let currentCapabilities = [];
    let currentEvaluations = [];

    function node(tag, text, cls) {
      const e = document.createElement(tag);
      if (text !== undefined && text !== null) e.textContent = text;
      if (cls) e.className = cls;
      return e;
    }

    function clearReaderSession() {
      readerToken = null;
      currentPrincipal = null;
      currentWorkItems = [];
      currentCapabilities = [];
      currentEvaluations = [];
      authTokenInput.value = "";
      authPanel.classList.remove("is-hidden");
      sessionBadge.classList.add("is-hidden");
      disconnectBtn.classList.add("is-hidden");
      document.querySelector("#agent-me-status").textContent = "Desconectado";
      document.querySelector("#agent-me-desc").textContent = "Sin credencial de agente en memoria.";
      document.querySelector("#agent-me-details").textContent = "";
      board.replaceChildren();
      capabilities.replaceChildren();
      evaluations.replaceChildren();
      document.querySelector("#tasks-table-body").replaceChildren();
      document.querySelector("#proposals-table-body").replaceChildren();
      document.querySelector("#executions-table-body").replaceChildren();
      document.querySelector("#evidence-table-body").replaceChildren();
      document.querySelector("#agents-table-body").replaceChildren();
      document.querySelector("#git-candidates-table-body").replaceChildren();
      document.querySelector("#git-reviews-table-body").replaceChildren();
      document.querySelector("#git-promotion-history-table-body").replaceChildren();
      const tbodyUnaccredited = document.querySelector("#git-unaccredited-candidates-table-body");
      if (tbodyUnaccredited) tbodyUnaccredited.replaceChildren();
      message.textContent = "Sesión desconectada. Autenticación requerida para consultar el núcleo local.";
    }

    async function json(url) {
      if (!readerToken) {
        throw new Error("Se requiere identidad AGENT con acceso de lectura al proyecto");
      }
      let r = await fetch(url, { credentials: "same-origin", headers:{"X-Agent-Token":readerToken} });
      if (r.status === 401 || r.status === 403) {
        clearReaderSession();
        throw new Error("Credencial rechazada o revocada por el núcleo local (HTTP " + r.status + ")");
      }
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }

    async function checkCurrentPrincipal() {
      if (!readerToken) return;
      try {
        const res = await json("/v1/principals/me");
        currentPrincipal = res;
        sessionAgentId.textContent = "Agente: " + res.principal_id;
        sessionBadge.classList.remove("is-hidden");
        disconnectBtn.classList.remove("is-hidden");
        authPanel.classList.add("is-hidden");
        document.querySelector("#agent-me-status").textContent = res.enabled ? "Activo" : "Deshabilitado";
        document.querySelector("#agent-me-desc").textContent = "Identidad validada: " + res.principal_id + " (" + res.kind + ")";
        document.querySelector("#agent-me-details").textContent = "Permisos de consulta activos vía grant project.read.";
      } catch (err) {
        currentPrincipal = null;
      }
    }

    async function loadProjects() {
      try {
        const projects = await json("/v1/projects");
        const previous = project.value;
        project.replaceChildren();
        for (const p of projects) {
          const opt = node("option", p.name + " · " + p.state);
          opt.value = p.id;
          project.append(opt);
        }
        if (projects.some(p => p.id === previous)) {
          project.value = previous;
        }
        if (projects.length) {
          await checkCurrentPrincipal();
          await loadBoard();
        } else {
          board.replaceChildren();
          capabilities.replaceChildren();
          evaluations.replaceChildren();
          message.textContent = "Sin proyectos autorizados para esta identidad";
        }
      } catch (err) {
        message.replaceChildren(node("p", "No se pudieron consultar los proyectos: " + err.message, "meta"));
      }
    }

    async function loadBoard() {
      if (!project.value) return;
      message.textContent = "Cargando datos reales de PostgreSQL…";
      try {
        const work = await json("/v1/projects/"+encodeURIComponent(project.value)+"/board");
        const available = await json("/v1/projects/"+encodeURIComponent(project.value)+"/capabilities");
        const assessments = await json("/v1/projects/"+encodeURIComponent(project.value)+"/capability-evaluations");

        currentWorkItems = work;
        currentCapabilities = available;
        currentEvaluations = assessments;

        renderKanban(work);
        renderTasksTable(work);
        renderCapabilities(available, assessments);
        renderEvaluations(assessments);
        renderProposals(work);
        renderExecutions(work);
        renderEvidence(work);
        renderAgents(work);
        renderGitLifecycle(work);

        const executionCount = work.reduce((count, task) => count + (Array.isArray(task.executions) ? task.executions.length : 0), 0);
        message.textContent = "Mostrando " + work.length + " tareas · " + executionCount + " ejecuciones registradas · " + available.length + " capacidades";
      } catch (e) {
        message.replaceChildren(node("p", "No se pudo cargar el tablero: " + e.message, "meta"));
      }
    }

    function renderKanban(work) {
      board.replaceChildren();
      for (const state of states) {
        const col = node("section", "", "kanban-col");
        const header = node("div", "", "kanban-header");
        header.append(node("h2", labels[state]));
        const tasks = work.filter(w => w.status === state);
        header.append(node("span", tasks.length + " tareas", "count-pill"));
        col.append(header);

        if (!tasks.length) {
          col.append(node("div", "Sin tareas", "empty-state"));
        }

        for (const task of tasks) {
          const card = node("article", "", "task-card");
          card.tabIndex = 0;
          card.setAttribute("role", "button");
          card.setAttribute("aria-label", "Ver detalle de " + task.title);

          const titleRow = node("div", "", "card-title-row");
          titleRow.append(node("h3", task.title, "task-card-title"));
          card.append(titleRow);

          const meta = node("div", "", "task-meta");
          meta.append(node("span", task.id.slice(0, 8), "pill"));

          const criteriaCount = Array.isArray(task.acceptance_criteria) ? task.acceptance_criteria.length : 0;
          meta.append(node("span", criteriaCount + " criterios", "pill"));

          const executions = Array.isArray(task.executions) ? task.executions : [];
          if (executions.length) {
            meta.append(node("span", executions.length + " ejecuciones", "pill execution"));
          }

          const reviews = Array.isArray(task.reviews) ? task.reviews : [];
          for (const rev of reviews) {
            if (rev.decision === "VETO") meta.append(node("span", "VETO ACTIVO", "pill veto"));
            else if (rev.decision === "APPROVE") meta.append(node("span", "Aprobación registrada", "pill approve"));
            else if (rev.decision === "REJECT") meta.append(node("span", "Rechazado", "pill reject"));
          }

          const proposals = Array.isArray(task.patch_proposals) ? task.patch_proposals : [];
          if (proposals.length) {
            meta.append(node("span", proposals.length + " parches", "pill proposal"));
          }

          card.append(meta);
          card.addEventListener("click", () => openTaskDrawer(task));
          card.addEventListener("keydown", (ev) => {
            if (ev.key === "Enter" || ev.key === " ") {
              ev.preventDefault();
              openTaskDrawer(task);
            }
          });
          col.append(card);
        }
        board.append(col);
      }
    }

    function renderTasksTable(work) {
      const tbody = document.querySelector("#tasks-table-body");
      const filterStatus = document.querySelector("#filter-task-status").value;
      tbody.replaceChildren();

      const filtered = filterStatus === "ALL" ? work : work.filter(w => w.status === filterStatus);
      if (!filtered.length) {
        const tr = node("tr");
        const td = node("td", "No hay tareas registradas para este filtro.", "empty-state");
        td.colSpan = 8;
        tr.append(td);
        tbody.append(tr);
        return;
      }

      for (const t of filtered) {
        const tr = node("tr");
        tr.append(node("td", t.id.slice(0, 8)));
        tr.append(node("td", t.title));
        tr.append(node("td", labels[t.status] || t.status));
        tr.append(node("td", String(Array.isArray(t.acceptance_criteria) ? t.acceptance_criteria.length : 0)));
        tr.append(node("td", String(Array.isArray(t.executions) ? t.executions.length : 0)));
        tr.append(node("td", String(Array.isArray(t.reviews) ? t.reviews.length : 0)));
        tr.append(node("td", String(Array.isArray(t.patch_proposals) ? t.patch_proposals.length : 0)));

        const actionTd = node("td");
        const btn = node("button", "Ver detalle");
        btn.type = "button";
        btn.addEventListener("click", () => openTaskDrawer(t));
        actionTd.append(btn);
        tr.append(actionTd);
        tbody.append(tr);
      }
    }

    function renderCapabilities(available, assessments) {
      capabilities.replaceChildren();
      const filterType = document.querySelector("#filter-cap-type").value;
      const filtered = filterType === "ALL" ? available : available.filter(c => c.capability_type === filterType);

      if (!filtered.length) {
        capabilities.append(node("p", "No hay capacidades registradas para este proyecto.", "meta-line"));
        return;
      }

      for (const capability of filtered) {
        const isSkill = capability.capability_type === "agent_skill" || capability.capability_type === "agent";
        const card = node("article", "", "catalog-card" + (isSkill ? " is-skill" : ""));

        const titleRow = node("div", "", "card-title-row");
        titleRow.append(node("strong", capability.capability_id+" · "+capability.version));
        if (isSkill) {
          titleRow.append(node("span", "Habilidad (Skill)", "pill skill"));
        } else {
          titleRow.append(node("span", capability.capability_type, "pill"));
        }
        card.append(titleRow);

        card.append(node("div", capability.capability_type + " · " + capability.status, "meta-line"));
        card.append(node("p", typeof capability.contract.purpose === "string" ? capability.contract.purpose : "Contrato registrado; propósito no especificado."));

        card.append(node("div", "Procedencia: "+JSON.stringify(capability.provenance), "meta-line"));
        card.append(node("div", "Permisos declarados: " + (capability.required_permissions.join(", ") || "ninguno"), "meta-line"));
        card.append(node("div", "Riesgos y límites: " + (capability.risks.join(", ") || "no declarados"), "meta-line"));
        card.append(node("div", "Pruebas y evidencia: " + [...capability.tests, ...(capability.evidence || [])].join(", "), "meta-line"));

        const assessedBy = assessments.filter(item => item.details.capability_id === capability.capability_id && item.details.version === capability.version);
        card.append(node("div", assessedBy.length ? "Evaluada en tareas: " + assessedBy.map(item => item.task_title).join(", ") : "Evaluada en tareas: Sin evaluaciones vinculadas a tareas.", "meta-line"));

        card.append(node("div", "Ejecución autorizada: no", "meta-line disclaimer"));
        card.append(node("div", "Registro sin permiso de ejecución implícito", "meta-line"));

        capabilities.append(card);
      }
    }

    function renderEvaluations(assessments) {
      evaluations.replaceChildren();
      if (!assessments.length) {
        evaluations.append(node("p", "No hay evaluaciones registradas.", "meta-line"));
        return;
      }

      for (const assessment of assessments) {
        const details = assessment.details;
        const card = node("article", "", "catalog-card");
        const recommendation = details.recommendation || "Sin recomendación única (empate)";

        card.append(node("strong", assessment.task_title + " · " + recommendation));
        card.append(node("div", "Tarea: " + assessment.task_id, "meta-line"));
        card.append(node("p", details.rationale));

        const scoreStr = Object.entries(details.scores || {}).map(([name, score]) => name + " " + score).join(" · ");
        card.append(node("div", "Puntuaciones: " + scoreStr, "meta-line"));
        card.append(node("div", "Evidencia: " + (details.evidence || []).join(", "), "meta-line"));
        card.append(node("div", "Evaluación no autoriza ejecución.", "meta-line disclaimer"));

        evaluations.append(card);
      }
    }

    function renderProposals(work) {
      const tbody = document.querySelector("#proposals-table-body");
      tbody.replaceChildren();

      const allProposals = [];
      for (const task of work) {
        const proposals = Array.isArray(task.patch_proposals) ? task.patch_proposals : [];
        for (const p of proposals) {
          allProposals.push({ taskTitle: task.title, taskId: task.id, proposal: p });
        }
      }

      if (!allProposals.length) {
        const tr = node("tr");
        const td = node("td", "No hay propuestas de código registradas en este proyecto.", "empty-state");
        td.colSpan = 9;
        tr.append(td);
        tbody.append(tr);
        return;
      }

      for (const item of allProposals) {
        const p = item.proposal;
        const tr = node("tr");
        tr.append(node("td", p.id.slice(0, 8)));
        tr.append(node("td", item.taskTitle));
        tr.append(node("td", p.proposer_id));
        tr.append(node("td", p.base_sha.slice(0, 8)));
        tr.append(node("td", p.patch_sha256.slice(0, 10)));
        tr.append(node("td", (p.changed_paths || []).join(", ") || "sin rutas"));
        tr.append(node("td", p.status));

        const validations = Array.isArray(p.validations) ? p.validations : [];
        if (validations.length) {
          const valSummary = validations.map(v => v.validator_id + " (árbol " + v.candidate_tree.slice(0, 7) + ")").join(", ");
          tr.append(node("td", valSummary));
        } else {
          tr.append(node("td", "Pendiente de validación"));
        }

        tr.append(node("td", "No disponible (aislado)"));
        tbody.append(tr);
      }
    }

    function renderExecutions(work) {
      const tbody = document.querySelector("#executions-table-body");
      tbody.replaceChildren();

      const allExecutions = [];
      for (const task of work) {
        const execs = Array.isArray(task.executions) ? task.executions : [];
        for (const e of execs) {
          allExecutions.push({ taskTitle: task.title, taskId: task.id, execution: e });
        }
      }

      if (!allExecutions.length) {
        const tr = node("tr");
        const td = node("td", "No hay ejecuciones registradas en este proyecto.", "empty-state");
        td.colSpan = 8;
        tr.append(td);
        tbody.append(tr);
        return;
      }

      for (const item of allExecutions) {
        const e = item.execution;
        const res = e.result || {};
        const tr = node("tr");
        tr.append(node("td", e.id.slice(0, 8)));
        tr.append(node("td", item.taskTitle));
        tr.append(node("td", e.status));
        tr.append(node("td", e.worker_id || "No asignado"));
        tr.append(node("td", String(e.attempts || 1)));
        tr.append(node("td", (res.capability_id ? res.capability_id + "@" + res.capability_version : "Check: " + (res.check_id || "genérico"))));
        tr.append(node("td", res.candidate_sha ? res.candidate_sha.slice(0, 8) : "no ligado"));

        const logTd = node("td");
        if (res.stdout || res.stderr) {
          const details = node("details");
          details.append(node("summary", "Ver salida (" + (res.conclusion || "código " + res.exit_code) + ")"));
          if (res.stdout) details.append(node("pre", res.stdout, "code-block"));
          if (res.stderr) details.append(node("pre", res.stderr, "code-block"));
          logTd.append(details);
        } else {
          logTd.textContent = "Sin salida registrada";
        }
        tr.append(logTd);
        tbody.append(tr);
      }
    }

    function renderEvidence(work) {
      const tbody = document.querySelector("#evidence-table-body");
      tbody.replaceChildren();

      let hasEvidenceOrReviews = false;
      for (const task of work) {
        const evidenceRefs = Array.isArray(task.evidence) ? task.evidence : [];
        const reviews = Array.isArray(task.reviews) ? task.reviews : [];

        if (evidenceRefs.length || reviews.length) {
          hasEvidenceOrReviews = true;
          const tr = node("tr");
          tr.append(node("td", task.title));
          tr.append(node("td", evidenceRefs.join(", ") || "Sin referencias directas"));

          if (reviews.length) {
            const decs = reviews.map(r => r.decision + (r.sha_bound ? " (SHA ligado)" : "")).join(" · ");
            tr.append(node("td", decs));
            tr.append(node("td", reviews.map(r => r.reviewer_id).join(", ")));
            tr.append(node("td", reviews.map(r => r.candidate_sha ? r.candidate_sha.slice(0, 8) : "sin SHA").join(", ")));
            tr.append(node("td", reviews.map(r => r.created_at).join(", ")));
          } else {
            tr.append(node("td", "Sin dictamen de auditor"));
            tr.append(node("td", "—"));
            tr.append(node("td", "—"));
            tr.append(node("td", "—"));
          }
          tbody.append(tr);
        }
      }

      if (!hasEvidenceOrReviews) {
        const tr = node("tr");
        const td = node("td", "No hay evidencias ni revisiones registradas en este proyecto.", "empty-state");
        td.colSpan = 6;
        tr.append(td);
        tbody.append(tr);
      }
    }

    function renderAgents(work) {
      const tbody = document.querySelector("#agents-table-body");
      tbody.replaceChildren();

      const participants = new Map();
      if (currentPrincipal) {
        participants.set(currentPrincipal.principal_id, {
          role: "Sesión Lector Activo (" + currentPrincipal.kind + ")",
          interactions: "Consultas de tablero, catálogo y evidencias"
        });
      }

      for (const task of work) {
        if (task.author_id) {
          const prev = participants.get(task.author_id) || { role: "Autor de Tarea", interactions: "" };
          participants.set(task.author_id, prev);
        }
        for (const e of (task.executions || [])) {
          if (e.worker_id) {
            const prev = participants.get(e.worker_id) || { role: "Worker Ejecutor", interactions: "" };
            prev.interactions = (prev.interactions ? prev.interactions + "; " : "") + "Ejecución " + e.id.slice(0, 8);
            participants.set(e.worker_id, prev);
          }
        }
        for (const r of (task.reviews || [])) {
          if (r.reviewer_id) {
            const prev = participants.get(r.reviewer_id) || { role: "Auditor Revisor", interactions: "" };
            prev.interactions = (prev.interactions ? prev.interactions + "; " : "") + "Dictamen " + r.decision;
            participants.set(r.reviewer_id, prev);
          }
        }
        for (const p of (task.patch_proposals || [])) {
          if (p.proposer_id) {
            const prev = participants.get(p.proposer_id) || { role: "Agente Proponente", interactions: "" };
            prev.interactions = (prev.interactions ? prev.interactions + "; " : "") + "Propuesta " + p.id.slice(0, 8);
            participants.set(p.proposer_id, prev);
          }
          for (const v of (p.validations || [])) {
            if (v.validator_id) {
              const prev = participants.get(v.validator_id) || { role: "Validador Aislado", interactions: "" };
              prev.interactions = (prev.interactions ? prev.interactions + "; " : "") + "Validación en árbol " + v.candidate_tree.slice(0, 7);
              participants.set(v.validator_id, prev);
            }
          }
        }
      }

      if (!participants.size) {
        const tr = node("tr");
        const td = node("td", "No hay identidades registradas en las actividades de este proyecto.", "empty-state");
        td.colSpan = 3;
        tr.append(td);
        tbody.append(tr);
        return;
      }

      for (const [id, data] of participants.entries()) {
        const tr = node("tr");
        tr.append(node("td", id));
        tr.append(node("td", data.role));
        tr.append(node("td", data.interactions || "Participación registrada"));
        tbody.append(tr);
      }
    }

    function renderGitLifecycle(work) {
      const tbodyCandidates = document.querySelector("#git-candidates-table-body");
      const tbodyReviews = document.querySelector("#git-reviews-table-body");
      const tbodyPromotions = document.querySelector("#git-promotion-history-table-body");
      const tbodyUnaccredited = document.querySelector("#git-unaccredited-candidates-table-body");
      const metricCandidates = document.querySelector("#metric-candidate-count");
      const metricVeto = document.querySelector("#metric-veto-status");
      const metricPromotions = document.querySelector("#metric-promotions-count");

      if (!tbodyCandidates || !tbodyReviews || !tbodyPromotions) return;

      tbodyCandidates.replaceChildren();
      tbodyReviews.replaceChildren();
      tbodyPromotions.replaceChildren();
      if (tbodyUnaccredited) tbodyUnaccredited.replaceChildren();

      const patchProposals = [];
      const historicalChecks = [];
      let hasVeto = false;
      const allReviews = [];

      for (const task of work) {
        for (const r of (task.reviews || [])) {
          if (r.decision === "VETO") hasVeto = true;
          allReviews.push({ taskTitle: task.title, taskId: task.id, review: r });
        }

        for (const p of (task.patch_proposals || [])) {
          patchProposals.push({
            id: p.id,
            taskTitle: task.title,
            taskId: task.id,
            proposerId: p.proposer_id,
            baseSha: p.base_sha,
            patchSha256: p.patch_sha256,
            changedPaths: p.changed_paths || [],
            status: p.status,
            validations: p.validations || [],
            applied: p.applied || false,
            taskReviews: task.reviews || []
          });
        }

        for (const ex of (task.executions || [])) {
          const res = ex.result || {};
          if (res.candidate_sha) {
            historicalChecks.push({
              id: ex.id,
              taskTitle: task.title,
              taskId: task.id,
              workerId: ex.worker_id || "worker-sandbox",
              candidateSha: res.candidate_sha,
              status: ex.status,
              conclusion: res.conclusion || ("código " + res.exit_code),
              checkId: res.check_id || "check",
              capabilityId: res.capability_id,
              capabilityVersion: res.capability_version,
              taskReviews: task.reviews || []
            });
          }
        }
      }

      if (metricCandidates) {
        metricCandidates.textContent = patchProposals.length + " propuestas · " + historicalChecks.length + " checks";
      }
      if (metricPromotions) {
        metricPromotions.textContent = "0";
      }
      if (metricVeto) {
        if (hasVeto) {
          metricVeto.textContent = "VETO ACTIVO";
          metricVeto.classList.add("metric-value--danger");
          metricVeto.classList.remove("metric-value--ok");
          const gatePill = document.querySelector("#gate-pill");
          if (gatePill) gatePill.textContent = "VETO ACTIVO · INTEGRACIÓN PROHIBIDA";
        } else {
          metricVeto.textContent = "Sin veto en DB";
          metricVeto.classList.remove("metric-value--danger");
          metricVeto.classList.add("metric-value--ok");
        }
      }

      // Tabla 1: Propuestas de Parche y Comprobaciones de Commits Históricos
      if (!patchProposals.length && !historicalChecks.length) {
        const tr = node("tr");
        const td = node("td", "No hay propuestas de parche ni comprobaciones de commits registradas en este proyecto.", "empty-state");
        td.colSpan = 9;
        tr.append(td);
        tbodyCandidates.append(tr);
      } else {
        // Propuestas de parche activas
        for (const p of patchProposals) {
          const tr = node("tr");
          const tdType = node("td");
          tdType.append(node("strong", "Propuesta de Parche " + p.id.slice(0, 8)));
          tr.append(tdType);

          tr.append(node("td", p.taskTitle));
          tr.append(node("td", p.proposerId));

          const tdBase = node("td");
          tdBase.append(node("code", (p.baseSha ? p.baseSha.slice(0, 12) : "—"), "sha-mono"));
          tr.append(tdBase);

          const tdPatch = node("td");
          tdPatch.append(node("code", (p.patchSha256 ? p.patchSha256.slice(0, 12) : "—"), "sha-mono"));
          tr.append(tdPatch);

          const tdTree = node("td");
          let treeVal = "—";
          if (p.validations.length) treeVal = p.validations[0].candidate_tree;
          tdTree.append(node("code", treeVal.slice(0, 12), "sha-mono"));
          tr.append(tdTree);

          const tdVal = node("td");
          if (p.validations.length) {
            tdVal.append(node("span", "Validado en árbol aislado", "pill approve"));
          } else {
            tdVal.append(node("span", "Validación aislada pendiente", "pill reject"));
          }
          tr.append(tdVal);

          const tdRev = node("td");
          if (p.taskReviews.length) {
            for (const r of p.taskReviews) {
              const pillClass = r.decision === "VETO" ? "pill veto" : r.decision === "APPROVE" ? "pill approve" : "pill reject";
              tdRev.append(node("span", r.decision, pillClass));
            }
          } else {
            tdRev.append(node("span", "Sin dictamen", "pill"));
          }
          tr.append(tdRev);

          const tdInt = node("td");
          tdInt.append(node("span", "Aislado (no aplicado al canónico)", "pill"));
          tr.append(tdInt);

          tbodyCandidates.append(tr);
        }

        // Comprobaciones históricas sobre commits
        for (const hc of historicalChecks) {
          const tr = node("tr");
          const tdType = node("td");
          tdType.append(node("strong", "Check Histórico " + hc.id.slice(0, 8)));
          tdType.append(node("div", "Ejecución en sandbox", "meta-line"));
          tr.append(tdType);

          tr.append(node("td", hc.taskTitle));
          tr.append(node("td", hc.workerId));

          // Base SHA: No aplica
          tr.append(node("td", "No aplica", "meta-line"));

          // SHA256 Parche: No aplica
          tr.append(node("td", "No aplica", "meta-line"));

          // Commit Evaluado
          const tdTree = node("td");
          tdTree.append(node("code", hc.candidateSha.slice(0, 12), "sha-mono"));
          tr.append(tdTree);

          // Verificación Técnica
          const tdVal = node("td");
          tdVal.append(node("span", "Check: " + (hc.capabilityId ? hc.capabilityId + " (" + hc.conclusion + ")" : hc.conclusion), "pill execution"));
          tr.append(tdVal);

          // Dictamen Auditor
          const tdRev = node("td");
          tdRev.append(node("span", "Check técnico · No autoriza promoción", "pill"));
          tr.append(tdRev);

          // Estado de Integración
          const tdInt = node("td");
          tdInt.append(node("span", "Histórico · No acreditado para integración", "pill reject"));
          tr.append(tdInt);

          tbodyCandidates.append(tr);
        }
      }

      // Tabla 2: Dictámenes, Veto y Bloqueos de Auditoría
      if (!allReviews.length) {
        const tr = node("tr");
        const td = node("td", "No hay revisiones ni dictámenes registrados para las tareas de este proyecto.", "empty-state");
        td.colSpan = 7;
        tr.append(td);
        tbodyReviews.append(tr);
      } else {
        for (const item of allReviews) {
          const r = item.review;
          const tr = node("tr");
          tr.append(node("td", item.taskTitle));
          tr.append(node("td", r.reviewer_id));

          const tdDec = node("td");
          const pillClass = r.decision === "VETO" ? "pill veto" : r.decision === "APPROVE" ? "pill approve" : "pill reject";
          tdDec.append(node("span", r.decision, pillClass));
          tr.append(tdDec);

          const tdVeto = node("td");
          if (r.decision === "VETO") {
            tdVeto.append(node("strong", "SÍ — INTEGRACIÓN DETENIDA", "pill veto"));
          } else {
            tdVeto.append(node("span", "No"));
          }
          tr.append(tdVeto);

          const tdSha = node("td");
          tdSha.append(node("code", (r.candidate_sha ? r.candidate_sha.slice(0, 12) : "sin SHA ligado"), "sha-mono"));
          tr.append(tdSha);

          tr.append(node("td", (r.evidence || []).join(", ") || "Sin referencias"));

          const tdBlock = node("td");
          if (r.decision === "VETO") {
            tdBlock.append(node("span", "Veto activo: promoción estrictamente prohibida", "pill veto"));
          } else if (r.decision === "REJECT") {
            tdBlock.append(node("span", "Rechazo activo: requiere subsanación previa", "pill reject"));
          } else {
            tdBlock.append(node("span", "Bloqueada: revisión local no certifica independencia externa", "pill"));
          }
          tr.append(tdBlock);

          tbodyReviews.append(tr);
        }
      }

      // Tabla 3: Registro de Promociones Acreditadas e Historial de Integración
      // Honest state: exactly 0 accredited promotions exist in the repository
      const trPromoEmpty = node("tr");
      const tdPromoEmpty = node("td", "", "empty-state");
      tdPromoEmpty.colSpan = 6;
      tdPromoEmpty.classList.add("promotion-empty");
      tdPromoEmpty.append(node("div", "Cero Promociones Acreditadas", "strong"));
      tdPromoEmpty.append(node("div", "No existen promociones acreditadas ni ejecutadas en el repositorio canónico. Ningún candidato cuenta con autorización verificable de integración ni certificación independiente de auditoría bajo GOV-REV-001 (Constitución arts. 3 y 6). La integración permanece estrictamente bloqueada (fail-closed).", "meta-line"));
      trPromoEmpty.append(tdPromoEmpty);
      tbodyPromotions.append(trPromoEmpty);

      // Tabla 4: Ramas Candidatas en Desarrollo (Sin Promoción Acreditada)
      if (tbodyUnaccredited) {
        const unaccreditedBranches = [
          {
            branch: "feat/control-center-daily-ui (PR #15)",
            sha: "142d6c5c542e6b6f790175f7a8cf14c23c6be73b",
            base: "origin/feat/capability-backed-repository-checks (91eb754)",
            status: "NO ACREDITADA (Gate cerrado)",
            missing: "Auditoría independiente externa certificada + Autoridad de integración",
            condition: "Bloqueada en espera de estabilización de dependencias base (#10 y #11)"
          },
          {
            branch: "feat/capability-backed-repository-checks (PR #11)",
            sha: "91eb7543658fe92875cefa3de1e27704d830feb7",
            base: "origin/feat/capability-registry-runtime (#10)",
            status: "NO ACREDITADA (Gate cerrado)",
            missing: "Dictamen independiente GOV-REV-001 vinculado a SHA exacto",
            condition: "Bloqueada por consolidación pendiente de PR #10"
          },
          {
            branch: "feat/capability-registry-runtime (PR #10)",
            sha: "c35ff310135b9b76d5dc965d762acd6e4ebade10",
            base: "main",
            status: "NO ACREDITADA (Gate cerrado)",
            missing: "Resolución de CI base y auditoría técnica independiente",
            condition: "Base de la cadena de dependencias P0"
          },
          {
            branch: "docs/agent-operating-rules (PR #16)",
            sha: "ea549700ad82405dd0f64eb9121aa116d281a022",
            base: "main",
            status: "NO ACREDITADA (Gate cerrado)",
            missing: "Auditoría independiente y resolución de CI externo en test_core.py",
            condition: "Documento de reglas; sin adopción automática por agentes"
          }
        ];

        for (const ub of unaccreditedBranches) {
          const tr = node("tr");
          tr.append(node("td", ub.branch));
          const tdSha = node("td");
          tdSha.append(node("code", ub.sha.slice(0, 12), "sha-mono"));
          tr.append(tdSha);
          tr.append(node("td", ub.base));
          const tdStatus = node("td");
          tdStatus.append(node("span", ub.status, "pill veto"));
          tr.append(tdStatus);
          tr.append(node("td", ub.missing));
          tr.append(node("td", ub.condition));
          tbodyUnaccredited.append(tr);
        }
      }
    }

    function openTaskDrawer(task) {
      drawerTitle.textContent = task.title;
      drawerTaskId.textContent = "ID de tarea: " + task.id;
      drawerTaskStatus.textContent = labels[task.status] || task.status;

      // Acceptance Criteria
      drawerAcceptance.replaceChildren();
      const criteria = Array.isArray(task.acceptance_criteria) ? task.acceptance_criteria : [];
      if (criteria.length) {
        for (const c of criteria) {
          drawerAcceptance.append(node("li", c));
        }
      } else {
        drawerAcceptance.append(node("li", "Sin criterios de aceptación explícitos."));
      }

      // Evidence
      drawerEvidence.replaceChildren();
      const evidence = Array.isArray(task.evidence) ? task.evidence : [];
      if (evidence.length) {
        const ul = node("ul");
        for (const ev of evidence) ul.append(node("li", ev));
        drawerEvidence.append(ul);
      } else {
        drawerEvidence.append(node("div", "Sin referencias de evidencia registradas.", "meta-line"));
      }

      // Executions
      drawerExecutions.replaceChildren();
      const executions = Array.isArray(task.executions) ? task.executions : [];
      if (executions.length) {
        for (const ex of executions) {
          const res = ex.result || {};
          const card = node("div", "", "catalog-card");
          card.append(node("strong", "Ejecución " + ex.id + " · " + ex.status));
          card.append(node("div", "Worker: " + (ex.worker_id || "no asignado") + " · Intentos: " + ex.attempts, "meta-line"));
          if (res.capability_id) card.append(node("div", "Capacidad: " + res.capability_id + " · " + res.capability_version, "meta-line"));
          if (res.check_id) card.append(node("div", "Check: " + res.check_id + " · " + (res.conclusion || "sin dictamen"), "meta-line"));
          if (res.candidate_sha) card.append(node("div", "SHA Candidato: " + res.candidate_sha, "meta-line"));
          if (res.exit_code !== undefined) card.append(node("div", "Código de salida: " + res.exit_code, "meta-line"));
          if (res.stdout) card.append(node("pre", res.stdout, "code-block"));
          if (res.stderr) card.append(node("pre", res.stderr, "code-block"));
          drawerExecutions.append(card);
        }
      } else {
        drawerExecutions.append(node("div", "Sin ejecuciones registradas.", "meta-line"));
      }

      // Reviews
      drawerReviews.replaceChildren();
      const reviews = Array.isArray(task.reviews) ? task.reviews : [];
      if (reviews.length) {
        for (const rev of reviews) {
          const card = node("div", "", "catalog-card");
          const disposition = rev.decision === "VETO" ? "VETO ACTIVO" :
            rev.decision === "APPROVE" ? "Aprobación registrada" :
            rev.decision === "REJECT" ? "Rechazo registrado" : "Dictamen histórico";
          card.append(node("strong", disposition + " · " + (rev.sha_bound ? "SHA " + rev.candidate_sha : "sin SHA verificable")));
          card.append(node("div", "Revisor: " + rev.reviewer_id, "meta-line"));
          card.append(node("div", "Referencias: " + ((rev.evidence || []).join(", ") || "sin referencias"), "meta-line"));
          card.append(node("div", "Fecha: " + rev.created_at, "meta-line"));
          card.append(node("div", "Registro almacenado; independencia y validez no certificadas.", "meta-line"));
          drawerReviews.append(card);
        }
      } else {
        drawerReviews.append(node("div", "Sin dictámenes de auditor registrados.", "meta-line"));
      }

      // Proposals
      drawerProposals.replaceChildren();
      const proposals = Array.isArray(task.patch_proposals) ? task.patch_proposals : [];
      if (proposals.length) {
        for (const p of proposals) {
          const card = node("div", "", "catalog-card");
          card.append(node("strong", "Parche " + p.status + " · no aplicado"));
          card.append(node("div", "Agente proponente: " + p.proposer_id, "meta-line"));
          card.append(node("div", "SHA base: " + p.base_sha, "meta-line"));
          card.append(node("div", "Digest del parche: " + p.patch_sha256, "meta-line"));
          card.append(node("div", "Rutas: " + (p.changed_paths || []).join(", "), "meta-line"));
          card.append(node("div", "Fecha: " + p.created_at, "meta-line"));
          const validations = Array.isArray(p.validations) ? p.validations : [];
          if (validations.length) {
            for (const v of validations) {
              card.append(node("div", "Validado por " + v.validator_id + " · árbol " + v.candidate_tree, "meta-line"));
            }
          } else {
            card.append(node("div", "Validación aislada pendiente", "meta-line"));
          }
          card.append(node("div", "Contenido del diff: reservado a credencial AUDITOR en revisión (HTTP 403 para agentes)", "meta-line"));
          card.append(node("div", "Aplicación al repositorio: no disponible", "meta-line disclaimer"));
          drawerProposals.append(card);
        }
      } else {
        drawerProposals.append(node("div", "Sin propuestas de parche registradas.", "meta-line"));
      }

      drawerOverlay.classList.add("open");
      drawerOverlay.setAttribute("aria-hidden", "false");
    }

    function closeTaskDrawer() {
      drawerOverlay.classList.remove("open");
      drawerOverlay.setAttribute("aria-hidden", "true");
    }

    // Navigation Tabs Event Listeners
    document.querySelectorAll(".nav-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".nav-tab").forEach(t => {
          t.classList.remove("active");
          t.setAttribute("aria-selected", "false");
        });
        document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
        tab.classList.add("active");
        tab.setAttribute("aria-selected", "true");
        const targetId = tab.dataset.tab;
        const targetEl = document.querySelector("#" + targetId);
        if (targetEl) targetEl.classList.add("active");
      });
    });

    // Form and Controls Event Listeners
    authForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const val = authTokenInput.value.trim();
      if (!val) return;
      readerToken = val;
      loadProjects().catch(err => {
        clearReaderSession();
        message.replaceChildren(node("p", "Error al autenticar: " + err.message, "meta"));
      });
    });

    disconnectBtn.addEventListener("click", () => {
      clearReaderSession();
    });

    reloadBtn.addEventListener("click", () => {
      loadProjects().catch(e => {
        message.textContent = e.message;
      });
    });

    project.addEventListener("change", () => {
      loadBoard();
    });

    document.querySelector("#filter-task-status").addEventListener("change", () => {
      renderTasksTable(currentWorkItems);
    });

    document.querySelector("#filter-cap-type").addEventListener("change", () => {
      renderCapabilities(currentCapabilities, currentEvaluations);
    });

    drawerClose.addEventListener("click", closeTaskDrawer);
    drawerOverlay.addEventListener("click", (e) => {
      if (e.target === drawerOverlay) closeTaskDrawer();
    });
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && drawerOverlay.classList.contains("open")) {
        closeTaskDrawer();
      }
    });

    const btnPromote = document.querySelector("#btn-promote-candidate");
    if (btnPromote) {
      btnPromote.addEventListener("click", () => {
        alert("Operación denegada: la sesión actual carece de autoridad verificable de integración. La promoción requiere dictamen de auditoría independiente externa conforme a GOV-REV-001.");
      });
    }

    // Initial load
    loadProjects().catch(e => {
      message.textContent = "Autenticación requerida para consultar el núcleo local.";
    });
