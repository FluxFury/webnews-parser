from datetime import datetime

import asyncpg
from flux_orm.models.models import Competition, Match, MatchStatus, RawNews, Sport, Team, TeamLink, TeamMember, \
    PlayerLink
from flux_orm.database import new_session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import lazyload


class CSLSMLiveMatchesAndTournamentPostgresPipeline:
    async def process_item(self, item, spider):
        await self.commit_data(item)
        return item

    @staticmethod
    async def commit_data(mtitem):
        match_start_date_format = "%Y-%m-%d %H:%M:%S"
        tournament_start_date_format = "%Y-%m-%d"
        tournament_start_datetime: [datetime | None] = datetime. \
            strptime(mtitem["tournament_start_date"], tournament_start_date_format) if mtitem[
            "tournament_start_date"] else None
        match_start_datetime: [datetime | None] = datetime.strptime(mtitem["match_begin_time"],
                                                                    match_start_date_format) if mtitem[
            "match_begin_time"] else None
        async with new_session(expire_on_commit=True, autoflush=False) as session:
            stmt = select(Sport).options(lazyload(Sport.competitions)).filter_by(name="CS2")
            cs_sport = await session.execute(stmt)
            cs_sport = cs_sport.scalars().first()
            if mtitem["has_tournament_info"]:
                local_tournament = Competition(sport_id=cs_sport.sport_id,
                                               name=mtitem["tournament_name"],
                                               description=mtitem["tournament_description"],
                                               prize_pool=mtitem["tournament_prize_pool"],
                                               location=mtitem["tournament_location"],
                                               start_date=tournament_start_datetime or None,
                                               image_url=mtitem["tournament_logo_link"])
                local_tournament_dict = {key: value for key, value in local_tournament.__dict__.items() if
                                         not key.startswith("_")}

                stmt = insert(Competition).values(local_tournament_dict)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["name"],  # Specify unique constraint columns
                    set_=local_tournament_dict  # Fields to update if conflict is detected
                )
                await session.execute(stmt)
                stmt = select(Competition).filter_by(name=mtitem["tournament_name"])
                local_tournament_updated = await session.execute(stmt)
                local_tournament_updated = local_tournament_updated.scalars().first()
                session.add(local_tournament_updated)

            stmt = select(Team).filter_by(name=mtitem["team1"])
            first_team = await session.execute(stmt)
            first_team = first_team.scalars().first()
            stmt = select(Team).filter_by(name=mtitem["team2"])
            second_team = await session.execute(stmt)
            second_team = second_team.scalars().first()
            teams_in_match_db = [first_team, second_team]
            teams_in_match_local: list[Team] = [
                Team(name=mtitem[f"team{_}"], image_url=mtitem[f"team{_}_logo_link"])
                for _ in range(1, 3)
            ]

            def update_team(db_team, local_team):
                """
                Updates the team in the database if it exists and isn't TBD, otherwise returns the local team
                """
                if not db_team and local_team.name != "TBD":
                    return local_team
                return db_team

            if not any(teams_in_match_db):
                teams_in_match_db = [team for team in teams_in_match_local if team.name != "TBD"]
            else:
                for i in range(len(teams_in_match_db)):
                    teams_in_match_db[i] = update_team(teams_in_match_db[i], teams_in_match_local[i])

            teams_in_match_db = [team for team in teams_in_match_db if team is not None]
            teams_in_match_updated = teams_in_match_db

            match_name = mtitem["team1"] + " - " + mtitem["team2"]

            local_match = Match(match_name=match_name,
                                pretty_match_name=mtitem["pretty_match_name"],
                                planned_start_datetime=match_start_datetime or None,
                                match_streams=mtitem["match_streams"])
            local_match_dict = {key: value for key, value in local_match.__dict__.items() if not key.startswith("_")}
            stmt = insert(Match).values(local_match_dict)
            stmt = stmt.on_conflict_do_update(
                constraint="match_name_planned_start_datetime_unique",
                set_=local_match_dict
            )
            await session.execute(stmt)
            stmt = select(Match).filter_by(match_name=match_name)
            local_match_updated = await session.execute(stmt)
            local_match_updated = local_match_updated.scalars().first()
            if mtitem["has_tournament_info"]:
                for team in teams_in_match_updated:
                    if team not in local_tournament_updated.teams:
                        local_tournament_updated.teams.append(team)
                local_match_updated.competition = local_tournament_updated
            if not local_match_updated.match_status:
                local_match_status = MatchStatus(name=mtitem["match_status"],
                                                 status={"team1_score": mtitem["team1_score"],
                                                         "team2_score": mtitem["team2_score"],
                                                         "match_format": mtitem["match_format"],
                                                         "tournament_format": mtitem["tournament_format"],
                                                         "tournament_stage": mtitem["tournament_stage"]},
                                                 )
                session.add(local_match_status)
                local_match_updated.match_status = local_match_status
            else:
                local_match_status_updated = local_match_updated.match_status
                local_match_status_updated.name = mtitem["match_status"]
                local_match_status_updated.status = {"team1_score": mtitem["team1_score"],
                                                     "team2_score": mtitem["team2_score"],
                                                     "match_format": mtitem["match_format"],
                                                     "tournament_format": mtitem["tournament_format"],
                                                     "tournament_stage": mtitem["tournament_stage"]}
                local_match_updated.match_status = local_match_status_updated

            local_match_updated.match_teams = teams_in_match_updated
            await session.commit()
        await CSLSMLiveMatchesAndTournamentPostgresPipeline.commit_team_links(mtitem)

    @staticmethod
    async def commit_team_links(mtitem):
        async with new_session() as session:
            stmt = select(TeamLink).filter_by(link=mtitem["team1_page_link"])
            first_team_link = await session.execute(stmt)
            first_team_link = first_team_link.scalars().first()
            stmt = select(TeamLink).filter_by(link=mtitem["team2_page_link"])
            second_team_link = await session.execute(stmt)
            second_team_link = second_team_link.scalars().first()
            if not first_team_link and mtitem["team1_page_link"] != "TBD":
                first_team_link = TeamLink(link=mtitem["team1_page_link"])
                session.add(first_team_link)
            if not second_team_link and mtitem["team2_page_link"] != "TBD":
                second_team_link = TeamLink(link=mtitem["team2_page_link"])
                session.add(second_team_link)
            await session.commit()


