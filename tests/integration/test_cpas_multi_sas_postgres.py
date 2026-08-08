"""P5-004 follow-up: CPAS / Multi-SAS concurrency against real PostgreSQL."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import pytest
from sqlalchemy import text

import database
from models.models import (
    AdminInjectedData,
    Cbsd,
    FadDump,
    Grant,
    PeerFadRecord,
    PeerSas,
)
from services.concurrency import (
    _supports_advisory_lock,
    acquire_cpas_pipeline_xact_lock,
)
from services.cpas_service import (
    KIND_CPAS_AUDIT,
    execute_cpas_pipeline,
    freeze_cpas_snapshot,
)
from services.fad_service import fad_cbsd_id, get_published_dump

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

_TABLES = (
    "fad_files",
    "fad_dumps",
    "peer_fad_records",
    "peer_sas",
    "grants",
    "cbsds",
    "admin_injected_data",
)


def _pg_url() -> str | None:
    return os.environ.get("SAS_TEST_DATABASE_URL") or None


def _start_ephemeral_postgres() -> tuple[str, str]:
    if shutil.which("docker") is None:
        raise RuntimeError("docker executable not found")

    container = f"sas-p5-004-cpas-pg-{os.getpid()}"
    user, password, db = "sas", "sas_test", "sas"
    host_port = str(55452 + (os.getpid() % 1000))
    subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)
    run = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container,
            "-e",
            f"POSTGRES_USER={user}",
            "-e",
            f"POSTGRES_PASSWORD={password}",
            "-e",
            f"POSTGRES_DB={db}",
            "-p",
            f"127.0.0.1:{host_port}:5432",
            "postgres:15-alpine",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        detail = (run.stderr or run.stdout or "").strip()
        raise RuntimeError(f"docker run postgres failed: {detail}")

    url = f"postgresql+psycopg2://{user}:{password}@127.0.0.1:{host_port}/{db}"
    probe_code = (
        "import sqlalchemy as sa\n"
        f"e = sa.create_engine({url!r})\n"
        "with e.connect() as c:\n"
        "    c.exec_driver_sql('SELECT 1')\n"
    )
    deadline = time.time() + 90
    last_err = ""
    while time.time() < deadline:
        probe = subprocess.run(
            [PYTHON, "-c", probe_code],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if probe.returncode == 0:
            return url, container
        last_err = (probe.stderr or probe.stdout or "").strip()
        time.sleep(1.0)

    subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)
    raise RuntimeError(f"ephemeral postgres not ready: {last_err}")


@pytest.fixture(scope="module")
def postgres_url() -> Iterator[str]:
    env = _pg_url()
    if env:
        yield env
        return

    candidate = "postgresql+psycopg2://sas:sas_test@127.0.0.1:55432/sas"
    try:
        from sqlalchemy import create_engine

        eng = create_engine(candidate)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        yield candidate
        return
    except Exception:
        pass

    if shutil.which("docker") is None:
        pytest.skip(
            "PostgreSQL unavailable: set SAS_TEST_DATABASE_URL or install Docker"
        )

    try:
        url, container = _start_ephemeral_postgres()
    except RuntimeError as exc:
        pytest.fail(str(exc))

    try:
        yield url
    finally:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)


@pytest.fixture
def pg_session(postgres_url: str) -> Iterator:
    previous = str(database.engine.url)
    database.rebind_engine(postgres_url)
    database.init_db(retries=5, delay_seconds=0.5)
    session = database.SessionLocal()
    try:
        for table in _TABLES:
            try:
                session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            except Exception:
                session.rollback()
        session.commit()
        yield session
    finally:
        session.close()
        database.rebind_engine(previous)


def _silence_external_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid network / external DB; do not mock CPAS/FAD advisory locks."""
    monkeypatch.setattr(
        "services.database_sync_service.sync_injected_database_urls",
        lambda db: None,
    )
    monkeypatch.setattr(
        "services.cpas_service.run_peer_fad_sync",
        lambda db, client=None: {
            "peers": 0,
            "ok": 0,
            "failed": 0,
            "skipped_same_generation": 0,
            "errors": [],
        },
    )


