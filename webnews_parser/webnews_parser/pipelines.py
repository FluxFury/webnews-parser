"""Pipeline classes for processing scraped items."""

from datetime import datetime
from typing import Any

from flux_orm.database import new_session
from flux_orm.models.models import (
    Competition,
    Match,
    MatchStatus,
    RawNews,
    Sport,
    Team,
    TeamMember,
)
from flux_orm.models.enums import PipelineStatus
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
import scrapy

from .utils.db_utils import poll_sport_by_name, update_object
from flux_orm.models.utils import utcnow_naive

async def upsert_match(item: dict[str, Any], session: AsyncSession) -> Match:
    """Create or update a match."""
    # Create a copy of the item and remove status since it's not a Match field
    match_data = item.copy()
    match_data.pop("match_status", None)
    
    sport = await poll_sport_by_name("CS2")
    stmt = (
        insert(Match).values(**match_data, sport_id=sport.sport_id).on_conflict_do_update(
            index_elements=["external_id"],
            set_={
                "match_name": match_data["match_name"],
                "planned_start_datetime": match_data["planned_start_datetime"]
            }
        )
    )
    await session.execute(stmt)

    select_stmt = select(Match).options(joinedload(Match.match_status)).filter_by(external_id=item["external_id"])
    result = await session.execute(select_stmt)

    return result.scalar_one()


async def get_or_create_team(
    session: AsyncSession,
    team_data: dict[str, Any],
    team_name: str,
    pretty_team_name: str,
    team_url: str,
) -> Team:
    """Get existing team or create a new one."""
    stmt = select(Team).filter_by(name=team_name)
    result = await session.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        team = Team()
        team.name = team_name
        team.pretty_name = pretty_team_name
        team.team_url = team_url
        session.add(team)

    if team_data:
        update_object(team, team_data)

    return team


class CSCreateLiveScheduledMatchesPipeline:
    """Pipeline for creating new matches with empty tournament placeholders."""

    async def process_item(self, item: dict[str, Any], spider: scrapy.Spider) -> dict[str, Any]:
        """
        Process match items and create new database entries.

        Args:
            item: The scraped match data.
            spider: The spider instance.

        Returns:
            dict: The processed item.

        """
        async with new_session(expire_on_commit=True, autoflush=False) as session:
            match = await upsert_match(item, session)

            if not match.match_status:
                match_status = MatchStatus()
                match_status.name = item["match_status"]
                match.match_status = match_status
            else:
                match.match_status.name = item["match_status"]

            try:
                await session.commit()
            except IntegrityError as e:
                spider.logger.error(f"IntegrityError: {e}")
                await session.rollback()
            except Exception as e:
                spider.logger.error(f"Error: {e}")
                await session.rollback()
        return item


class CSUpdateLiveScheduledMatchesPipeline:
    """Pipeline for updating match information and status."""

    async def process_item(self, item: dict[str, Any], spider: scrapy.Spider) -> dict[str, Any]:
        """Update match details and status."""
        async with new_session(expire_on_commit=True, autoflush=False) as session:
            stmt = (
                select(Match)
                .options(joinedload(Match.match_status), joinedload(Match.match_teams))
                .filter_by(match_id=item["match_id"])
            )
            result = await session.execute(stmt)
            match = result.unique().scalar_one()

            # Update match data
            update_object(
                match,
                {
                    "pretty_match_name": item.get("pretty_match_name"),
                    "tournament_url": item.get("tournament_url"),
                    "match_streams": item.get("match_streams"),
                },
            )

            item_team_1 = item.get("pretty_team1_name")
            item_team_2 = item.get("pretty_team2_name")
            if item_team_1 and item_team_1 != "TBD":
                team1 = await get_or_create_team(
                    session,
                    item,
                    item.get("team1_name"),
                    item_team_1,
                    item.get("team1_url"),
                )
                if team1 not in match.match_teams:
                    match.match_teams.append(team1)

            if item_team_2 and item_team_2 != "TBD":
                team2 = await get_or_create_team(
                    session,
                    item,
                    item.get("team2_name"),
                    item_team_2,
                    item.get("team2_url"),
                )
                if team2 not in match.match_teams:
                    match.match_teams.append(team2)

            # Update match status
            match_status_data = {
                "name": item["match_status"],
                "status": {
                    "team1_score": item["team1_score"],
                    "team2_score": item["team2_score"],
                    "match_format": item["match_format"],
                },
            }

            if not match.match_status:
                match_status = MatchStatus()
                update_object(match_status, match_status_data)
                match.match_status = match_status
            else:
                update_object(match.match_status, match_status_data)

            try:
                await session.commit()
            except IntegrityError as e:
                spider.logger.error(f"IntegrityError: {e}")
                await session.rollback()
            except Exception as e:
                spider.logger.error(f"Error: {e}")
                await session.rollback()
        return item


