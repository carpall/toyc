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

def plugin_call(impl_name, component, method, **kwargs):
  results = [getattr(plugin, impl_name)(component, method, **kwargs) for plugin in PLUGINS_INSTANCES]

  if any(results) != all(results):
    raise PluginError(f'plugins conflict on implementation of {impl_name} for {component}.{method}')
  
  return results[0]

class PluginError(Exception):
  pass

class Plugin:
  def __init__(self, **kwargs):
    self.__dict__ = kwargs

  def __init_subclass__(cls):
    PLUGINS_CLASSES.append(cls)
  
  def on_error_report(self, component, method, error):
    """
    Parameters
    ----------
    - `component: CompilerComponent` the compiler component which reported the error
    - `method: function` the method which made the plugin call
    - `error: CompilerError` the error instance

    Return
    ------
    `bool` indicates whether `method` should stop to be executed
    """

    return ContinueExecution

  def match_next_token(self, component, method, lexer):
    """
    Parameters
    ----------
    - `component: CompilerComponent` the compiler component which reported the error
    - `method: function` the method which made the plugin call
    - `lexer: Lexer` the lexer instance

    Return
    ------
    `Out(ret: bool, collector: function(Lexer) -> Token)` where `ret` indicates whether matching the token, `collector` is a function to collect the token
    """

    return Out(False, collector=lambda lexer: None)
  
  def match_comment_pattern(self, component, method, lexer):
    """
    Parameters
    ----------
    - `component: CompilerComponent` the compiler component which reported the error
    - `method: function` the method which made the plugin call
    - `lexer: Lexer` the lexer instance

    Return
    ------
    `Out(ret: bool, skipper: function(Lexer) -> None)` where `ret` indicates whether matching the comment, `skipper` is a function to skip the comment
    """

    return Out(False, skipper=lambda lexer: None)
  
  def on_token_append_to_lexer_output(self, component, method, lexer, lexer_output):
    """
    Parameters
    ----------
    - `component: CompilerComponent` the compiler component which reported the error
    - `method: function` the method which made the plugin call
    - `lexer: Lexer` the lexer instance
    - `lexer_output: List[Token]` the lexer output list

    Return
    ------
    `bool` indicates whether `method` should stop to be executed
    """

    return ContinueExecution