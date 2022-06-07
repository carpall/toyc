from exposed_components import *
from compiler_utils     import *
from plugin             import *
from sys                import argv

load_plugins('plugins')
init_plugins(COMPONENTS_MODULES)

compiler = Compiler(argv[1:], COMPONENTS_MODULES)
result = compiler.parse_args()

if result is not None:
  print(result.rewrite())