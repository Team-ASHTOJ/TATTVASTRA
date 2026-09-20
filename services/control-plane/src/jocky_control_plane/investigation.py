"""Evidence-linked graph and conservative correlation over collected records."""

import ipaddress
from typing import Any
from uuid import UUID

import networkx as nx  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from jocky_control_plane.models import Finding, Observation, User
from jocky_control_plane.security import provenance, publish


def graph(db: Session, case_id: UUID, user: User, *, persist: bool = False) -> dict[str, Any]:
    observations = db.scalars(
        select(Observation)
        .where(Observation.organization_id == user.organization_id, Observation.case_id == case_id)
        .order_by(Observation.created_at, Observation.id)
    ).all()
    network = nx.MultiDiGraph()
    processes: dict[tuple[str, str, str], list[Observation]] = {}
    connections: list[Observation] = []
    for observation in observations:
        endpoint = str(observation.endpoint_id)
        data = observation.document["data"]
        pid = data.get("pid", data.get("process_id"))
        process_key = (endpoint, str(observation.job_id), str(pid))
        process = "process:" + ":".join(process_key)
        meta = {
            "simulation": observation.simulation,
            "simulation_label": observation.simulation_label,
            "observation_id": str(observation.id),
        }
        network.add_node(endpoint, type="Endpoint", **meta)
        if observation.collector == "processes" and pid is not None:
            processes.setdefault(process_key, []).append(observation)
            network.add_node(process, type="Process", pid=pid, **meta)
            network.add_edge(endpoint, process, relationship="Endpoint -> Process", **meta)
            username = data.get("username") or data.get("user")
            if username:
                account = f"user:{endpoint}:{username}"
                network.add_node(account, type="User", name=username, **meta)
                network.add_edge(account, process, relationship="User -> Process", **meta)
        elif observation.collector in {"connections", "network"}:
            connections.append(observation)
            connection_node = "connection:" + str(observation.id)
            network.add_node(connection_node, type="Connection", **meta)
            if pid is not None:
                network.add_node(process, type="Process", pid=pid, **meta)
                network.add_edge(
                    process, connection_node, relationship="Process -> Connection", **meta
                )
            remote = data.get("remote_address") or data.get("remote_ip") or data.get("remote")
            if remote:
                network.add_node("ip:" + str(remote), type="IP", address=remote, **meta)
                network.add_edge(
                    connection_node, "ip:" + str(remote), relationship="Connection -> IP", **meta
                )
        elif observation.collector in {
            "files",
            "file_metadata",
            "file_hash",
            "services",
            "drivers",
            "modules",
        }:
            kind = (
                "Service"
                if observation.collector == "services"
                else "File"
                if observation.collector.startswith("file")
                else "Driver"
            )
            node = f"{kind}:{observation.id}"
            network.add_node(node, type=kind, **meta)
            if kind != "Driver" and pid is None:
                continue  # No observed process association; do not invent one.
            parent = endpoint if kind == "Driver" else process
            if kind != "Driver":
                network.add_node(process, type="Process", pid=pid, **meta)
            network.add_edge(
                parent,
                node,
                relationship=f"{'Endpoint' if kind == 'Driver' else 'Process'} -> {kind}",
                **meta,
            )

    for connection in connections:
        data = connection.document["data"]
        pid = data.get("pid", data.get("process_id"))
        candidates = processes.get(
            (str(connection.endpoint_id), str(connection.job_id), str(pid)), []
        )
        started = data.get("process_start_time")
        if started is not None:
            candidates = [p for p in candidates if p.document["data"].get("start_time") == started]
        identities = {str(p.document["data"].get("start_time")) for p in candidates}
        if not candidates or len(identities) != 1:
            continue
        process_observation = candidates[-1]
        process_data = process_observation.document["data"]
        # Unknown/null signing status never means unsigned. Match within one job
        # to avoid joining a reused PID across unrelated collection sessions.
        if process_data.get("signed") is not False:
            continue
        try:
            external = ipaddress.ip_address(
                data.get("remote_address") or data.get("remote_ip") or data.get("remote", "")
            ).is_global
        except ValueError:
            continue
        if not external or process_observation.simulation != connection.simulation:
            continue
        rule_key = f"unsigned-external:{process_observation.id}:{connection.id}"
        finding = db.scalar(
            select(Finding).where(Finding.case_id == case_id, Finding.rule_key == rule_key)
        )
        if finding is None:
            if not persist:
                continue
            finding = Finding(
                **provenance(connection),
                case_id=case_id,
                rule_key=rule_key,
                title="Unsigned process with external connection",
                severity="MEDIUM",
                observation_ids=[str(process_observation.id), str(connection.id)],
            )
            db.add(finding)
            db.flush()
            publish(
                db,
                user,
                "finding.created",
                finding.id,
                simulation=finding.simulation,
                simulation_label=finding.simulation_label,
            )
        node = "finding:" + str(finding.id)
        network.add_node(
            node,
            type="Finding",
            simulation=finding.simulation,
            simulation_label=finding.simulation_label,
        )
        for identifier in finding.observation_ids:
            network.add_node(
                identifier,
                type="Observation",
                simulation=finding.simulation,
                simulation_label=finding.simulation_label,
            )
            network.add_edge(
                node,
                identifier,
                relationship="Finding -> Observation",
                simulation=finding.simulation,
                simulation_label=finding.simulation_label,
            )
    return {
        "nodes": [{"id": key, **value} for key, value in network.nodes(data=True)],
        "edges": [
            {"source": start, "target": end, **value}
            for start, end, value in network.edges(data=True)
        ],
    }
