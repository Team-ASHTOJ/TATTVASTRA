"""Deadline sweeper; PostgreSQL jobs remain the queue of record."""

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from jocky_control_plane.config import Settings
from jocky_control_plane.hunts import transition
from jocky_control_plane.models import Endpoint, Job, Organization, Role, State, User
from jocky_control_plane.security import aware, publish


def sweep(factory: sessionmaker[Session], settings: Settings) -> None:
    with factory.begin() as db:
        for organization in db.scalars(select(Organization).with_for_update(skip_locked=True)):
            user = db.scalar(
                select(User)
                .where(
                    User.organization_id == organization.id,
                    User.role == Role.ADMIN,
                    User.disabled.is_(False),
                )
                .limit(1)
            )
            if user is None:
                continue
            for endpoint in db.scalars(
                select(Endpoint).where(
                    Endpoint.organization_id == organization.id, Endpoint.status == State.ONLINE
                )
            ):
                if endpoint.last_seen is None or aware(endpoint.last_seen) < datetime.now(
                    UTC
                ) - timedelta(seconds=90):
                    endpoint.status = State.OFFLINE
                    publish(
                        db,
                        user,
                        "agent.state",
                        endpoint.id,
                        {"state": "OFFLINE"},
                        simulation=endpoint.simulation,
                        simulation_label=endpoint.simulation_label,
                    )
            jobs = db.scalars(
                select(Job)
                .where(
                    Job.organization_id == organization.id,
                    Job.status.in_(
                        [State.QUEUED, State.DISPATCHED, State.RUNNING, State.CANCEL_REQUESTED]
                    ),
                    Job.deadline <= datetime.now(UTC),
                )
                .with_for_update()
            ).all()
            for job in jobs:
                transition(db, job, State.FAILED, user, settings, "Job deadline exceeded")


def run(factory: sessionmaker[Session], settings: Settings) -> None:
    while True:
        sweep(factory, settings)
        time.sleep(1)
