from compiler_utils import extend_pos
from utils          import Debug

rewriter_indent = ''

class Node(Debug):
  def __init__(self, pos, **kwargs):
    self.__dict__ = kwargs
    self.pos = pos

    super().__init__(['pos'])
  
  def rewrite(self):
    raise NotImplementedError(f"{self.__class__.__name__} does not implement 'fmt'")

class IntTypeNode(Node):
  def __init__(self, kind, pos):
    super().__init__(pos, kind=kind)
  
  def rewrite(self):
    return f'{self.kind}'

class ContainerNode(Node):
  def __init__(self, nodes, pos):
    super().__init__(pos, nodes=nodes)
  
  def rewrite(self):
    global rewriter_indent

    r = '{'
    rewriter_indent += '  '

    for node in self.nodes:
      r += f'\n{rewriter_indent}{node.rewrite()}'
    
    rewriter_indent = rewriter_indent[:-2]
    return r + f'\n{rewriter_indent}}}'

class VarNode(Node):
  def __init__(self, type, name, expr):
    super().__init__(name.pos, type=type, name=name, expr=expr)
  
  def rewrite(self):
    return f'{self.type.rewrite()} {self.name.rewrite()} {self.expr.rewrite() if self.expr is not None else ""};'

class FnNode(Node):
  class ParamNode(Node):
    def __init__(self, id, type):
      super().__init__(extend_pos(id.pos, type.pos), type=type, id=id)
    
    def rewrite(self):
      return f'{self.type.rewrite()} {self.id.rewrite()}'

  def __init__(self, type, id, params, body):
    super().__init__(
      id.pos,
      type=type,
      id=id,
      params=params,
      body=body
    )
  
  def rewrite(self):
    return f'{self.type.rewrite()} {self.id.rewrite()}({", ".join(self.params)}) {self.body.rewrite() if self.body is not None else ";"}'

class BadNode(Node):
  def __init__(self, token):
    super().__init__(token.pos, token=token)
  
  def rewrite(self):
    return '<?>'

class Token(Node):
  def __init__(self, kind, value, pos):
    super().__init__(pos, kind=kind, value=value)
  
  def rewrite(self):
    return f'{self.value}'

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