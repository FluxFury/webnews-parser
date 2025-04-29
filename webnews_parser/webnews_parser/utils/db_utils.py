from flux_orm import Competition, MatchStatus
from flux_orm.database import new_session, new_sync_session
from flux_orm.models.models import Match, Sport
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import class_mapper, RelationshipProperty


def update_object(obj, data: dict):
    """
    Update an object's attributes with values from a dictionary, excluding relationships.

    This function iterates over the provided data dictionary and sets the corresponding attributes
    on the given object. It skips any keys that correspond to relationship properties in the SQLAlchemy model.

    Args:
        obj (Any): The SQLAlchemy ORM object to update.
        data (dict): A dictionary containing attribute names and their new values.

    """
    mapper = class_mapper(obj.__class__)
    relationship_keys = {prop.key for prop in mapper.iterate_properties if isinstance(prop, RelationshipProperty)}

    for key, value in data.items():
        if key in relationship_keys:
            continue

        setattr(obj, key, value)


async def poll_latest_match() -> Match:
    """Get the most recently added match from the database asynchronously."""
    async with new_session() as session:
        stmt = (
            select(Match)
            .order_by(desc(Match.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


def sync_poll_latest_match() -> Match:
    """Get the most recently added match from the database synchronously."""
    with new_sync_session() as session:
        stmt = (
            select(Match)
            .order_by(desc(Match.planned_start_datetime))
            .limit(1)
        )
        result = session.execute(stmt)
        return result.scalar_one_or_none()
    
async def poll_sport_by_name(name: str) -> Sport:
    """Get a sport by its name."""
    async with new_session() as session:
        stmt = select(Sport).filter_by(name=name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


def poll_cs2_matches() -> list[Match]:
    """Get all CS2 matches that have an associated competition."""
    with new_sync_session() as session:
        stmt = (
            select(Match)
            .join(Match.sport)
            .join(Match.match_status)
            .filter(
                Sport.name == "CS2",
                MatchStatus.name.in_(["scheduled", "live"])
            )
            .distinct()
        )
        result = session.execute(stmt)
        return result.scalars().all()


def get_matches_with_empty_tournaments() -> list[Match]:
    """Get matches with empty tournaments."""
    with new_sync_session() as session:
        stmt = select(Match).filter_by(competition_id = None)
        matches = session.execute(stmt)
        return matches.scalars().all()
            