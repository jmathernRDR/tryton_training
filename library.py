import datetime

from sql import Window
from sql.conditionals import Coalesce
from sql.aggregate import Count, Max

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelSQL, ModelView, fields, Unique
from trytond.pyson import Eval, If, Bool

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
    number_of_books = fields.Function(
        fields.Integer('Number of books'),
        'getter_number_of_books')

    @classmethod
    def getter_number_of_books(cls, editors, name):
        result = {x.id: 0 for x in editors}
        Book = Pool().get('library.book')
        book = Book.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*book.select(book.editor, Count(book.id),
                                    where=book.editor.in_([x.id for x in editors]),
                                    group_by=[book.editor]))
        for editor_id, count in cursor.fetchall():
            result[editor_id] = count
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
    birth_date = fields.Date('Birth date',
                             states={'required': Bool(Eval('death_date', 'False'))},
                             depends=['death_date'])
    death_date = fields.Date('Death date',
                             domain=[If(Bool(Eval("death_date", False)),
                                        [("death_date", ">", Eval("birth_date"))],
                                        [])],
                             states={'invisible': ~Eval('birth_date')},
                             depends=['birth_date'])

    gender = fields.Selection([('man', 'Man'), ('woman', 'Woman')], 'Gender')
    age = fields.Function(
        fields.Integer('Age', states={'invisible': ~Eval('death_date')}),
        'getter_age')
    number_of_books = fields.Function(
        fields.Integer('Number of books'),
        'getter_number_of_books')
    genres = fields.Function(
        fields.Many2Many('library.genre', None, None, 'Genres',
                         states={'invisible': ~Eval('genres')}),
        'getter_genres', searcher='searcher_genres')
    latest_book = fields.Function(
        fields.Many2One('library.book', 'Latest Book',
                        states={'invisible': ~Eval('latest_book', False)}),
        'getter_latest_book')

    """Test affichage Lastest_book si le champs publishing_date est également renseigné ...
    >>> Ne marche pas !! :(
    cond2 = (
        (Bool(Eval('latest_book', False)) == False) |
        ((Bool(Eval('latest_book', True)) != True) &
         (Eval('publishing_date', None) == None)))

    latest_book = fields.Function(
        fields.Many2One('library.book', 'Latest Book',
                        states={'invisible': cond2},
                        depends=["publishing_date"]),
        'getter_latest_book')"""

    def getter_age(self, name):
        if not self.birth_date:
            return None
        end_date = self.death_date or datetime.date.today()
        age = end_date.year - self.birth_date.year
        if (end_date.month, end_date.day) < (
            self.birth_date.month, self.birth_date.day):
            age -= 1
        return age

    def getter_genres(self, name):
        genres = set()
        for book in self.books:
            if book.genre:
                genres.add(book.genre.id)
        return list(genres)

    @classmethod
    def getter_latest_book(cls, authors, name):
        result = {x.id: None for x in authors}
        Book = Pool().get('library.book')
        book = Book.__table__()
        sub_book = Book.__table__()
        cursor = Transaction().connection.cursor()

        sub_query = sub_book.select(sub_book.author,
                                    Max(Coalesce(sub_book.publishing_date,
                                                 datetime.date.min),
                                        window=Window([sub_book.author])).as_(
                                        'max_date'),
                                    where=sub_book.author.in_([x.id for x in authors]))

        cursor.execute(*book.join(sub_query,
                                  condition=(book.author == sub_query.author)
                                            & (Coalesce(book.publishing_date,
                                                        datetime.date.min)
                                               == sub_query.max_date)
                                  ).select(book.author, book.id))
        for author_id, book in cursor.fetchall():
            result[author_id] = book
        return result if result else None

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
    def searcher_genres(cls, name, clause):
        return []


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
                             domain=[If(
                                 Bool(Eval('publishing_date', False)),
                                 [('creation_date', '<=', Eval('publishing_date'))],
                                 [])],
                             required=True, depends=['publishing_date'])
    editor_genre = fields.Function(fields.Many2One('library.editor', 'Editor Genre'), "getter_editor_genre")
    isbn = fields.Char('ISBN', size=13,
                       help='The International Standard Book Number')
    publishing_date = fields.Date('Publishing date')
    description = fields.Char('Description')
    summary = fields.Text('Summary')
    cover = fields.Binary('Cover')
    page_count = fields.Integer('Page Count',
                                help='The number of page in the book')
    edition_stopped = fields.Boolean('Edition stopped',
                                     help='If True, this book will not be printed again in this version')
    number_of_exemplaries = fields.Function(
        fields.Integer('Number of exemplaries'),
        'getter_number_of_exemplaries')
    latest_exemplary = fields.Function(
        fields.Many2One('library.book.exemplary', 'Latest exemplary'),
        'getter_latest_exemplary')

    def getter_latest_exemplary(self, name):
        latest = None
        for exemplary in self.exemplaries:
            if not exemplary.acquisition_date:
                continue
            if not latest or (
                latest.acquisition_date < exemplary.acquisition_date):
                latest = exemplary
        return latest.id if latest else None

    @classmethod
    def getter_number_of_exemplaries(cls, books, name):
        result = {x.id: 0 for x in books}
        Exemplary = Pool().get('library.book.exemplary')
        exemplary = Exemplary.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*exemplary.select(exemplary.book, Count(exemplary.id),
                                         where=exemplary.book.in_(
                                             [x.id for x in books]),
                                         group_by=[exemplary.book]))
        for book_id, count in cursor.fetchall():
            result[book_id] = count
        return result

    @classmethod
    def __setup__(cls):
        super().__setup__()
        # Gestion de la table Book sur l'unicité du titre pour un auteur
        t = cls.__table__()
        cls._sql_constraints += [
            ('author_title_uniq', Unique(t, t.author, t.title),
             'The pair author/title must be unique!'),
        ]
        #gestion des messages d'erreur de la méthode de classe validate.
        cls._error_messages.update({
            'invalid_isbn': 'ISBN should only be digits',
            'invalid_isbn_length': 'ISBN should have 13 digits',
            'invalid_isbn_check_digit': 'The check digit has failed',
        })

    @classmethod
    def validate(cls, books):
        for book in books:
            if not book.isbn:
                continue
            try:
                if int(book.isbn) < 0:
                    raise ValueError
            except ValueError as e:
                cls.raise_user_error('invalid_isbn', str(e))

            try:
                if len(book.isbn) != 13:
                    raise ValueError
            except ValueError as e:
                cls.raise_user_error('invalid_isbn_length', str(e))

            check_digit_sum = 0
            for i, num in enumerate(book.isbn):
                if (i + 1) % 2 == 0:
                    check_digit_sum += int(num) * 3
                else:
                    check_digit_sum += int(num)
            if check_digit_sum % 10 != 0:
                cls.raise_user_error('invalid_isbn_check_digit')


