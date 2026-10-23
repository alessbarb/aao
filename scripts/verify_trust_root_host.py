#!/usr/bin/python3 -I
"""Read-only host verifier for the trust-root install preconditions (BOOTSTRAP_DOSSIER).

Run by the CEO as root:  sudo /usr/bin/python3 -I verify_trust_root_host.py --expected-revision <sha>
It changes nothing. Exit 0 only if every check passes. Paste the full output in the bootstrap issue.

  1. Runtime exclusivity of the aao-auditor uid: only the auditor systemd units run as it, the account
     cannot be entered another way, and nobody but root (or the auditor itself, for its own git tree)
     can write the code it executes.
  2. Custody of the supervisor intake socket and its parent directory, the heartbeat, and the anchor.
"""
from __future__ import annotations

import argparse
import grp
import hashlib
import json
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
import sysconfig
from pathlib import Path

AUDITOR, SUPERVISOR, TRUST = "aao-auditor", "aao-supervisor", "aao-trust"
ANCHOR = Path("/etc/aao-audit/trust-anchor.json")
ANCHOR_FIELDS = {"schema", "policy_path", "policy_sha256", "auditor_uid", "auditor_public_key", "ledger_path",
                 "ledger_anchor_path", "attribution_path", "supervisor_public_key", "supervisor_key_id",
                 "supervisor_heartbeat_path", "supervisor_intake_socket"}
INTAKE_DIR = Path("/run/aao-veto-intake")
INTAKE_SOCKET = INTAKE_DIR / "veto.sock"
HEARTBEAT = Path("/var/lib/aao-heartbeat/heartbeat.json")
AUDITOR_ROOT = Path("/srv/aao/frozen/aao-auditor")
AUDITOR_CGROUP = re.compile(r"^0::/system\.slice/(system-aao\\x2dauditor\.slice/)?aao-auditor(@[^/]+|-dispatch)\.service$")
INTAKE_CGROUP = re.compile(r"^0::/system\.slice/aao-supervisor-intake\.service$")
TOOLS = ("git", "bwrap", "openssl", "timeout", "prlimit")
results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> bool:
    results.append((ok, name, detail))
    return ok


def uid(name: str) -> int:
    return pwd.getpwnam(name).pw_uid


def gid(name: str) -> int:
    return grp.getgrnam(name).gr_gid


def ancestors_safe(path: Path, writers: set[int]) -> str:
    """'' if no ancestor of path is a symlink or writable by a uid outside `writers` (root always allowed)."""
    for parent in Path(os.path.abspath(path)).parents:
        info = os.lstat(parent)
        if stat.S_ISLNK(info.st_mode):
            return f"{parent} is a symlink"
        sticky_root = info.st_mode & stat.S_ISVTX and info.st_uid == 0
        if (info.st_mode & 0o022 and not sticky_root) or info.st_uid not in {0, *writers}:
            return f"{parent} owner={info.st_uid} mode={oct(stat.S_IMODE(info.st_mode))}"
    return ""


def tree_writers(root: Path, owners: set[int]) -> list[str]:
    """Entries under root (inclusive) owned outside `owners`, or group/other writable, or symlinks leaving root."""
    bad = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in [".", *dirs, *files]:
            path = Path(directory) if name == "." else Path(directory) / name
            info = os.lstat(path)
            if stat.S_ISLNK(info.st_mode):
                target = Path(os.path.realpath(path))
                if not (target.is_relative_to(root) or target.is_relative_to("/usr")):
                    bad.append(f"{path} -> {target}")
                continue
            if info.st_uid not in owners or info.st_mode & 0o022:
                bad.append(f"{path} owner={info.st_uid} mode={oct(stat.S_IMODE(info.st_mode))}")
            if len(bad) >= 5:
                return bad
    return bad


def processes() -> list[tuple[int, set[int], str]]:
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            status = (entry / "status").read_text()
            cgroup = (entry / "cgroup").read_text().strip()
        except OSError:
            continue
        uids = next((set(map(int, line.split()[1:])) for line in status.splitlines() if line.startswith("Uid:")), set())
        found.append((int(entry.name), uids, cgroup))
    return found


def sudoers_grants(target: str) -> list[str]:
    """Rules (outside root/%sudo/%admin) whose Runas list could reach `target`."""
    files = [Path("/etc/sudoers"), *sorted(Path("/etc/sudoers.d").glob("*"))]
    bad = []
    for path in files:
        for line in path.read_text(errors="replace").splitlines():
            line = line.split("#", 1)[0].strip()
            match = re.match(r"^(\S+)\s+\S+\s*=\s*\(([^)]*)\)", line)
            if not match or match.group(1) in ("root", "%sudo", "%admin"):
                continue
            runas = match.group(2).split(":", 1)[0]
            if any(item.strip() in ("ALL", target) for item in runas.split(",")):
                bad.append(f"{path}: {line}")
    return bad


