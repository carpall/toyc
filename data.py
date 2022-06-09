class Node:
  def __init__(self, kind):
    self.kind = kind
  
  def __str__(self):
    return repr(self)

  def __repr__(self):
    c = self.__dict__.copy()

    try:
      c.pop('pos')
    except KeyError:
      pass

    return repr(c)

class Token(Node):
  def __init__(self, kind, value, pos):
    super().__init__(kind)

    self.value = value
    self.pos = pos

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