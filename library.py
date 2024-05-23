from trytond.model import ModelSQL, ModelView, fields


__all__ = [
    'Genre',
    'Editor',
    'EditorGenreRelation',
    'Author',
    'Book',
    'Exemplary',
    ]


class Genre(ModelSQL, ModelView):
    'Genre'
    __name__ = 'library.genre'

    name = fields.Char('Name', required=True)

class Editor(ModelSQL, ModelView):
    'Editor'
    __name__ = 'library.editor'

    name = fields.Char('Name', required=True)
    genres = fields.Many2Many('library.editor-library.genre', 'editor',
        'genre', 'Genres')
    creation_date = fields.Date('Creation Date')


class EditorGenreRelation(ModelSQL):
    'Editor - Genre relation'
    __name__ = 'library.editor-library.genre'

    editor = fields.Many2One('library.editor', 'Editor', required=True,
        ondelete='CASCADE')
    genre = fields.Many2One('library.genre', 'Genre', required=True,
        ondelete='RESTRICT')


class Author(ModelSQL, ModelView):
    'Author'
    __name__ = 'library.author'

    books = fields.One2Many('library.book', 'author', 'Books')
    name = fields.Char('Name', required=True)
    birth_date = fields.Date('Birth Date')
    death_date = fields.Date('Death Date')
    gender = fields.Selection([('man', 'Man'), ('woman', 'Woman')], 'Gender')
    book_count = fields.Integer('Book Count', help='The number of books an author wrote')


class Book(ModelSQL, ModelView):
    'Book'
    __name__ = 'library.book'

    title = fields.Char('Title', required=True)
    author = fields.Many2One('library.author', 'Author', required=True,
        ondelete='CASCADE')
    exemplaries = fields.One2Many('library.book.exemplary', 'book',
        'Exemplaries')
    genre = fields.Many2One('library.genre', 'Genre', ondelete='RESTRICT',
        required=False)
    editor = fields.Many2One('library.editor', 'Editor', ondelete='RESTRICT',
        required=True)
    summary = fields.Text('Summary')
    short_description = fields.Char('my_string', help='A one-line description of a book')
    page_count = fields.Integer('Page Count',
                                help='The number of page in the book')
    edition_stopped = fields.Boolean('Edition stopped',
                                     help='If True, this book will not be printed again in this version')
    cover = fields.Binary('Cover')


class Exemplary(ModelSQL, ModelView):
    'Exemplary'
    __name__ = 'library.book.exemplary'
    id = fields.Integer("Identifier", required=True, readonly=True)
    book = fields.Many2One('library.book', 'Book', ondelete='CASCADE',
        required=True)
    acquisition_price = fields.Numeric('Acquisition Price', digits=(16, 2))
    acquisition_date = fields.Date('Acquisition Date')