def exclusivity(expected_revision: str) -> None:
    account = pwd.getpwnam(AUDITOR)
    check(account.pw_shell in ("/usr/sbin/nologin", "/sbin/nologin", "/bin/false"), "E1 auditor shell is nologin",
          account.pw_shell)
    try:
        shadow = next((line.split(":")[1] for line in Path("/etc/shadow").read_text().splitlines()
                       if line.startswith(AUDITOR + ":")), "")
    except OSError as error:
        shadow = repr(error)
    check(shadow[:1] in ("!", "*"), "E2 auditor password is locked", shadow[:1] if shadow[:1] not in "!*" else "")
    check(not Path(f"/var/lib/systemd/linger/{AUDITOR}").exists(), "E3 no systemd user linger for auditor")
    spool = [str(p) for d in ("/var/spool/cron/crontabs", "/var/spool/cron/atjobs") if Path(d).is_dir()
             for p in Path(d).iterdir() if p.lstat().st_uid == account.pw_uid]
    check(not spool, "E4 no cron/at jobs owned by auditor", ", ".join(spool))
    check(not Path(account.pw_dir, ".ssh", "authorized_keys").exists(), "E5 no SSH authorized_keys for auditor")
    grants = sudoers_grants(AUDITOR)
    check(not grants, "E6 no sudoers rule can run as auditor (besides root/%sudo/%admin)", "; ".join(grants))
    strays = [f"pid {pid} {cg}" for pid, uids, cg in processes()
              if account.pw_uid in uids and not AUDITOR_CGROUP.match(cg)]
    check(not strays, "E7 every auditor-uid process is inside an aao-auditor unit", "; ".join(strays[:5]))
    unit = Path("/etc/systemd/system/aao-auditor@.service")
    check(unit.is_file() and unit.stat().st_uid == 0 and not unit.stat().st_mode & 0o022 and
          not ancestors_safe(unit, set()), "E8 auditor unit is root-owned and protected")
    # Write closure of the auditor's code.
    tree, venv = AUDITOR_ROOT / "tree", AUDITOR_ROOT / "venv"
    problem = ancestors_safe(AUDITOR_ROOT, {uid(TRUST)})
    check(not problem, "E9 frozen auditor directory ancestors are protected", problem)
    bad = tree_writers(tree, {0, account.pw_uid})
    check(tree.is_dir() and not bad, "E10 auditor git tree: no writer besides root/auditor", "; ".join(bad))
    revision = subprocess.run(["git", "-c", "safe.directory=*", "-C", str(tree), "rev-parse", "HEAD"],
                              check=False, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-c", "safe.directory=*", "-C", str(tree), "status", "--porcelain",
                            "--untracked-files=all"], check=False, capture_output=True, text=True).stdout.strip()
    check(revision == expected_revision and not dirty, "E11 auditor tree is clean at the expected revision",
          f"HEAD={revision} dirty={bool(dirty)}")
    bad = tree_writers(venv, {0})
    check(venv.is_dir() and not bad, "E12 auditor venv is root-owned, no group/other write", "; ".join(bad))
    base = Path(os.path.realpath(venv / "bin" / "python"))
    stdlib = Path(sysconfig.get_paths()["stdlib"])
    bad = [f"{base}"] if base.lstat().st_uid != 0 or base.lstat().st_mode & 0o022 or ancestors_safe(base, set()) else []
    bad += tree_writers(stdlib, {0})
    check(not bad, "E13 base interpreter and stdlib are root-only writable", "; ".join(bad))
    bad = []
    for tool in TOOLS:
        path = shutil.which(tool, path="/usr/bin:/bin")
        real = Path(os.path.realpath(path)) if path else None
        if real is None or real.lstat().st_uid != 0 or real.lstat().st_mode & 0o022 or ancestors_safe(real, set()):
            bad.append(f"{tool}={real}")
    check(not bad, "E14 git/bwrap/openssl/timeout/prlimit are root-only writable", ", ".join(bad))
    key = Path(f"/var/lib/{AUDITOR}/keys/auditor-ed25519.pem")
    info = key.lstat() if key.exists() else None
    check(bool(info) and stat.S_ISREG(info.st_mode) and info.st_uid == account.pw_uid and
          stat.S_IMODE(info.st_mode) == 0o600, "E15 auditor signing key is auditor-owned 0600")


