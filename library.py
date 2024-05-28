from trytond.model import ModelSQL, ModelView, fields
from datetime import datetime, timedelta
from sql.aggregate import Count, Max
from sql.conditionals import Coalesce
from trytond.pool import Pool
from trytond.transaction import Transaction


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
    creation_date = fields.Date('Creation date',
                                help='The date at which the editor was created')
    genres = fields.Many2Many('library.editor-library.genre', 'editor',
                              'genre', 'Genres')
    published_book_count = fields.Function(
        fields.Integer("Published Book Count",
                       help="Number of Books an editor published"),
        "getter_published_book_count")
    published_book_1year = fields.Function(
        fields.Integer("Published Book One Year",
                       help="List of books an editor published in the past year"),
        "getter_published_book_1year")

    @classmethod
    def getter_published_book_count(cls, editors, name):
        result = {x.id: 0 for x in editors}
        Book = Pool().get('library.book')
        book = Book.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*book.select(book.editor, Count(book.id),
                                    where=book.editor.in_([x.id for x in editors]),
                                    group_by=[book.editor]))
        for book_id, count in cursor.fetchall():
            result[book_id] = count
        return result


    @classmethod
    def getter_published_book_1year(cls, editors, name):
        result = {x.id: 0 for x in editors}
        Book = Pool().get('library.book')
        book = Book.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*book.select(book.editor, Count(book.id),
                                    where=(book.editor.in_([x.id for x in editors])
                                            and book.publication_date >= (datetime.now() - timedelta(days=365))),
                                    group_by=[book.editor]))
        for book_id, count in cursor.fetchall():
            result[book_id] = count
        return result

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
    birth_date = fields.Date('Birth date')
    death_date = fields.Date('Death date')
    gender = fields.Selection([('man', 'Man'), ('woman', 'Woman')], 'Gender')
    age = fields.Function(
        fields.Integer('Age'),
        'getter_age', searcher='searcher_age')
    number_of_books = fields.Function(
        fields.Integer('Number of books'),
        'getter_number_of_books')
    genres = fields.Function(
        fields.One2Many('library.genre', None, 'Genres'),
        'getter_genres')
    most_recent_book = fields.Function(
        fields.Many2One('library.book',"Most recent Book"),
        "getter_most_recent_book")
    def getter_age(self, name):
        if not self.birth_date:
            return None
        end_date = self.death_date or datetime.today()
        age = end_date.year - self.birth_date.year
        if (end_date.month, end_date.day) < (
            self.birth_date.month, self.birth_date.day):
            age -= 1
        return age

    @classmethod
    def getter_number_of_books(cls, authors, name):
        result = {x.id: 0 for x in authors}
        Book = Pool().get('library.book')
        book = Book.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*book.select(book.author, Count(book.id),
                                    where=book.author.in_([x.id for x in authors]),
                                    group_by=[book.author]))
        for author_id, count in cursor.fetchall():
            result[author_id] = count
        return result

    @classmethod
    def searcher_age(cls, age, name):
        return age

    @classmethod
    def getter_genres(cls, authors, name):
        result = {x.id: [] for x in authors}
        Book = Pool().get('library.book')
        book = Book.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*book.select(book.author, book.genre,
                                    where=book.author.in_([x.id for x in authors]),
                                    group_by=[book.author, book.genre]))
        for book_id, book_genre in cursor.fetchall():
            result[book_id].append(book_genre)
        return result
    @classmethod
    def getter_most_recent_book(cls, authors, name):
        result = {x.id: [] for x in authors}
        Books = Pool().get('library.book')
        book = Books.__table__()
        book2 = Books.__table__()
        cursor = Transaction().connection.cursor()
        '''
        #### ne marche pas :( ####

        #import web_pdb;web_pdb.set_trace()
        sub_query = book2.select(book2.author, Max(book2.publication_date).as_('max_date'),
                                #where=(book.author == book2.author)
                                where=(book2.author.in_([x.id for x in authors])),
                                group_by=[book2.author])


        cursor.execute(*book.join(sub_query, condition=(book.author == sub_query.author))
                            .select(book.author, book.title,
                            where=(book.author.in_([x.id for x in authors])
                                & book.publication_date == Max(sub_query.max_date)),
                            group_by=[book.author, book.title]))
        '''

        for book_id, book_title in cursor.fetchall():
                result[book_id] = book_title
        return result

class Book(ModelSQL, ModelView):
    'Book'
    __name__ = 'library.book'
    _rec_name = 'title'

    author = fields.Many2One('library.author', 'Author', required=True,
                             ondelete='CASCADE')
    exemplaries = fields.One2Many('library.book.exemplary', 'book',
                                  'Exemplaries')
    title = fields.Char('Title', required=True)
    genre = fields.Many2One('library.genre', 'Genre', ondelete='RESTRICT',
                            required=False)
    editor = fields.Many2One('library.editor', 'Editor', ondelete='RESTRICT',
                             required=True)
    description = fields.Char('Description')
    summary = fields.Text('Summary')
    cover = fields.Binary('Cover')
    publication_date = fields.Date('Publication date')

    latest_acquisition_date = fields.Function(
        fields.Date('Latest Acquisition Date',
                    help="Date of the most recent exemplary"),
        'getter_latest_acquisition_date')

    page_count = fields.Integer('Page Count',
                                help='The number of page in the book')
    exemplary_count = fields.Function(
                        fields.Integer("Exemplary Count",
                                       help="Number of copies of the book"),
                        "getter_exemplary_count")
    edition_stopped = fields.Boolean('Edition stopped',
                                     help='If True, this book will not be printed again in this version')
    isbn = fields.Char("ISBN", size=13,
                       help="The International Standard Book Number of the book")

    @classmethod
    def getter_latest_acquisition_date(cls, books, name):
        result = {x.id: [] for x in books}
        Exemplary = Pool().get('library.book.exemplary')
        exemplary = Exemplary.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(
            *exemplary.select(exemplary.book, Max(exemplary.acquisition_date),
                              where=exemplary.book.in_([x.id for x in books]),
                              group_by=[exemplary.book],
                              order_by=[exemplary.book]))
        for book_exemplary_id, book_exemplary_acquisition_date in cursor.fetchall():
            result[book_exemplary_id] = book_exemplary_acquisition_date
        return result

    @classmethod
    def getter_exemplary_count(cls, books, name):
        result = {x.id: 0 for x in books}
        Exemplary = Pool().get('library.book.exemplary')
        exemplary = Exemplary.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*exemplary.select(exemplary.book, Count(exemplary.id),
                                    where=exemplary.book.in_([x.id for x in books]),
                                    group_by=[exemplary.book]))
        for exemplary_id, count in cursor.fetchall():
            result[exemplary_id] = count
        return result




class Exemplary(ModelSQL, ModelView):
    'Exemplary'
    __name__ = 'library.book.exemplary'
    _rec_name = 'identifier'

    book = fields.Many2One('library.book', 'Book', ondelete='CASCADE',
                           required=True)
    identifier = fields.Char('Identifier', required=True)
    acquisition_date = fields.Date('Acquisition Date')
    acquisition_price = fields.Numeric('Acquisition Price', digits=(16, 2))

    def get_rec_name(self, name):
        return '%s: %s' % (self.book.rec_name, self.identifier)
