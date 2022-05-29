from os    import listdir
from types import ModuleType
from utils import Out

StopExecution = True
ContinueExecution = False

PLUGINS_CLASSES   = []
PLUGINS_INSTANCES = []

def load_plugins(path):
  for file in listdir(path):
    if file.endswith('.plugin.py'):
      module = ModuleType(file.removesuffix('.plugin.py'))
      exec(open(f'{path}/{file}').read(), module.__dict__)

def init_plugins(**kwargs):
  for plugin_class in PLUGINS_CLASSES:
    PLUGINS_INSTANCES.append(plugin_class(**kwargs))

def plugin_call(impl_name, component, **kwargs):
  results = [getattr(plugin, impl_name)(component, **kwargs) for plugin in PLUGINS_INSTANCES]

  if any(results) != all(results):
    raise PluginError(f'plugins conflict on implementation of {impl_name} hook for {component}')
  
  return results[0]

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
    - `error: CompilerError`         the error instance

    Return
    ------
    `bool` indicates whether the caller should stop to be executed
    """

    return ContinueExecution

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
  
  def match_comment_pattern(self, component):
    """
    this call occurs when the lexer component is trying to find a comment

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call

    Return
    ------
    `Out(ret: bool, skipper: function(Lexer) -> None)` where `ret` indicates whether matching the comment, `skipper` is a function to skip the comment
    """

    return Out(False, skipper=lambda lexer: None)
  
  def on_token_append_to_lexer_output(self, component):
    """
    this call occurs when the lexer component is about to add a token to the token list

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call

    Return
    ------
    `bool` indicates whether the caller should stop to be executed
    """

    return ContinueExecution
  
  def on_redefine_preprocessor_symbol(self, component, symbol):
    """
    this call occurs when the preprocessor component is about to redefine an already defined symbol

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol: PreprocessorSymbol`                 the symbol that is about to be defined

    Return
    ------
    `bool` indicates whether the caller should stop to be executed
    """

    return ContinueExecution
  
  def on_define_new_preprocessor_symbol(self, component, symbol):
    """
    this call occurs when the preprocessor component is about to define a new symbol (not defined yet)

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol: PreprocessorSymbol`                 the symbol that is about to be defined

    Return
    ------
    `bool` indicates whether the caller should stop to be executed
    """

    return ContinueExecution
  
  def on_undefine_preprocessor_symbol(self, component, symbol_name):
    """
    this call occurs when the preprocessor component is about to undefine a defined symbol

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `symbol_name: str`                           the symbol name that is about to be defined

    Return
    ------
    `bool` indicates whether the caller should stop to be executed
    """

    return ContinueExecution
  
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

    return None
  
  def on_unknown_preprocessor_directive(self, component, directive):
    """
    this call occurs when the preprocessor component is about to report the invalid directive

    Parameters
    ----------
    - `component: MethodType[CompilerComponent.*]` the compiler component instance which made the plugin call
    - `directive: Token`                           the symbol name that is about to be defined

    Return
    ------
    `bool` indicates whether the caller should stop to be executed
    """

    return ContinueExecution
  
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