class Exemplary(ModelSQL, ModelView):
    'Exemplary'
    __name__ = 'library.book.exemplary'
    _rec_name = 'identifier'

    book = fields.Many2One('library.book', 'Book', ondelete='CASCADE',
                           required=True)
    identifier = fields.Char('Identifier', required=True)
    acquisition_date = fields.Date('Acquisition Date')
    acquisition_price = fields.Numeric('Acquisition Price', digits=(16, 2),
                                       domain=['OR', ('acquisition_price', '=', None),
                                               ('acquisition_price', '>', 0)])

    def get_rec_name(self, name):
        return '%s: %s' % (self.book.rec_name, self.identifier)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('identifier_uniq', Unique(t, t.identifier),
             'The identifier must be unique!'),
        ]


'''Homework
First of all you should practice with pyson and domains. Here are some tests
(some do not have a solution though), assuming "A", "B", and "C" are fields on the same model:
'''
#- The value of "A" should be greater than 0 if "B" is greater than "C". If either "B" or "C" are not defined, "A" should be "0"

'''domain=[If(Eval('B') > Eval('C'),
            [('A', '>', 0)],
            If(['OR',
                (Eval('B'), '=', None),(Eval('C'), '=', None)],
                [('A', '=', 0)],
                [] ))]'''

#- "A" should be not null if "B.x" is greater than "0"

'''=> pas possible,  Eval ne support pas les champs indirects'''

#- The field "x" of field "A" should be greater than field "y" on "A"

'''=> pas possible,  Eval ne support pas les champs indirects'''

#- The field "x" of field "A" should be greater than field "B" or equal to field "C"

'''domain=['OR',
        ('A.x', '>', Eval('B')),
        ('A.x', '=', Eval('C'))
        ]

'''