def _seed_conflict_grant(db, *, fcc: str = "fcc-pg", serial: str = "sn-pg", grant_id: str = "G-PG") -> Grant:
    cbsd = Cbsd(
        cbsd_id=f"{fcc}/{serial}",
        fcc_id=fcc,
        cbsd_serial_number=serial,
        user_id="u-pg",
        registration_json=json.dumps(
            {
                "fccId": fcc,
                "cbsdSerialNumber": serial,
                "cbsdCategory": "A",
                "airInterface": {"radioTechnology": "E_UTRA"},
                "measCapability": [],
                "installationParam": {
                    "latitude": 39.0,
                    "longitude": -100.0,
                    "height": 10,
                    "heightType": "AGL",
                },
            }
        ),
    )
    db.add(cbsd)
    db.flush()
    expire = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1)
    grant = Grant(
        grant_id=grant_id,
        cbsd_pk=cbsd.id,
        cbsd_id=cbsd.cbsd_id,
        low_frequency=3550000000,
        high_frequency=3560000000,
        max_eirp=20.0,
        channel_type="GAA",
        grant_expire_time=expire.replace(tzinfo=None),
        terminated=False,
        grant_json="{}",
    )
    db.add(grant)
    peer = PeerSas(certificate_hash=f"peer-{fcc}", url="https://localhost/v1.3")
    db.add(peer)
    db.flush()
    rid = fad_cbsd_id(fcc, serial)
    db.add(
        PeerFadRecord(
            peer_sas_id=peer.id,
            record_type="cbsd",
            record_id=rid,
            data_json=json.dumps(
                {"id": rid, "grants": [{"id": "peer-g", "terminated": False}]}
            ),
        )
    )
    db.commit()
    return grant


def _completed_audits(db) -> list[dict[str, Any]]:
    rows = db.query(AdminInjectedData).filter_by(kind=KIND_CPAS_AUDIT).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            data = json.loads(row.data_json or "{}")
        except json.JSONDecodeError:
            continue
        if data.get("event") == "cpas_completed":
            out.append(data)
    return out


def _failed_audits(db) -> list[dict[str, Any]]:
    rows = db.query(AdminInjectedData).filter_by(kind=KIND_CPAS_AUDIT).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            data = json.loads(row.data_json or "{}")
        except json.JSONDecodeError:
            continue
        if data.get("event") == "cpas_failed":
            out.append(data)
    return out


def test_postgres_cpas_advisory_lock_blocks_peer_session(pg_session):
    assert _supports_advisory_lock(pg_session) is True
    barrier = threading.Barrier(2)
    peer_blocked = threading.Event()
    peer_acquired = threading.Event()
    release_holder = threading.Event()
    holder_saw_advisory = threading.Event()

    def holder() -> None:
        s = database.SessionLocal()
        try:
            acquire_cpas_pipeline_xact_lock(s)
            n = s.execute(
                text(
                    "SELECT COUNT(*) FROM pg_locks "
                    "WHERE locktype = 'advisory' AND granted = true"
                )
            ).scalar()
            if int(n) >= 1:
                holder_saw_advisory.set()
            barrier.wait(timeout=10)
            release_holder.wait(timeout=5.0)
            s.commit()
        finally:
            s.close()

    def waiter() -> None:
        barrier.wait(timeout=10)
        s = database.SessionLocal()
        try:
            s.execute(text("SET LOCAL lock_timeout = '400ms'"))
            try:
                acquire_cpas_pipeline_xact_lock(s)
                peer_acquired.set()
            except Exception:
                peer_blocked.set()
            finally:
                release_holder.set()
                s.rollback()
        finally:
            s.close()

    t1 = threading.Thread(target=holder)
    t2 = threading.Thread(target=waiter)
    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)
    assert holder_saw_advisory.is_set()
    assert peer_blocked.is_set()
    assert not peer_acquired.is_set()