class CSUpdateTournamentsPipeline:
    """Pipeline for updating tournament information for existing matches."""

    async def process_item(self, item: dict[str, Any], spider: scrapy.Spider) -> dict[str, Any]:
        """
        Update tournament information for a match.

        Args:
            item: The scraped tournament data.
            spider: The spider instance.

        Returns:
            dict: The processed item.

        """
        async with new_session() as session:
            sport = await poll_sport_by_name("CS2")
            stmt = (
                select(Match)
                .options(joinedload(Match.match_teams).joinedload(Team.competitions))
                .filter_by(match_id=item.get("match_id"))
            )
            result = await session.execute(stmt)
            match = result.unique().scalar_one()
            if match.competition:
                update_object(
                    match.competition,
                    {
                        "name": item.get("tournament_name"),
                        "description": item.get("tournament_description"),
                        "prize_pool": item.get("tournament_prize_pool"),
                        "location": item.get("tournament_location"),
                        "start_date": item.get("tournament_start_date"),
                        "image_url": item.get("tournament_logo_link"),
                    },
                )
            else:
                select_stmt = select(Competition).filter_by(
                    name=item.get("tournament_name")
                )
                result = await session.execute(select_stmt)
                competition = result.scalar_one_or_none()
                if not competition:
                    competition = Competition()
                update_object(
                    competition,
                    {
                        "name": item.get("tournament_name"),
                        "description": item.get("tournament_description"),
                        "prize_pool": item.get("tournament_prize_pool"),
                        "location": item.get("tournament_location"),
                        "start_date": item.get("tournament_start_date"),
                        "image_url": item.get("tournament_logo_link"),
                    },
                )
                match.competition = competition
                competition.sport = sport

            for team in match.match_teams:
                if competition not in team.competitions:
                    team.competitions.append(competition)

            await session.commit()
        return item


class CSNewsPostgresPipeline:
    """Pipeline for processing and storing news articles."""

    async def process_item(self, item: dict[str, Any], spider: scrapy.Spider) -> dict[str, Any]:
        """
        Store news articles in the database.

        Args:
            item: The scraped news data.
            spider: The spider instance.

        Returns:
            dict: The processed item.
            
        """
        async with new_session() as session:
            sport = await poll_sport_by_name("CS2")
            news = RawNews(
                url=item.get("url"),
                header=item.get("header"),
                text=item.get("text"),
                news_creation_time=item.get("news_creation_time"),
                sport_id=sport.sport_id,
                pipeline_status=PipelineStatus.NEW,
                pipeline_update_time=utcnow_naive(),
            )
            session.add(news)
            try:
                await session.commit()
            except IntegrityError as e:
                spider.logger.error(f"IntegrityError: {e}")
                await session.rollback()
            except Exception as e:
                spider.logger.error(f"Error: {e}")
                await session.rollback()
        return item


class CSTeamsPostgresPipeline:
    """Pipeline for processing and storing team information."""

    async def process_item(self, item: dict[str, Any], spider: scrapy.Spider) -> dict[str, Any]:
        """
        Store team information in the database.

        Args:
            item: The scraped team data.
            spider: The spider instance.

        Returns:
            dict: The processed item.
        """
        await self._commit_team_data(item)
        return item

    @staticmethod
    async def _commit_team_data(item: dict[str, Any]) -> None:
        """Store or update team data."""
        async with new_session(expire_on_commit=True, autoflush=False) as session:
            team_page_link = item.get("team_page_link")
            team = await session.scalar(select(Team).options(joinedload(Team.members)).filter_by(team_url=team_page_link))
            if not team:
                team = Team()
                update_object(
                    team,
                    {
                        "name": item.get("team_name"),
                        "pretty_name": item.get("team_pretty_name"),
                        "regalia": item.get("regalia"),
                        "stats": item.get("stats"),
                        "image_url": item.get("team_logo_link"),
                        "team_url": team_page_link,
                    },
                )
                session.add(team)
            else:
                update_object(
                    team,
                    {
                        "pretty_name": item.get("team_pretty_name"),
                        "regalia": item.get("regalia"),
                        "stats": item.get("stats"),
                        "team_url": team_page_link,
                    },
                )

            await CSTeamsPostgresPipeline._update_team_members(team, item, session)
            await session.commit()

    @staticmethod
    async def _update_team_members(team: Team, item: dict[str, Any], session: AsyncSession) -> None:
        """Update team members information."""
        players_data = item.get("players", {})

        for nickname, player_data in players_data.items():
            team_member_url = item.get("players").get(nickname)[1]
            member = await session.scalar(
                select(TeamMember).filter_by(team_member_url=team_member_url)
            )

            if not member:
                member = TeamMember()
                update_object(
                    member,
                    {
                        "nickname": nickname,
                        "country": player_data[2],  # Index 2 contains country
                        "stats": {"status": player_data[0]},  # Index 0 contains status
                        "image_url": player_data[3],  # Index 3 contains image URL
                        "team_member_url": team_member_url,
                    }
                )
            else:
                member.stats["status"] = player_data[0]
                member.image_url = player_data[3]
            if not member in team.members:
                team.members.append(member)


