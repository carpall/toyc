import sys

from os      import listdir
from os.path import isdir
from types   import ModuleType
from utils   import Out

PLUGINS_CLASSES   = []
PLUGINS_INSTANCES = []

def load_plugins(path):
  for member in listdir(path):
    member = f'{path}/{member}'

    if not isdir(member):
      continue

    plugin_setup_path = f'{member}/setup.py'

    module = ModuleType('setup')
    module.__file__ = plugin_setup_path

    sys.path.append(member)
    exec(open(plugin_setup_path).read(), module.__dict__)
    sys.path.remove(member)

def init_plugins(**kwargs):
  for plugin_class in PLUGINS_CLASSES:
    PLUGINS_INSTANCES.append(plugin_class(**kwargs))

def plugin_call(impl_name, component, **kwargs):
  for plugin in PLUGINS_INSTANCES:
    yield getattr(plugin, impl_name)(component, **kwargs)

class PluginError(Exception):
  pass

class Plugin:
  def __init__(self, **kwargs):
    self.__dict__ = kwargs

  def __init_subclass__(cls):
    PLUGINS_CLASSES.append(cls)
  
  def on_error_report(self, component, error):
    """
    this call occurs when an error is about to be added to the component's error list

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `error: CompilerError`                       the error instance

    Return
    ------
    `None`
    """

    return
  
  def on_error_reported(self, component, error):
    """
    this call occurs when an error has just been added

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `error: CompilerError`                       the error instance

    Return
    ------
    `None`
    """

    return

  def match_next_token(self, component):
    """
    this call occurs when the lexer component is trying to find a token to collect

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call

    Return
    ------
    `Out(ret: bool, collector: function(Lexer) -> Token)` where `ret` indicates whether matching the token, `collector` is a function to collect the token
    """

    return Out(False, collector=lambda lexer: None)
  
  def on_token_append_to_lexer_output(self, component):
    """
    this call occurs when the lexer component is about to add a token to the token list

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call

    Return
    ------
    `None`
    """

    return
  
  def on_token_appended_to_lexer_output(self, component):
    """
    this call occurs when the lexer component just added a token to the token list

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call

    Return
    ------
    `None`
    """

    return
  
  def on_redefine_preprocessor_symbol(self, component, symbol):
    """
    this call occurs when the preprocessor component is about to redefine an already defined symbol

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol: PreprocessorSymbol`                 the symbol that is about to be defined

    Return
    ------
    `None`
    """

    return
  
  def on_redefined_preprocessor_symbol(self, component, symbol):
    """
    this call occurs when the preprocessor component just redefined an already defined symbol

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol: PreprocessorSymbol`                 the symbol that is about to be defined

    Return
    ------
    `None`
    """

    return
  
  def on_define_new_preprocessor_symbol(self, component, symbol):
    """
    this call occurs when the preprocessor component is about to define a new symbol (not defined yet)

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol: PreprocessorSymbol`                 the symbol that is about to be defined

    Return
    ------
    `None`
    """

    return
  
  def on_defined_new_preprocessor_symbol(self, component, symbol):
    """
    this call occurs when the preprocessor component just defined a new symbol (not defined yet)

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol: PreprocessorSymbol`                 the symbol that is about to be defined

    Return
    ------
    `None`
    """

    return
  
  def on_undefine_preprocessor_symbol(self, component, symbol_name):
    """
    this call occurs when the preprocessor component is about to undefine a defined symbol

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol_name: str`                           the symbol name that is about to be defined

    Return
    ------
    `None`
    """

    return
  
  def on_undefined_preprocessor_symbol(self, component, symbol_name):
    """
    this call occurs when the preprocessor component just undefined a defined symbol

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol_name: str`                           the symbol name that is about to be defined

    Return
    ------
    `None`
    """

    return
  
  def on_undefine_preprocessor_symbol_not_found(self, component, symbol_name):
    """
    this call occurs when the preprocessor component is about to undefine an undefined symbol

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol_name: str`                           the symbol name that is about to be defined

    Return
    ------
    `None`
    """

    return
  
  def on_unknown_preprocessor_directive(self, component, directive):
    """
    this call occurs when the preprocessor component is about to report the invalid directive

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `directive: Token`                           the symbol name that is about to be defined

    Return
    ------
    `str` a string indicating races details of which the caller must take into account after the call:
    {
      'avoid_reporting': the caller won't report the 'unknown directive' error
    }
    """

    return
  
  def match_next_node(self, component):
    """
    this call occurs when the parser component is matching nodes to add to the ast, in any context (global, local, expression, etc...)

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call

    Return
    ------
    `Out(ret: bool, new_idx: int, node: Node)` where `ret` indicates whether matching the node, `new_idx` it's the index to which the caller must skip, 'node' it's the matched node
    """

    return Out(False, new_idx=None, node=None)