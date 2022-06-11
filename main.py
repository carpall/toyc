from exposed_components import *
from compiler_utils     import *
from plugin             import *
from utils              import *
from pretty_printer     import *
from sys                import argv

load_plugins('plugins')
init_plugins(COMPONENTS_MODULES)

compiler = Compiler(argv[1:], COMPONENTS_MODULES)
result   = compiler.parse_args()

# print(json(result))
PrettyAstFmt(result).print()