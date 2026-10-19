# GOV-REV-001 — Autonomous audit and independent assurance policy

**Version:** 1.1
**Status:** CEO-approved, 2026-10-19
**Authority:** CEO explicit approval in AAO governance conversation
**Scope:** AAO engineering and governed projects; subject to constitutional reserved powers

## Purpose and authority

AAO shall operate with autonomous technical verification and a functionally independent auditing capability. Routine code reviews and engineering acceptance checks shall not depend on human reviewers. CEO intervention is reserved for strategic, constitutional, high residual-risk, and other explicitly reserved decisions. This policy does not itself change the constitutional kernel, ratify a project mandate, accept M2-A, or authorize external effects or production deployment.

## Segregation of duties

Implementation, verification, audit, technical authorization, and governance must have identifiable, separated authority. An implementer may not certify its own changes; a second subagent sharing the same write authority, unprotected evidence and policy control does **not** establish independence. Auditor independence requires separate credentials and permissions, protected review criteria and evidence, freedom to reject, enforceable veto, independent resources, and tamper-evident attribution. Every claim of independence must be supported by evidence; otherwise classify it as provisional.

## Assurance levels

- **A — local, inert, disposable:** no real external effects, production deployment, real sensitive data, or irreversible/strategic consequences. Requires implementer-independent automated adversarial assessment, repeatable tests tied to exact revisions, findings disposition, and autonomous audit gating. A human technical reviewer is not required. CEO intervention only for reserved exceptions or decisions.
- **B — controlled runtime:** level A plus independently controlled isolation, permissions, stop and recovery tests, adversarial exercises, and risk-based predelegated technical authorization. No human technical review requirement by default; unapproved external capabilities remain prohibited.
- **C — operational deployment:** stronger autonomous separation of audit and executor, privilege isolation, ongoing monitoring, verified emergency controls, recovery evidence, and independent technical authorization. No default human review gate; operations above delegated risk/authority remain blocked pending CEO reserved decisions.
- **D — reserved authority:** AAO prepares analysis and evidence, but CEO alone authorizes constitutional, strategic, high residual-risk and other constitutionally reserved matters. This is an authority decision, not a requirement that CEO personally review code.

## Audit procedure and blocking

1. Freeze implementation source SHA and identify package SHA separately.
2. Define reviewed behavior, threats, operating limits, and required assurance level before evaluating results.
3. Obtain independent verification and adversarial audit findings with exact source references and reproducible methods.
4. Deny promotion on unresolved critical findings and any residual risk outside delegated authority; require remediation or competent disposition of high findings.
5. Recheck changed code and affected contracts after remediation.
6. Technical authorization must verify auditor identity, scope, veto, evidence integrity and delegated permission without relying on implementer claims.
7. Record verdict, scope, known limitations, residual risks, SHA, audit identity, policy version, and permitted/prohibited operations.
8. Never treat CI green, separate prompts, separate model vendors, or hashes alone as proof of functional audit independence.
9. Do not self-expand powers, weaken audit policy, or lift default-off external execution controls.

## Application to M2-A

M2-A remains a **local/inert** candidate. Level A is the intended assurance class, contingent on demonstrating actual separation for the specific review. The previous human-reviewer requirement in the draft review request is superseded by CEO-approved GOV-REV-001 v1.1 **for ordinary technical review**; any reserved CEO risk/acceptance authority remains unchanged. An internal Codex subagent review or this conversation's static analysis is insufficient on its own to prove independent functional audit.

The corrected source candidate is `31e7397be082394a6da95eadebd0d8ad6bf99c39`; review package checkpoint is `fedfcadf241126970ea5970fb26b4e869dce1d5f`. Re-pin code and package after any further changes. H-02 privileged database bypass, H-03 evidence authorship/identity and H-04 recovery limitations remain risks/limits, not automatically satisfied. A-10 must demonstrate appropriate Level A independence, and A-11 must record the competent authority's permitted disposition; neither is satisfied by this policy's approval.

## Governance

The audit function must have enforceable independent veto and controls it cannot waive itself. A periodic second-line review of the auditor's own code and policies must not be performed solely by the component under review. CEO emergency suspension and reserved powers remain independent of runtime agents.

Changes to this policy and any constitutional interactions require classification and authority verification. No constitutional amendment is inferred merely by committing this document. Where legal, contractual, or specifically reserved human verification is independently mandatory, this internal policy cannot waive it.