class CSPlayersPipeline:
    """Pipeline for processing and storing player information."""

    async def process_item(self, item: dict[str, Any], spider: scrapy.Spider) -> dict[str, Any]:
        """
        Store player information in the database.

        Args:
            item: The scraped player data.
            spider: The spider instance.

        Returns:
            dict: The processed item.

        """
        async with new_session() as session:
            # Check if player exists by nickname
            stmt = select(TeamMember).filter_by(team_member_url=item.get("team_member_url"))
            print(item.get("team_member_url"))
            result = await session.execute(stmt)
            player = result.scalar_one_or_none()

            if not player:
                player = TeamMember()

            

            update_object(
                player,
                {
                    "nickname": item.get("player_nickname"),
                    "name": item.get("player_name"),
                    "age": int(item.get("player_age")) if item.get("player_age") is not None else None,
                    "country": item.get("player_country"),
                    "team_member_url": item.get("team_member_url"),
                    "image_url": item.get("image_url"),
                },
            )
            
            if not player.stats:
                player.stats = {}
                
            player.stats.update({
                "games_last_year": item.get("player_played_games_last_year"),
                "games_overall": item.get("player_played_games_overall"),
                "status": item.get("player_status"),
            })


            team_stmt = select(Team).options(joinedload(Team.members)).filter_by(team_url=item.get("team_page_link"))
            result = await session.execute(team_stmt)
            team = result.unique().scalar_one_or_none()
            
            if team and player not in team.members:
                team.members.append(player)

            if not player in session:
                session.add(player)
            
            try:
                await session.commit()
            except IntegrityError as e:
                spider.logger.error(f"IntegrityError: {e}")
                await session.rollback()
            except Exception as e:
                spider.logger.error(f"Error: {e}")
                await session.rollback()
        return item


class CSPastMatchesPostgresPipeline:
    """Pipeline for processing and storing past matches information."""

    async def process_item(self, item: dict[str, Any], spider: scrapy.Spider) -> dict[str, Any]:
        """
        Store past match information in the database.

        Args:
            item: The scraped match data.
            spider: The spider instance.

        Returns:
            dict: The processed item.

        """
        async with new_session() as session:

            sport = await poll_sport_by_name("CS2")

            stmt = select(Match).options(joinedload(Match.match_status)).filter_by(external_id=item.get("external_id"))
            result = await session.execute(stmt)
            match = result.scalar_one_or_none()

            if not match:
                match = Match()
                match.sport = sport
                match.match_name = item.get("match_name")
                match.external_id = item.get("external_id")

                match_status = MatchStatus()
                match_status.name = "finished"
                match_status.status = {
                    "team1_score": item.get("team1_score"),
                    "team2_score": item.get("team2_score"),
                }
                match.match_status = match_status
                
                # Set match dates - date is already parsed by the loader
                match.planned_start_datetime = item.get("date")

                session.add(match)
            else:
                match.match_status.name = "finished"
                match.match_status.status = {
                    "name": "finished",
                    "team1_score": item.get("team1_score"),
                    "team2_score": item.get("team2_score"),
                }

            try:
                await session.commit()
            except IntegrityError as e:
                spider.logger.error(f"IntegrityError: {e}")
                await session.rollback()
            except Exception as e:
                spider.logger.error(f"Error: {e}")
                await session.rollback()
        return item
