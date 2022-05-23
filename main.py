import compiler_utils, data, xlexer, preprocessor

from compiler_utils import *
from xlexer         import *
from preprocessor   import *
from parser         import *
from plugin         import *

load_plugins('plugins/')
init_plugins(utils_module=compiler_utils, data_module=data, lexer_module=xlexer, preprocessor_module=preprocessor)

src_info = SourceInfo('samples/sam1.c')

lexer_result = Lexer(src_info).gen()
lexer_result.print_errors_and_then(
  lambda tokens: [print('Lexer:'), print('\n'.join(map(lambda s: '  ' + s, map(repr, tokens)))), print()]
)

preprocessor_result = Preprocessor(src_info, lexer_result.result).gen()
preprocessor_result.print_errors_and_then(
  lambda tokens: [print('Preprocessor:'), print('\n'.join(map(lambda s: '  ' + s, map(repr, tokens)))), print()]
)

parser_result = Parser(src_info, preprocessor_result.result).gen()
parser_result.print_errors_and_then(
  lambda ast: [print('Parser:'), print(ast), print()]
)