class CSNewsPostgresPipeline:
    async def process_item(self, item, spider):
        await self.commit_data(item)
        return item

    @staticmethod
    async def commit_data(nitem):
        async with new_session(expire_on_commit=True, autoflush=False) as session:
            stmt = select(Sport).options(lazyload(Sport.competitions)).filter_by(name="CS2")
            cs_sport = await session.execute(stmt)
            cs_sport = cs_sport.scalars().first()
            try:
                if nitem["unix_time"]:
                    inted_time = int(nitem["unix_time"]) / 1000
                    news_creation_time = datetime.fromtimestamp(inted_time)
                else:
                    news_creation_time = None
            except (ValueError, OSError) as e:
                news_creation_time = None
                print(f"Error processing unix_time {nitem['unix_time']}: {e}")

            local_news = RawNews(header=nitem["header"],
                                 text=nitem["text"],
                                 url=nitem["url"],
                                 news_creation_time=news_creation_time,
                                 sport_id=cs_sport.sport_id)
            session.add(local_news)
            await session.commit()


class CSPastMatchesPostgresPipeline:
    async def process_item(self, item, spider):
        await self.commit_data(item)
        return item

    @staticmethod
    async def commit_data(pmitem):
        async with new_session(expire_on_commit=True, autoflush=False) as session:
            match_status = MatchStatus(name='finished', status={"team1_score": pmitem["team1_score"],
                                                                "team2_score": pmitem["team2_score"]}
                                       )
            match_start_date_format = "%Y-%m-%d %H:%M:%S"
            match_start_datetime: [datetime | None] = datetime.strptime(pmitem["date"], match_start_date_format) if \
                pmitem[
                    "date"] else None
            match_name = pmitem["team1"] + " - " + pmitem["team2"]
            stmt = select(Match).filter_by(match_name=match_name)
            match = await session.execute(stmt)
            match = match.scalars().first()
            local_match = Match(match_name=match_name,
                                planned_start_datetime=match_start_datetime or None,
                                )
            local_match_dict = {key: value for key, value in local_match.__dict__.items() if not key.startswith("_")}
            if not match:
                stmt = insert(Match).values(local_match_dict)
                stmt = stmt.on_conflict_do_update(
                    constraint="match_name_planned_start_datetime_unique",
                    set_=local_match_dict
                )
                await session.execute(stmt)
                stmt = select(Match).filter_by(match_name=match_name)
                local_match = await session.execute(stmt)
                local_match = local_match.scalars().first()
                session.add(local_match)
            else:
                local_match = match
            local_match.match_status = match_status
            await session.commit()


