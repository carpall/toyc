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

class PtrTypeNode(Node):
  def __init__(self, type, pos):
    super().__init__(pos, type=type)
  
  def rewrite(self):
    return f'{self.type.rewrite()}*'

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
      r += f'\n{rewriter_indent}{node.rewrite()};'
    
    rewriter_indent = rewriter_indent[:-2]
    return r + f'\n{rewriter_indent}}}'

class BinNode(Node):
  def __init__(self, op, left, right):
    super().__init__(extend_pos(left.pos, right.pos), op=op, left=left, right=right)
  
  def rewrite(self):
    return f'({self.left.rewrite()} {self.op.rewrite()} {self.right.rewrite()})'

class UnaryNode(Node):
  def __init__(self, op, expr):
    super().__init__(extend_pos(op.pos, expr.pos), op=op, expr=expr)
  
  def rewrite(self):
    return f'(({self.op.rewrite()}({self.expr.rewrite()}))'

class WhileNode(Node):
  def __init__(self, condition_expr, body, pos):
    super().__init__(pos, condition_expr=condition_expr, body=body)
  
  def rewrite(self):
    return f'while ({self.condition_expr.rewrite()}) {self.body.rewrite()}'

class IfNode(Node):
  class ConditionCaseNode(Node):
    def __init__(self, case, condition_expr, body):
      super().__init__(case.pos, case=case, condition_expr=condition_expr, body=body)
  
    def rewrite(self):
      return \
        f'{self.case.rewrite()} ({self.condition_expr.rewrite()}) {self.body.rewrite()}' \
          if self.case.kind != 'else' else \
            f'else {self.body.rewrite()}'
  
  def __init__(self, nodes):
    super().__init__(nodes[0].pos, nodes=nodes)
  
  def rewrite(self):
    return ' '.join(map(lambda node: node.rewrite(), self.nodes))

class VarNode(Node):
  def __init__(self, type, name, expr):
    super().__init__(name.pos, type=type, name=name, expr=expr)
  
  def rewrite(self):
    return f'{self.type.rewrite()} {self.name.rewrite()}{f" = {self.expr.rewrite()}" if self.expr is not None else ""}'

class StructNode(Node):
  def __init__(self, name, body, pos):
    super().__init__(pos, name=name, body=body)
  
  def rewrite(self):
    return f'struct {self.name.rewrite()} {self.body.rewrite()}'

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
    return f'{self.type.rewrite()} {self.id.rewrite()}({", ".join(self.params)}) {self.body.rewrite() if self.body is not None else ""}'

class BadNode(Node):
  def __init__(self, pos):
    super().__init__(pos)
  
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