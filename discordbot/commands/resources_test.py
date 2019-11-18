import re
from typing import Dict, List
from urllib.parse import urlparse

from discordbot.commands.resources import message, site_resources

def test_message():
    resources = {
        'http://localhost/test/': 'Test Page'
    }
    assert message(resources) == 'Test Page: <http://localhost/test/>'
    resources = {}
    assert re.search('/resources/>$', message(resources))

def test_site_resources():
    assert site_resources('gibberish') == {}
    assert paths(site_resources('card Channel')) == ['/cards/channel/']
    assert paths(site_resources('cards Channel')) == ['/cards/channel/']
    assert paths(site_resources('archetype Red Deck Wins')) == ['/archetypes/red-deck-wins/']
    assert paths(site_resources('archetypes Red Deck Wins')) == ['/archetypes/red-deck-wins/']
    assert paths(site_resources('person bakert99')) == ['/people/bakert99/']
    assert paths(site_resources('people bakert99')) == ['/people/bakert99/']
    assert paths(site_resources('s9 card Channel')) == ['/seasons/9/cards/channel/']
    assert paths(site_resources('all cards Channel')) == ['/seasons/all/cards/channel/']
    assert paths(site_resources('sall archetype Red Deck Wins')) == ['/seasons/all/archetypes/red-deck-wins/']
    assert paths(site_resources('10 archetypes Red Deck Wins')) == ['/seasons/10/archetypes/red-deck-wins/']
    assert paths(site_resources('all person bakert99')) == ['/seasons/all/people/bakert99/']
    assert paths(site_resources('1 people bakert99')) == ['/seasons/1/people/bakert99/']

    print(site_resources('Necropotence'))
    assert paths(site_resources('Necropotence')) == ['/seasons/all/cards/Necropotence/']
    # BAKERT get a currently not-legal card for this test don't hardcode channel
    # BAKERT get a currently legal card for this test don't hardcode channel
    assert urlparse(site_resources('Channel')).path == '/cards/Channel/'
    assert urlparse(site_resources('bakert99')).path == '/people/bakert99/'
    assert urlparse(site_resources('bakert99 all')).path == '/seasons/all/people/bakert99/'
    assert urlparse(site_resources('all bakert99')).path == '/seasons/all/people/bakert99/'
    assert urlparse(site_resources('person bakert99')).path == '/people/bakert99/'
    assert urlparse(site_resources('people bakert99 all')).path == '/seasons/all/people/bakert99/'
    # BAKERT need fuzzy matching on archetype names to make this work
    assert urlparse(site_resources('red deck wnis')).path == '/archetypes/red-deck-wins/'
    assert urlparse(site_resources('red dcek wins 8')).path == '/seasons/8/archetypes/red-deck-wins/'
    assert urlparse(site_resources('cards nonsense')).path == '/cards/'
    assert urlparse(site_resources('9 archetype nonsense')).path == '/seasons/9/archetypes/'

def paths(resources: Dict[str, str]) -> List[str]:
    return [urlparse(s).path for s in resources.keys()]
