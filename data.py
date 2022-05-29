from compiler_utils import extend_pos
from utils          import Debug

class Node(Debug):
  def __init__(self, pos, **kwargs):
    self.__dict__ = kwargs
    self.pos = pos

    super().__init__(['pos'])

class IntTypeNode(Node):
  def __init__(self, kind, pos):
    super().__init__(pos, kind=kind)

class BlockNode(Node):
  def __init__(self, nodes, pos):
    super().__init__(pos, nodes=nodes)

class FnNode(Node):
  class ParamNode(Node):
    def __init__(self, id, type):
      super().__init__(extend_pos(id.pos, type.pos), type=type, id=id)

  def __init__(self, type, id, params, body):
    super().__init__(
      id.pos,
      type=type,
      id=id,
      params=params,
      body=body
    )

class BadNode(Node):
  def __init__(self, token):
    super().__init__(token.pos, token=token)

class Token(Node):
  def __init__(self, kind, value, pos):
    super().__init__(pos, kind=kind, value=value)

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