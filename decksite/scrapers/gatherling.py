import datetime
from typing import Any, Dict, List, Optional


from decksite.data import archetype, competition, deck, match, person
from decksite.database import db
from magic import decklist
from shared import dtutil, fetch_tools, logger
from shared.pd_exception import InvalidDataException

WINNER = '1st'
SECOND = '2nd'
TOP_4 = 't4'
TOP_8 = 't8'

ALIASES: Dict[str, str] = {}
PLAYERDATA: Dict[str, str] = {}


def scrape() -> None:
    events = fetch_tools.fetch_json('https://gatherling.com/api.php?action=recent_events')
    for (name, data) in events.items():
        parse_tournament(name, data)

def parse_tournament(name: str, data: dict) -> int:
    PLAYERDATA.update(data['players'])
    dt = get_dt(data['start'], dtutil.GATHERLING_TZ)
    competition_series = data['series']
    url = 'https://gatherling.com/eventreport.php?event=' + name
    top_n = find_top_n(data['finalrounds'])
    db().begin('tournament')
    competition_id = competition.get_or_insert_competition(dt, dt, name, competition_series, url, top_n)
    ranks = rankings(data)
    medals = medal_winners(data)
    final = finishes(medals, ranks)
    n = add_decks(dt, competition_id, final, data)
    db().commit('tournament')
    return n

def get_dt(start: str, timezone: Any) -> datetime.datetime:
    return dtutil.parse(start, '%d %B %Y %H:%M', timezone)

def find_top_n(finalrounds: int) -> competition.Top:
    if finalrounds == 0:
        return competition.Top.NONE
    return competition.Top(pow(2, finalrounds))

def add_decks(dt: datetime.datetime, competition_id: int, final: Dict[str, int], data: dict) -> int:
    decks_added = 0
    ds: List[deck.Deck] = []
    allds: List[deck.Deck] = []
    for dj in data['decks']:
        d = tournament_deck(dj, competition_id, dt, final)
        if d is not None:
            if d.get('id') is None or not match.load_matches_by_deck(d):
                decks_added += 1
                d['gatherling_username'] = dj['playername']
                ds.append(d)
            allds.append(d)
    matches = parse_matches(data, allds)
    add_ids(matches, ds)
    insert_matches_without_dupes(dt, matches)
    guess_archetypes(ds)
    return decks_added

def guess_archetypes(ds: List[deck.Deck]) -> None:
    deck.calculate_similar_decks(ds)
    for d in ds:
        if d.similar_decks and d.similar_decks[0].archetype_id is not None:
            archetype.assign(d.id, d.similar_decks[0].archetype_id, None, False)

def rankings(data: dict) -> List[str]:
    standings = []
    for s in data['standings']:
        standings.append(s['player'])
    return standings

def medal_winners(data: dict) -> Dict[str, int]:
    winners = {}
    for f in data['finalists']:
        mtgo_username = aliased(f['player'])
        medal = f['medal']
        if medal == WINNER:
            winners[mtgo_username] = 1
        elif medal == SECOND:
            winners[mtgo_username] = 2
        elif medal == TOP_4:
            winners[mtgo_username] = 3
        elif medal == TOP_8:
            winners[mtgo_username] = 5
        else:
            raise InvalidDataException(f'Unknown medal `{medal}`')
    return winners

def finishes(winners: Dict[str, int], ranks: List[str]) -> Dict[str, int]:
    final = winners.copy()
    r = len(final)
    for p in ranks:
        if p not in final.keys():
            r += 1
            final[p] = r
    return final

def tournament_deck(deck_json: dict, competition_id: int, date: datetime.datetime, final: Dict[str, int]) -> Optional[deck.Deck]:
    d: deck.RawDeckDescription = {'source': 'Gatherling', 'competition_id': competition_id, 'created_date': dtutil.dt2ts(date)}
    player = deck_json['playername']
    username = aliased(player)
    d['mtgo_username'] = username
    d['finish'] = final.get(username)
    if d['finish'] is None:
        raise InvalidDataException(f'{username} has no finish')

    gatherling_id = deck_json["id"]
    d['url'] = gatherling_url(f'deck.php?mode=view&id={gatherling_id}')
    d['name'] = deck_json['name']
    d['archetype'] = deck_json['archetype']
    d['identifier'] = gatherling_id
    existing = deck.get_deck_id(d['source'], d['identifier'])
    if existing is not None:
        return deck.load_deck(existing)
    # This probably should be using the JSON too, but one thing at a time
    dlist = decklist.parse(fetch_tools.post(gatherling_url('deckdl.php'), {'id': gatherling_id}))
    d['cards'] = dlist
    if len(dlist['maindeck']) + len(dlist['sideboard']) == 0:
        logger.warning('Rejecting deck with id {id} because it has no cards.'.format(id=gatherling_id))
        return None
    return deck.add_deck(d)

MatchListType = List[Dict[str, Any]]

def parse_matches(tournament: dict, ds: List[deck.Deck]) -> MatchListType:
    matches = []

    decks = {}
    for d in ds:
        decks[d['gatherling_username']] = d

    for m in tournament['matches']:
        deck_a = decks[m['playera']]
        deck_b = decks[m['playerb']]

        roundnum = m['round']
        elimination = 0
        if m['timing'] == 2:
            roundnum = roundnum + tournament['mainrounds']
            ... # TODO: Need to cross-reference tournament[finalrounds] with m[round] to get Top X

        matches.append({
            'round': roundnum,
            'elimination': elimination,
            'left_games': m['playera_wins'],
            'left_identifier': deck_a.identifier,
            'right_games': m['playerb_wins'],
            'right_identifier': deck_b.identifier
        })
    return matches

def insert_matches_without_dupes(dt: datetime.datetime, matches: MatchListType) -> None:
    db().begin('insert_matches_without_dupes')
    inserted: Dict[str, bool] = {}
    for m in matches:
        reverse_key = str(m['round']) + '|' + str(m['right_id']) + '|' + str(m['left_id'])
        if inserted.get(reverse_key):
            continue
        match.insert_match(dt, m['left_id'], m['left_games'], m['right_id'], m['right_games'], m['round'], m['elimination'])
        key = str(m['round']) + '|' + str(m['left_id']) + '|' + str(m['right_id'])
        inserted[key] = True
    db().commit('insert_matches_without_dupes')

def add_ids(matches: MatchListType, ds: List[deck.Deck]) -> None:
    decks_by_identifier = {d.identifier: d for d in ds}
    def lookup(gatherling_id: int) -> deck.Deck:
        try:
            return decks_by_identifier[gatherling_id]
        except KeyError as c:
            raise InvalidDataException("Unable to find deck with gatherling id '{0}'".format(gatherling_id)) from c
    for m in matches:
        m['left_id'] = lookup(m['left_identifier']).id
        m['right_id'] = lookup(m['right_identifier']).id if m['right_identifier'] else None

def gatherling_url(href: str) -> str:
    if href.startswith('http'):
        return href
    return 'https://gatherling.com/{href}'.format(href=href)

def aliased(username: str) -> str:
    if not ALIASES:
        load_aliases()
    return ALIASES.get(username, username)

def load_aliases() -> None:
    ALIASES['dummyplaceholder'] = '' # To prevent doing the load on every lookup if there are no aliases in the db.
    for entry in person.load_aliases():
        ALIASES[entry.alias] = entry.mtgo_username
