from trytond.pool import Pool
from . import wizard
from . import library


def register():
    Pool.register(
        library.Genre,
        library.Editor,
        library.EditorGenreRelation,
        library.Author,
        library.Book,
        library.Exemplary,
        wizard.CreateExemplariesParameters,
        wizard.FuseBooksChoice,
        wizard.FuseBooksValidation,
        module='library', type_='model')

    Pool.register(
        wizard.CreateExemplaries,
        wizard.FuseBooks,
        module='library', type_='wizard')
