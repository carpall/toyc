class Node:
  def __init__(self, pos):
    self.pos = pos
  
  def __repr__(self):
    return f'{self.__class__.__name__} {vars(self)}'

class BadNode(Node):
  def __init__(self, token):
    super().__init__(token.pos)
    
    self.token = token

class Token(Node):
  def __init__(self, kind, value, pos):
    super().__init__(pos)

    self.kind = kind
    self.value = value

class PreprocessorSymbol:
  def __init__(self, name, value):
    self.name = name
    self.value = value

class PreprocessorIdentifier(PreprocessorSymbol):
  pass

class PreprocessorMacro(PreprocessorSymbol):
  def __init__(self, name, args, value):
    super().__init__(name, value)

    self.args = args