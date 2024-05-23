from trytond.pool import Pool

from . import library


def register():
    Pool.register(
        library.Genre,
        library.Editor,
        library.EditorGenreRelation,
        library.Author,
        library.Book,
        library.Exemplary,
        module='library', type_='model')
