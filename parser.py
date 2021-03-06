from inspect import unwrap
from turtle import right
from compiler_utils import CompilerComponent, CompilerResult, SourcePosition
from utils          import *
from data           import *
from plugin         import plugin_call

BUILTIN_INT_TYPES = ['signed', 'unsigned', 'char', 'short', 'int', 'long']

class Parser(CompilerComponent):
  def __init__(self, src_info, tokens):
    super().__init__(src_info)

    self.tokens = tokens
    self.idx = 0

  @property
  def cur(self):
    return self.tokens[self.idx] if not self.eof() else Token(
      'eof',
      '',
      SourcePosition(
        self.src_info,
        self.last.pos.row,
        self.last.pos.col + self.last.pos.len,
        1,
        None,
        None
      )
    )

  @property
  def bck(self):
    return self.tokens[self.idx - 1]
  
  @property
  def last(self):
    return self.tokens[-1]

  @property
  def global_pos(self):
    return SourcePosition(self.src_info, None, None, None, None, None)

  def eof(self):
    return self.idx >= len(self.tokens)
  
  def save_idx(self):
    return self.idx

  def update_idx(self, new_idx):
    self.idx = new_idx
  
  def advance(self, count=1):
    self.idx += count

    return self.tokens[self.idx - count]

  def get_expecting_error_msg(self, method, args, get_just_token=False):
    match method.__name__:
      case 'match_token':
        token = f"'{args[0]}'"
      
      case '<lambda>':
        token = f"'expr'"

      case _:
        token = f"'{method.__name__.replace('match_', '')}'"
    
    if get_just_token:
      return token
    
    return f'expect {token}'

  def expect(self, method, *args):
    if not (matches := method(*args)).unwrap():
      self.report(self.get_expecting_error_msg(method, args), self.cur.pos)
      self.update_idx(new_idx := self.idx + 1)
      return Out(False, new_idx=new_idx, node=BadNode(self.cur.pos))

      # return Out(False, new_idx=self.idx, node=BadNode(self.cur.pos))
    
    self.update_idx(matches.new_idx)
    return matches
  
  def expect_any(self, *methods_and_args):
    for method, args in methods_and_args:
      if (matches := method(*args)).unwrap():
        self.update_idx(matches.new_idx)
        return matches
    
    self.report(
      f"expected one of {', '.join([self.get_expecting_error_msg(method, args, get_just_token=True) for method, args in methods_and_args])}",
      self.cur.pos
    )

    return Out(False, new_idx=self.idx + 1, node=None)

  def match_token(self, kind):
    if self.eof():
      return Out(False)

    return Out(self.cur.kind == kind, new_idx=self.idx + 1, node=self.cur)
  
  def match_any_token(self, kinds):
    for kind in kinds:
      if (matches_token := self.match_token(kind)).unwrap():
        return matches_token
    
    return Out(False)

  def convert_types_chain_to_single(self, chain, pos):
    try:
      return {
        'char': 'chr',
        'signed char': 'chr',
        'unsigned char': 'uchr',

        'short': 'i16',
        'short int': 'i16',
        'signed short': 'i16',
        'signed short int': 'i16',

        'unsigned short': 'u16',
        'unsigned short int': 'u16',

        'int': 'i32',
        'signed': 'i32',
        'signed int': 'i32',

        'unsigned': 'u32',
        'unsigned int': 'u32',

        'long': 'i64',
        'long int': 'i64',
        'signed long': 'i64',
        'signed long int': 'i64',

        'unsigned long': 'u64',
        'unsigned long int': 'u64',

        'long long': 'i64',
        'long long int': 'i64',
        'signed long long': 'i64',
        'signed long long int': 'i64',

        'unsigned long long': 'u64',
        'unsigned long long int': 'u64',
      }[' '.join(chain)]
    except KeyError:
      self.report('invalid integer type', pos)

  def match_int_type(self):
    if self.cur.kind not in BUILTIN_INT_TYPES:
      return Out(False)

    old_idx = self.save_idx()
    start_pos = self.cur.pos
    types_chain = []

    while self.cur.kind in BUILTIN_INT_TYPES:
      types_chain.append(self.cur.kind)
      self.advance()
    
    pos = extend_pos(start_pos, self.bck.pos)
    new_idx = self.save_idx_and_update(old_idx)

    return Out(True, new_idx=new_idx, node=IntTypeNode(self.convert_types_chain_to_single(types_chain, pos), pos))

  def match_type(self):
    if not (
      (matches_type := self.match_int_type())    .unwrap() or \
      (matches_type := self.match_token('id'))   .unwrap() or \
      (matches_type := self.match_struct_node()) .unwrap()
    ): return Out(False)

    # when the definition of a strutt is taken for the definition of a variable
    # just check if there is a point and a comma then you want to define a strutt otherwise you want to define a variable
    if isinstance(matches_type.node, StructNode) and self.match_on_idx(
      matches_type.new_idx,
      self.match_token,
      ';'
    ).unwrap():
      return Out(False)

    old_idx = self.save_idx_and_update(matches_type.new_idx)
    node = matches_type.node
    
    while not self.eof() and self.match_token('*').unwrap():
      node = PtrTypeNode(node, extend_pos(node.pos, self.advance().pos))
    
    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=node)

  def collect_fn_param_decl(self):
    type = self.expect(self.match_type).node
    id = self.expect(self.match_token, 'id').node

    return FnNode.ParamNode(id, type)

  def collect_fn_params_decl(self):
    self.expect(self.match_token, '(')
    params = []

    while True:
      # fn with no params
      if len(params) == 0 and (_ := self.match_token(')')).unwrap():
        break

      params.append(self.collect_fn_param_decl())

      if (_ := self.match_token(',')).unwrap():
        self.advance()
      else:
        break

    self.expect(self.match_token, ')')
    return params

  def match_on_idx(self, idx, matcher, *args):
    old_idx = self.save_idx_and_update(idx)
    result = matcher(*args)
    self.update_idx(old_idx)

    return result

  def match_block(self, allow_implicit_braces=True):
    if not (_ := self.match_token('{')).unwrap():
      if allow_implicit_braces:
        return self.match_expr(True)
      
      return Out(False)
    
    start_pos = self.cur.pos
    old_idx = self.save_idx()
    nodes = []

    self.advance()

    while not self.match_token('}').unwrap():
      nodes.append(self.expect(self.match_expr, True).node)

      # if not (matches_colon := self.match_token(';')).unwrap() and not self.match_on_idx(self.idx - 1, self.match_token, '}').unwrap():
      #   self.report("expected ';'", matches_colon.node.pos)
    
    end_pos = self.cur.pos
    self.expect(self.match_token, '}')

    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=ContainerNode(nodes, extend_pos(start_pos, end_pos)))

  def save_idx_and_update(self, old_idx):
    new_idx = self.save_idx()
    self.update_idx(old_idx)

    return new_idx

  def match_typed_node(self):
    if not (matched_type := self.match_type()).unwrap():
      return Out(False)

    old_idx = self.save_idx_and_update(matched_type.new_idx)
    decl_type = matched_type.node
    decl_name = self.expect(self.match_token, 'id').node
    
    match self.cur.kind:
      case '(': # fn decl
        node = self.collect_typed_fn_node(decl_type, decl_name)

      case ';' | '=': # var decl
        node = self.collect_typed_var_node(decl_type, decl_name)
      
      case _:
        return self.match_typed_unknown_node(old_idx, decl_type, decl_name)
    
    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=node)

  def match_typed_unknown_node(self, old_idx, decl_type, decl_name):
    self.update_idx(old_idx)
    return Out(False)

  def collect_typed_var_node(self, decl_type, decl_name):
    expr = None

    if self.cur.kind == '=':
      self.advance()
      expr = self.expect(self.match_expr).node if self.bck.kind == '=' else None

    return VarNode(decl_type, decl_name, expr)

  def collect_typed_fn_node(self, decl_type, decl_name):
    params = self.collect_fn_params_decl()
    block = self.expect_any((self.match_block, [False]), (self.match_token, [';'])).node

    return FnNode(decl_type, decl_name, params, block if isinstance(block, ContainerNode) else None)

  def match_parenthesized_expr(self):
    if not self.match_token('(').unwrap():
      return Out(False)

    old_idx = self.save_idx()
    start_pos = self.advance().pos
    expr = self.expect(self.match_expr).node
    end_pos = self.expect(self.match_token, ')').node.pos

    expr.pos = extend_pos(start_pos, end_pos)

    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=expr)

  def match_unary_expr(self):
    if not self.match_any_token(['+', '-']).unwrap():
      return Out(False)

    old_idx = self.save_idx()

    op = self.advance()
    expr = self.expect(self.match_expr).node

    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=UnaryNode(op, expr))

  def match_if_node(self):
    old_idx = self.save_idx()
    nodes = []
    
    while not self.eof() and self.match_any_token(['if', 'else']).unwrap():
      case = self.advance()

      if case.kind == 'if' and len(nodes) > 0:
        # this is another if statement, it has nothing to do with this
        self.advance(-1)
        break
      
      if case.kind == 'else':
        if self.match_token('if').unwrap():
          if_kw = self.advance()
          case = Token('elif', 'else if', extend_pos(case.pos, if_kw.pos))
        
        if len(nodes) == 0:
          self.report(f"expected 'if' before '{case.value}'", case.pos)
      
      if len(nodes) > 0 and nodes[-1].case.kind == 'else':
        self.report(f"unexpected '{case.value}' after 'else'", case.pos)
      
      condition_expr = self.expect(self.match_parenthesized_expr).node if case.kind != 'else' else None
      body = self.expect(self.match_block).node
      
      nodes.append(IfNode.ConditionCaseNode(case, condition_expr, body))

    new_idx = self.save_idx_and_update(old_idx)

    if len(nodes) == 0:
      return Out(False)

    return Out(True, new_idx=new_idx, node=IfNode(nodes))
  
  def eat(self, matcher, *args):
    if (matches := matcher(*args)).unwrap():
      self.update_idx(matches.new_idx)
      return matches.node

  def match_while_node(self):
    old_idx = self.save_idx()

    if not self.match_token('while').unwrap():
      return Out(False)

    pos = self.advance().pos
    condition_expr = self.expect(self.match_parenthesized_expr).node
    body = self.expect(self.match_block).node

    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=WhileNode(condition_expr, body, pos))

  def has_body(self, node):
    return isinstance(node, (ContainerNode, FnNode, IfNode, WhileNode))

  def match_struct_node(self):
    if not self.match_token('struct').unwrap():
      return Out(False)
    
    old_idx = self.save_idx()
    pos = self.advance().pos
    name = self.eat(self.match_token, 'id')
    body = self.expect(self.match_block).node

    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=StructNode(name, body, pos))

  def match_term(self, is_statement):
    if not (
      (m := self.match_typed_node())         .unwrap() or \
      (m := self.match_token('digit'))       .unwrap() or \
      (m := self.match_token('id'))          .unwrap() or \
      (m := self.match_if_node())            .unwrap() or \
      (m := self.match_while_node())         .unwrap() or \
      (m := self.match_parenthesized_expr()) .unwrap() or \
      (m := self.match_unary_expr())         .unwrap() or
      (m := self.match_struct_node())        .unwrap()
    ): return Out(False)

    old_idx = self.save_idx_and_update(m.new_idx)

    if is_statement:
      self.skip_semicolon(expect_first=not self.has_body(m.node))

    m.new_idx = self.save_idx_and_update(old_idx)
    
    return m

  def match_bin_or_term(self, members_matcher, ops):
    if not (matches_left := members_matcher()).unwrap():
      return Out(False)
    
    old_idx = self.save_idx_and_update(matches_left.new_idx)
    left = matches_left.node

    while not self.eof() and (matches_op := self.match_any_token(ops)).unwrap():
      self.update_idx(matches_op.new_idx)

      right = self.expect(members_matcher).node
      left = BinNode(matches_op.node, left, right)

    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=left)

  def match_expr(self, is_statement=False):
    for plugin_matches_node in plugin_call('match_next_node', self.match_expr):
      if plugin_matches_node.unwrap():
        return plugin_matches_node

    return self.match_bin_or_term(
      lambda: self.match_bin_or_term(lambda: self.match_term(is_statement), ['*', '/']),
      ['+', '-']
    )
  
  def skip(self, matcher, *args):
    if not (matches := matcher(*args)).unwrap():
      return
    
    self.update_idx(matches.new_idx)
  
  def skip_all(self, matcher, *args):
    while (matches := matcher(*args)).unwrap():
      self.update_idx(matches.new_idx)
  
  def skip_semicolon(self, expect_first):
    if expect_first:
      self.expect(self.match_token, ';')

    self.skip_all(self.match_token, ';')

  def gen(self):
    self.output = []

    while not self.eof():
      node = self.expect(self.match_expr).node
      self.skip_semicolon(expect_first=not self.has_body(node))

      self.output.append(node)

    return CompilerResult(self.errors_bag, ContainerNode(self.output, self.global_pos))