def socket_custody() -> None:
    supervisor, auditor_gid, ledger_gid = uid(SUPERVISOR), gid(AUDITOR), gid("aao-ledger-read")
    info = os.lstat(INTAKE_DIR) if INTAKE_DIR.exists() else None
    check(bool(info) and stat.S_ISDIR(info.st_mode) and info.st_uid == supervisor and info.st_gid == auditor_gid
          and stat.S_IMODE(info.st_mode) == 0o2750, "S1 intake dir is aao-supervisor:aao-auditor 2750",
          f"{info and (info.st_uid, info.st_gid, oct(stat.S_IMODE(info.st_mode)))}")
    problem = ancestors_safe(INTAKE_DIR, set())
    check(not problem, "S2 intake dir ancestors are root-owned and not writable", problem)
    info = os.lstat(INTAKE_SOCKET) if INTAKE_SOCKET.exists() else None
    check(bool(info) and stat.S_ISSOCK(info.st_mode) and info.st_uid == supervisor and info.st_gid == auditor_gid
          and stat.S_IMODE(info.st_mode) == 0o660, "S3 intake socket is aao-supervisor:aao-auditor 0660")
    inodes = {line.split()[6] for line in Path("/proc/net/unix").read_text().splitlines()[1:]
              if len(line.split()) >= 8 and line.split()[7] == str(INTAKE_SOCKET) and line.split()[5] == "01"}
    owners = set()
    for pid, uids, cgroup in processes():
        try:
            links = {os.readlink(fd) for fd in Path(f"/proc/{pid}/fd").iterdir()}
        except OSError:
            continue
        if any(f"socket:[{inode}]" in links for inode in inodes):
            owners.add((pid, frozenset(uids), cgroup))
    check(bool(owners) and all(uids == {supervisor} and INTAKE_CGROUP.match(cg) for _, uids, cg in owners),
          "S4 only aao-supervisor-intake.service listens on the socket", f"{sorted(owners, key=lambda o: o[0])}")
    info = os.lstat(HEARTBEAT.parent) if HEARTBEAT.parent.exists() else None
    check(bool(info) and info.st_uid == supervisor and info.st_gid == ledger_gid and
          stat.S_IMODE(info.st_mode) == 0o2750 and not ancestors_safe(HEARTBEAT.parent, set()),
          "S5 heartbeat dir is aao-supervisor:aao-ledger-read 2750")
    info = os.lstat(HEARTBEAT) if HEARTBEAT.exists() else None
    check(bool(info) and stat.S_ISREG(info.st_mode) and info.st_uid == supervisor and
          not info.st_mode & 0o022, "S6 heartbeat file is supervisor-owned, not group/other writable")


def anchor(expected_revision: str) -> None:
    info = os.lstat(ANCHOR) if ANCHOR.exists() else None
    if not check(bool(info) and stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
                 and not ancestors_safe(ANCHOR, set()), "T1 trust anchor is root-owned and protected"):
        return
    data = json.loads(ANCHOR.read_bytes())
    check(set(data) == ANCHOR_FIELDS, "T2 anchor has exactly the 12 fields of manifest_audit._ANCHOR_FIELDS")
    check(data.get("auditor_uid") == uid(AUDITOR), "T3 anchor auditor_uid is aao-auditor")
    check(data.get("supervisor_intake_socket") == str(INTAKE_SOCKET) and
          data.get("supervisor_heartbeat_path") == str(HEARTBEAT), "T4 anchor points at the verified socket/heartbeat")
    policy_path = Path(data.get("policy_path", "/nonexistent"))
    try:
        policy = json.loads(policy_path.read_bytes())
        digest = hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(",", ":"),
                                           ensure_ascii=False).encode()).hexdigest()
    except (OSError, ValueError):
        policy, digest = {}, ""
    check(digest == data.get("policy_sha256") and policy_path.stat().st_uid == uid(AUDITOR) if policy else False,
          "T5 pinned policy digest matches and the policy is auditor-owned")
    check(expected_revision in policy.get("trusted_auditor_revisions", []),
          "T6 policy trusts exactly the frozen auditor revision", f"{policy.get('trusted_auditor_revisions')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--expected-revision", required=True, help="trust-root candidate SHA (40 hex)")
    parser.add_argument("--smoke", action="store_true", help="non-root smoke run; unreadable checks FAIL")
    args = parser.parse_args()
    if os.geteuid() != 0 and not args.smoke:
        print("run as root (it only reads): sudo /usr/bin/python3 -I " + sys.argv[0], file=sys.stderr)
        return 2
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_revision):
        print("--expected-revision must be a full SHA", file=sys.stderr)
        return 2
    for section in (lambda: exclusivity(args.expected_revision), socket_custody,
                    lambda: anchor(args.expected_revision)):
        try:
            section()
        except (OSError, KeyError, ValueError) as error:
            check(False, "section aborted", repr(error))
    me = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(f"verify_trust_root_host.py sha256={me} expected_revision={args.expected_revision}")
    for ok, name, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    failed = sum(not ok for ok, _, _ in results)
    print(f"RESULT: {'PASS' if not failed else f'{failed} FAIL'} ({len(results)} checks)")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
