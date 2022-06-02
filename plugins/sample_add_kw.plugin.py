from plugin         import Plugin
from compiler_utils import Out
from data           import Token

class MyPlugin(Plugin):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    
    self.lexer_module.KEYWORDS.append('my_keyword')