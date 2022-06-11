from data import Node, Token

class PrettyAstFmt:
  def __init__(self, ast):
    self.ast = ast
    self.indent_level = 0
  
  @property
  def indent(self):
    return '  ' * self.indent_level

  def node_needs_semicolon(self, node):
    return not hasattr(node, 'body')

  def fmt_str(self, str):
    return str
  
  def fmt_continue(self, _):
    return f'continue'

  def fmt_break(self, _):
    return f'break'
  
  def fmt_assign(self, assign):
    lvalue = self.fmt_node(assign.lvalue)
    rvalue = self.fmt_node(assign.rvalue)

    return f'{lvalue} = {rvalue}'
  
  def fmt_while_(self, while_):
    expr = self.fmt_node(while_.expr)
    body = self.fmt_node(while_.body)

    return f'while ({expr}) {body}'
  
  def fmt_if_(self, if_):
    def fmt_elseif_node(node):
      return f'else if ({self.fmt_node(node.expr)}) {self.fmt_node(node.body)}'

    expr         = self.fmt_node(if_.expr)
    body         = self.fmt_node(if_.body)
    elseif_nodes = ' ' + ' '.join(map(fmt_elseif_node, if_.elseif_nodes)) + ' '
    else_node    = f'else {self.fmt_node(if_.else_node)}' if if_.else_node is not None else ''

    return f'if ({expr}) {body}{elseif_nodes}{else_node}'
  
  def fmt_var(self, var):
    def fmt_id_value(id_value):
      id    = self.fmt_node(id_value.id)
      value = f' = {self.fmt_node(id_value.value)}' if id_value.value is not None else ''

      return f'{id}{value}'

    type       = self.fmt_node(var.type)
    ids_values = ', '.join(map(fmt_id_value, var.ids_values))

    return f'{type} {ids_values}'

  def fmt_par(self, par):
    expr = self.fmt_node(par.expr)

    return f'({expr})'

  def fmt_call(self, call):
    args = ', '.join(map(self.fmt_node, call.args))

    return f'({args})'

  def fmt_inline_if_node(self, inline_if_node):
    then_expr = self.fmt_node(inline_if_node.then_expr)
    else_expr = self.fmt_node(inline_if_node.else_expr)

    return f' ? {then_expr} : {else_expr}'

  def fmt_digit(self, digit):
    return digit.value
  
  def fmt_term(self, term):
    node      = self.fmt_node(term.node)
    call_node = self.fmt_node(term.call_node) if term.call_node is not None else ''

    return f'{node}{call_node}'

  def fmt_expr(self, expr):
    def fmt_op_or_sub_bin(node):
      if isinstance(node, Token):
        return node.value

      return ' '.join(
        map(lambda node: node.value if isinstance(node, Token)else self.fmt_node(node), node)
      )
    
    nodes     = ' '.join(map(fmt_op_or_sub_bin, expr.nodes))
    inline_if = self.fmt_node(expr.inline_if) if expr.inline_if is not None else ''

    return f'{nodes}{inline_if}'

  def fmt_return_(self, return_):
    expr = f' {self.fmt_node(return_.expr)}' if return_.expr is not None else ''

    return f'return{expr}'

  def fmt_block(self, block):
    semicolon_when_needed = lambda statement: ';' if self.node_needs_semicolon(statement) else ''

    if hasattr(block, 'statement'):
      return f'\n{self.indent}  ' + self.fmt_node(block.statement) + semicolon_when_needed(block.statement)
    
    s = '{'
    self.indent_level += 1

    for statement in block.statements:
      s += '\n' + self.indent + self.fmt_node(statement) + semicolon_when_needed(statement)
    
    self.indent_level -= 1
    s += f'\n{self.indent}}}'

    return s

  def fmt_id(self, id):
    return id.value

  def fmt_type(self, type):
    is_unsigned = 'unsigned ' if type.is_unsigned else ''
    name        = self.fmt_node(type.name)
    ptr_level   = '*' * type.ptr_level

    return f'{is_unsigned}{name}{ptr_level}'

  def fmt_fn(self, fn):
    type   = self.fmt_node(fn.type)
    id     = self.fmt_node(fn.id)
    params = ', '.join(map(self.fmt_node, fn.params))
    body   = self.fmt_node(fn.body)

    return f'{type} {id}({params}) {body}'

  def fmt_node(self, node):
    attr = f'fmt_{node.kind}' if isinstance(node, Node) else f'fmt_{type(node).__name__}'

    if not hasattr(self, attr):
      raise Exception(f"unknown node kind: '{node.kind}'")
    
    return getattr(self, attr)(node)

  def fmt(self):
    return '\n'.join(map(self.fmt_node, self.ast))

  def print(self):
    pretty_fmt = self.fmt()
    print(pretty_fmt)