from decksite.view import View

# pylint: disable=no-self-use
class Archetype(View):
    def __init__(self, archetype, archetypes, matchups):
        self.archetype = next(a for a in archetypes if a.id == archetype.id)
        self.archetype.decks = archetype.decks
        # Load the deck information from archetype into skinny archetype loaded by load_archetypes_deckless_for with tree information.
        self.archetypes = archetypes
        self.decks = self.archetype.decks
        self.roots = [a for a in self.archetypes if a.is_root]

    def __getattr__(self, attr):
        return getattr(self.archetype, attr)

    def subtitle(self):
        return self.archetype.name
