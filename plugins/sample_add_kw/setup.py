from plugin         import Plugin
from compiler_utils import CompilerComponent, Out, SourcePosition
from data           import BadNode, Token

class MyPlugin(Plugin):
  def __init__(self, components_modules):
    super().__init__(components_modules)
    
    self.lexer.KEYWORDS.append('my_keyword')

    # import my_parser
    # self.parser = my_parser