class CSTeamsPostgresPipeline:
    async def process_item(self, item, spider):
        await self.commit_data(item)
        return item

    @staticmethod
    async def fill_player_links(titem):
        async with new_session() as session:
            for player in titem["players"]:
                stmt = select(PlayerLink).filter_by(link=titem["players"][player][1])
                player_link = await session.execute(stmt)
                player_link = player_link.scalars().first()
                if not player_link:
                    player_link = PlayerLink(link=titem["players"][player][1])
                    session.add(player_link)
            await session.commit()

    @staticmethod
    async def commit_data(titem):
        await CSTeamsPostgresPipeline.fill_player_links(titem)
        async with new_session(expire_on_commit=True, autoflush=False) as session:
            stmt = select(Team).filter_by(name=titem["team_name"])
            team = await session.execute(stmt)
            team = team.scalars().first()
            if not team:
                local_team = Team(name=titem["team_name"],
                                  pretty_name=titem["team_pretty_name"],
                                  regalia=titem["regalia"],
                                  stats=titem["stats"],
                                  image_url=titem["team_page_link"])
                for player in titem["players"]:
                    image_url = titem["players"][player][-1]
                    player_country = titem["players"][player][2]
                    player_status = titem["players"][player][0]
                    stmt = select(TeamMember).filter_by(nickname=player, image_url=image_url)
                    member = await session.execute(stmt)
                    member = member.scalars().first()
                    if not member:
                        member = TeamMember(nickname=player,
                                            country=player_country,
                                            stats={"status": player_status},
                                            image_url=image_url)
                        local_team.members.append(member)
                session.add(local_team)
            else:
                local_team = team
                local_team.pretty_name = titem["team_pretty_name"]
                local_team.team_region = titem["team_region"]
                local_team.stats = titem["stats"]
                local_team.regalia = titem["regalia"]
                for player in titem["players"]:
                    player_status = titem["players"][player][0]
                    player_country = titem["players"][player][2]
                    image_url = titem["players"][player][-1]
                    for member in team.members:
                        if member.name == player and member.image_url == image_url:
                            member.stats["status"] = player_status
                            member.image_url = image_url
                            break
                    else:
                        member = TeamMember(nickname=player,
                                            country=player_country,
                                            stats={"status": player_status},
                                            image_url=image_url)
                        local_team.members.append(member)

            await session.commit()


class CSPlayersPostgresPipeline:
    async def process_item(self, item, spider):
        await self.commit_data(item, spider)
        return item

    @staticmethod
    async def commit_data(pitem, spider):
        async with new_session(expire_on_commit=True, autoflush=False) as session:
            stmt = select(Team).filter_by(name=pitem["player_team"])
            team = await session.execute(stmt)
            team = team.scalars().first()
            if not team:
                return
            stmt = select(TeamMember).filter_by(nickname=pitem["player_nickname"], country=pitem["player_country"])
            player = await session.execute(stmt)
            player = player.scalars().first()
            if not player:
                local_player = TeamMember(nickname=pitem["player_nickname"],
                                          name=pitem["player_name"],
                                          country=pitem["player_country"],
                                          age=int(pitem["player_age"]) if pitem["player_age"] != "–" else None,
                                          stats={
                                                 "played_games_last_year": pitem["player_played_games_last_year"],
                                                 "played_games_overall": pitem["player_played_games_overall"],
                                                 })
                team.members.append(local_player)
                session.add(local_player)
            else:
                local_player = player
                local_player.name = pitem["player_name"]
                local_player.age = int(pitem["player_age"]) if pitem["player_age"] != "–" else None
                local_player.stats = {
                    "played_games_last_year": pitem["player_played_games_last_year"],
                    "played_games_overall": pitem["player_played_games_overall"],
                }
            try:
                await session.commit()
            except IntegrityError as e:
                spider.logger.info(f"Constraint violation error while committing player {pitem['player_nickname']} to the database: {e}")
                await session.rollback()