def test_postgres_concurrent_cpas_workers_serialize_and_reevaluate(
    pg_session, monkeypatch
):
    """Two independent sessions; second re-evaluates after lock — no double-terminate race."""
    _silence_external_sync(monkeypatch)
    grant = _seed_conflict_grant(pg_session)
    barrier = threading.Barrier(2)
    results: list[dict[str, Any] | str] = []
    lock = threading.Lock()

    def worker(label: str) -> None:
        s = database.SessionLocal()
        try:
            barrier.wait(timeout=15)
            result = execute_cpas_pipeline(s)
            with lock:
                results.append({"label": label, **result})
        except Exception as exc:  # noqa: BLE001
            with lock:
                results.append(f"err:{label}:{type(exc).__name__}:{exc}")
        finally:
            s.close()

    threads = [
        threading.Thread(target=worker, args=("w1",)),
        threading.Thread(target=worker, args=("w2",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert len(results) == 2
    assert all(isinstance(r, dict) for r in results), results
    assert all(r.get("ok") is True for r in results)

    verify = database.SessionLocal()
    try:
        g = verify.query(Grant).filter_by(id=grant.id).one()
        assert g.terminated is True
        assert g.lifecycle_state == "TERMINATED"
        # Exactly one published FAD; both workers may have published sequentially.
        assert verify.query(FadDump).filter_by(published=True).count() == 1
        current = get_published_dump(verify)
        assert current is not None
        completed = _completed_audits(verify)
        assert len(completed) == 2
        # Second worker must not invent a second termination of an already-dead grant
        # with a contradictory final state — grant stays terminated once.
        terminations = [int(r.get("terminated_grants") or 0) for r in results]
        # Exactly one worker applies the termination; the other re-evaluates under
        # lock and sees the grant already TERMINATED (0 new terminations).
        assert sorted(terminations) == [0, 1], terminations
        assert verify.query(Grant).filter_by(terminated=True).count() == 1
    finally:
        verify.close()


def test_postgres_cpas_freeze_uses_peer_n_while_n1_arrives(
    pg_session, monkeypatch
):
    """Frozen peer snapshot N is used while concurrent session publishes N+1."""
    _silence_external_sync(monkeypatch)
    grant = _seed_conflict_grant(pg_session, fcc="fcc-n", serial="sn-n", grant_id="G-N")
    peer = pg_session.query(PeerSas).one()
    rid = fad_cbsd_id("fcc-n", "sn-n")

    # N has conflict; N+1 clears peer grants (would not terminate if used live).
    entered_critical = threading.Event()
    release_critical = threading.Event()
    n1_applied = threading.Event()
    from services import fad_service

    real_create = fad_service.create_full_activity_dump

    def _paused_create(db, *args, **kwargs):
        entered_critical.set()
        assert release_critical.wait(timeout=15)
        return real_create(db, *args, **kwargs)

    monkeypatch.setattr(
        "services.cpas_service.create_full_activity_dump", _paused_create
    )

    worker_result: dict[str, Any] = {}

    def worker() -> None:
        s = database.SessionLocal()
        try:
            worker_result.update(execute_cpas_pipeline(s))
        finally:
            s.close()

    t = threading.Thread(target=worker)
    t.start()
    assert entered_critical.wait(timeout=30)

    # Mid-run: replace peer FAD with N+1 (no conflict).
    peer_id = peer.id
    publisher = database.SessionLocal()
    try:
        publisher.query(PeerFadRecord).filter_by(peer_sas_id=peer_id).delete()
        publisher.add(
            PeerFadRecord(
                peer_sas_id=peer_id,
                record_type="cbsd",
                record_id=rid,
                data_json=json.dumps({"id": rid, "grants": []}),
            )
        )
        p_row = publisher.query(PeerSas).filter_by(id=peer_id).one()
        p_row.last_fad_generation = "N+1"
        publisher.commit()
        n1_applied.set()
    finally:
        publisher.close()

    release_critical.set()
    t.join(timeout=60)

    assert n1_applied.is_set()
    assert worker_result.get("ok") is True
    # Run that froze N must still terminate (N had conflict).
    assert worker_result.get("terminated_grants") == 1
    assert any(d["reason"] == "peer_same_cbsd_grant" for d in worker_result["decisions"])

    verify = database.SessionLocal()
    try:
        g = verify.query(Grant).filter_by(id=grant.id).one()
        assert g.terminated is True
        # Durable peer store is N+1 for the next run.
        row = (
            verify.query(PeerFadRecord)
            .filter_by(peer_sas_id=peer_id, record_id=rid)
            .one()
        )
        assert json.loads(row.data_json)["grants"] == []
        p = verify.query(PeerSas).filter_by(id=peer_id).one()
        assert p.last_fad_generation == "N+1"

        # Next run sees N+1 (no conflict) and frozen grant set is empty → no new term.
        nxt = execute_cpas_pipeline(verify)
        assert nxt["ok"] is True
        assert nxt["terminated_grants"] == 0
    finally:
        verify.close()


def test_postgres_cpas_rollback_releases_lock_for_peer(
    pg_session, monkeypatch
):
    """Failure before final commit rolls back; peer worker proceeds; no false COMPLETED."""
    _silence_external_sync(monkeypatch)
    grant = _seed_conflict_grant(
        pg_session, fcc="fcc-rb", serial="sn-rb", grant_id="G-RB"
    )

    fail_once = {"done": False}
    from services import fad_service

    real_create = fad_service.create_full_activity_dump

    def _fail_first(db, *args, **kwargs):
        if not fail_once["done"]:
            fail_once["done"] = True
            raise RuntimeError("inject cpas fad failure")
        return real_create(db, *args, **kwargs)

    monkeypatch.setattr("services.cpas_service.create_full_activity_dump", _fail_first)

    first = database.SessionLocal()
    try:
        with pytest.raises(RuntimeError, match="inject cpas fad failure"):
            execute_cpas_pipeline(first)
    finally:
        first.close()

    # Grant must not stay terminated after failed critical section.
    check = database.SessionLocal()
    try:
        g = check.query(Grant).filter_by(id=grant.id).one()
        assert g.terminated is False
        assert _completed_audits(check) == []
        assert len(_failed_audits(check)) >= 1
    finally:
        check.close()

    # Peer session acquires lock and completes successfully.
    second = database.SessionLocal()
    try:
        result = execute_cpas_pipeline(second)
        assert result["ok"] is True
        assert result["terminated_grants"] == 1
        g = second.query(Grant).filter_by(id=grant.id).one()
        assert g.terminated is True
        completed = _completed_audits(second)
        assert len(completed) == 1
        assert second.query(FadDump).filter_by(published=True).count() == 1
    finally:
        second.close()


def test_postgres_multiprocess_cpas_one_valid_final_state(postgres_url: str):
    """Independent processes (no shared RLock) still serialize via pg_advisory_xact_lock."""
    previous = str(database.engine.url)
    database.rebind_engine(postgres_url)
    database.init_db(retries=5, delay_seconds=0.5)
    setup = database.SessionLocal()
    try:
        for table in _TABLES:
            setup.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        setup.commit()
        _seed_conflict_grant(setup, fcc="fcc-mp", serial="sn-mp", grant_id="G-MP")
    finally:
        setup.close()

    worker_code = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
import database
from services.cpas_service import execute_cpas_pipeline

database.rebind_engine({postgres_url!r})

# Silence external sync inside the worker process (locks remain real).
import services.database_sync_service as dbs
import services.cpas_service as cpas
dbs.sync_injected_database_urls = lambda db: None
cpas.run_peer_fad_sync = lambda db, client=None: {{
    "peers": 0, "ok": 0, "failed": 0, "skipped_same_generation": 0, "errors": []
}}

s = database.SessionLocal()
try:
    result = execute_cpas_pipeline(s)
    print(result["ok"], result["terminated_grants"], result["dump_id"])
finally:
    s.close()
"""
    procs = [
        subprocess.Popen(
            [PYTHON, "-c", worker_code],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    outputs: list[str] = []
    for p in procs:
        out, err = p.communicate(timeout=90)
        assert p.returncode == 0, err
        outputs.append(out.strip().splitlines()[-1])

    assert len(outputs) == 2
    parsed = [line.split() for line in outputs]
    assert all(parts[0] == "True" for parts in parsed)

    verify = database.SessionLocal()
    try:
        assert verify.query(Grant).filter_by(grant_id="G-MP", terminated=True).count() == 1
        assert verify.query(FadDump).filter_by(published=True).count() == 1
        assert len(_completed_audits(verify)) == 2
        # Advisory coordination — not merely process-local RLock — produced one
        # coherent published dump and one terminated grant.
        assert get_published_dump(verify) is not None
    finally:
        verify.close()
        database.rebind_engine(previous)


def test_postgres_freeze_captures_peer_records(pg_session):
    grant = _seed_conflict_grant(pg_session, fcc="fcc-fz", serial="sn-fz", grant_id="G-FZ")
    del grant
    snap = freeze_cpas_snapshot(pg_session)
    assert snap.peer_record_count >= 1
    assert any(rt == "cbsd" for _pid, rt, _rid, _data in snap.peer_records)


def test_postgres_dpa_collect_uses_frozen_local_pks(pg_session):
    """P7-005: DPA membership follows CpasSnapshot PKs on real PostgreSQL."""
    from services.cpas_service import evaluate_cpas_protections
    from services.dpa_protection import collect_active_dpa_grants

    grant_a = _seed_conflict_grant(
        pg_session, fcc="fcc-mcp-a", serial="sn-mcp-a", grant_id="G-MCP-A"
    )
    snap_n = freeze_cpas_snapshot(pg_session)
    grant_b = _seed_conflict_grant(
        pg_session, fcc="fcc-mcp-b", serial="sn-mcp-b", grant_id="G-MCP-B"
    )
    pg_session.commit()

    frozen = collect_active_dpa_grants(pg_session, grant_pks=snap_n.active_grant_pks)
    frozen_ids = {g.grant_id for g in frozen}
    assert "G-MCP-A" in frozen_ids
    assert "G-MCP-B" not in frozen_ids

    live = collect_active_dpa_grants(pg_session, grant_pks=None)
    live_ids = {g.grant_id for g in live}
    assert "G-MCP-A" in live_ids and "G-MCP-B" in live_ids

    decisions = evaluate_cpas_protections(pg_session, snap_n)
    assert all(d.grant_pk != grant_b.id for d in decisions)
    assert all(d.grant_id != "G-MCP-B" for d in decisions)

    snap_n1 = freeze_cpas_snapshot(pg_session)
    assert grant_a.id in snap_n1.active_grant_pks
    assert grant_b.id in snap_n1.active_grant_pks
    frozen_n1 = collect_active_dpa_grants(
        pg_session, grant_pks=snap_n1.active_grant_pks
    )
    assert {g.grant_id for g in frozen_n1} >= {"G-MCP-A", "G-MCP-B"}


def test_postgres_rf_snapshot_n_vs_n1_registration_mutation(pg_session):
    """C1: frozen local RF stays at generation N on real PostgreSQL."""
    from services.cpas_service import evaluate_cpas_protections

    grant = _seed_conflict_grant(
        pg_session, fcc="fcc-rf-n", serial="sn-rf-n", grant_id="G-RF-N"
    )
    snap_n = freeze_cpas_snapshot(pg_session)
    assert len(snap_n.local_grants) == 1
    assert snap_n.local_grants[0].latitude == pytest.approx(39.0)
    assert snap_n.local_grants[0].max_eirp_dbm_mhz == pytest.approx(20.0)

    cbsd = pg_session.query(Cbsd).filter_by(cbsd_id=grant.cbsd_id).one()
    cbsd.registration_json = json.dumps(
        {
            "cbsdCategory": "B",
            "installationParam": {
                "latitude": 41.25,
                "longitude": -95.0,
                "height": 25.0,
                "heightType": "AGL",
                "indoorDeployment": True,
            },
        }
    )
    cbsd.cbsd_category = "B"
    grant.max_eirp = 32.0
    pg_session.commit()

    # Re-evaluate generation N: frozen RF must ignore live mutations.
    assert snap_n.local_grants[0].latitude == pytest.approx(39.0)
    assert snap_n.local_grants[0].height_m == pytest.approx(10.0)
    assert snap_n.local_grants[0].cbsd_category == "A"
    assert snap_n.local_grants[0].indoor is False
    assert snap_n.local_grants[0].max_eirp_dbm_mhz == pytest.approx(20.0)
    evaluate_cpas_protections(pg_session, snap_n)

    snap_n1 = freeze_cpas_snapshot(pg_session)
    assert snap_n1.local_grants[0].latitude == pytest.approx(41.25)
    assert snap_n1.local_grants[0].height_m == pytest.approx(25.0)
    assert snap_n1.local_grants[0].cbsd_category == "B"
    assert snap_n1.local_grants[0].indoor is True
    assert snap_n1.local_grants[0].max_eirp_dbm_mhz == pytest.approx(32.0)
