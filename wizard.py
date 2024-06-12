from trytond.model import ModelView, fields
from trytond.pool import Pool
from trytond.wizard import Wizard, StateView, StateTransition, StateAction
from trytond.wizard import Button
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder
from trytond.exceptions import UserWarning
import datetime

__all__ = [
    'CreateExemplaries',
    'CreateExemplariesParameters',
    'FuseBooks',
    'FuseBooksChoice',
    'FuseBooksValidation',

]


class CreateExemplaries(Wizard):
    'Create Exemplaries'
    __name__ = 'library.book.create_exemplaries'

    start_state = 'parameters'
    parameters = StateView('library.book.create_exemplaries.parameters',
                           'library.create_exemplaries_parameters_view_form', [
                               Button('Cancel', 'end', 'tryton-cancel'),
                               Button('Create', 'create_exemplaries',
                                      'tryton-go-next', default=True)])
    create_exemplaries = StateTransition()
    open_exemplaries = StateAction('library.act_exemplary')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
            'invalid_model': 'This action should be started from a book',
            'invalid_date': 'You cannot purchase books in the future',
        })

    def default_parameters(self, name):
        if Transaction().context.get('active_model', '') != 'library.book':
            self.raise_user_error('invalid_model')
        return {
            'acquisition_date': datetime.date.today(),
            'book': Transaction().context.get('active_id'),
            'acquisition_price': 10,
        }

    def transition_create_exemplaries(self):
        if (self.parameters.acquisition_date and
            self.parameters.acquisition_date > datetime.date.today()):
            self.raise_user_error('invalid_date')
        Exemplary = Pool().get('library.book.exemplary')
        to_create = []
        while len(to_create) < self.parameters.number_of_exemplaries:
            exemplary = Exemplary()
            exemplary.book = self.parameters.book
            exemplary.acquisition_date = self.parameters.acquisition_date
            exemplary.acquisition_price = self.parameters.acquisition_price
            exemplary.identifier = self.parameters.identifier_start + str(
                len(to_create) + 1)
            to_create.append(exemplary)
        Exemplary.save(to_create)
        self.parameters.exemplaries = to_create
        return 'open_exemplaries'

    def do_open_exemplaries(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [x.id for x in self.parameters.exemplaries])])
        return action, {}


class CreateExemplariesParameters(ModelView):
    'Create Exemplaries Parameters'
    __name__ = 'library.book.create_exemplaries.parameters'

    book = fields.Many2One('library.book', 'Book', readonly=True)
    number_of_exemplaries = fields.Integer('Number of exemplaries',
                                           required=True,
                                           domain=[('number_of_exemplaries', '>', 0)],
                                           help='The number of exemplaries that will be created')
    identifier_start = fields.Char('Identifier start', required=True,
                                   help='The starting point for exemplaries identifiers')
    acquisition_date = fields.Date('Acquisition Date')
    acquisition_price = fields.Numeric('Acquisition Price', digits=(16, 2),
                                       domain=[('acquisition_price', '>=', 0)],
                                       help='The price that was paid per exemplary bought')
    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
                                   'Exemplaries')


class FuseBooks(Wizard):
    'Fuse Books'
    __name__ = 'library.book.fuse_books'

    start_state = 'choice'
    choice = StateView('library.book.fuse_books.choice',
                           'library.fuse_books_choice_view_form', [
                               Button('Cancel', 'end', 'tryton-cancel'),
                               Button('Fuse', 'fuse_books',
                                      'tryton-go-next', default=True)])
    fuse_books = StateTransition()

    validation = StateView('library.book.fuse_books.validation',
                           'library.fuse_books_validation_view_form', [
                               Button('Cancel', 'end', 'tryton-cancel'),
                               Button('Validate', 'fuse_books_val',
                                      'tryton-go-next', default=True)])
    fuse_books_val = StateTransition()
 

    @classmethod
    def __setup__(cls):

        super().__setup__()
        cls._error_messages.update({
            'invalid_model': 'This action should be started from a book',
            'invalid_author': 'The merge of Books had to be from the same author',
            'invalid_book_count': 'At least 2 books are needed to be fused',
        })


    def default_choice(self, name):
        
        if Transaction().context.get('active_model', '') != 'library.book':
            self.raise_user_error('invalid_model')
        
        #récupération de tous les book ids
        selected_book_ids = Transaction().context.get('active_ids', [])
        
        #check s'il y a au moins 2 books pour le merge
        if len(selected_book_ids) < 2:
            self.raise_user_error('invalid_book_count')
        
        ##check si tous les books ont le même auteur
        Book = Pool().get('library.book')
        book = Book()
        s_author = set()
        for book_author in book.read(selected_book_ids, ['author']):
            s_author.add(book_author['author'])
        if len(s_author) != 1:
            self.raise_user_error('invalid_author')

        #initialisation du nombre d'exemplaire
        Exemplary = Pool().get('library.book.exemplary')
        exemplary = Exemplary()
        exemplary_count = 0
        for book in exemplary.search([('book', 'in', selected_book_ids)]):
                exemplary_count += 1

        return {
            'books': selected_book_ids,
            'number_of_exemplaries': exemplary_count,
            'num_book_master' : 1,
        }

    def default_validation(self, name):
        #import web_pdb;web_pdb.set_trace()
        return {
            'final_book': [self.choice.books[self.choice.num_book_master -1].id],
            'books' : [x.id for x in self.choice.books],
        }

    def transition_fuse_books(self):

        #check si tous les books ont les mêmes caractéritiques
        #faudrait boucler avec seulement qq clés importantes
        dict_book = {}
        
        for book in self.choice.books:            
            for field_name in book._fields.keys():
                if field_name not in dict_book:
                    dict_book[field_name] = set()

                dict_book[field_name].add(getattr(book,field_name, None ))
      
        #gestion du warning
        l_col_mismatched = []
        for field_name, field_value in dict_book.items():
            if len(field_value) != 1:
                l_col_mismatched.append(field_name)
        #if len(l_col_mismatched) != 1 :
            #self.raise_user_warning('fields_mismatched' , {'l_col_mismatched': l_col_mismatched})
           
        return 'validation'
        
                
    def transition_fuse_books_val(self):
        #import web_pdb;web_pdb.set_trace()
        to_delete = [x for x in self.validation.books]
        to_delete.remove(self.validation.books[self.choice.num_book_master -1])

        Book = Pool().get('library.book')
        Book.delete(to_delete)
        
        return 'reload'

class FuseBooksChoice(ModelView):
    'Fuse Books Choice'
    __name__ = 'library.book.fuse_books.choice'

    books = fields.One2Many('library.book', None,
                            'Books', readonly=True)
    number_of_exemplaries = fields.Integer('Number of exemplaries', readonly=True)
    num_book_master = fields.Integer('Number of the Book Master')

class FuseBooksValidation(ModelView):
    'Fuse Books Validation'
    __name__ = 'library.book.fuse_books.validation'

    final_book = fields.One2Many('library.book', None,
                            'Final Book', readonly=True)
    books = fields.One2Many('library.book', None,
                            'Books')


