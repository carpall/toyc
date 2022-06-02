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
    return self.tokens[self.idx]

  @property
  def bck(self):
    return self.tokens[self.idx - 1]

  @property
  def global_pos(self):
    return SourcePosition(self.src_info, None, None, None, None, None)
  
  def cur_or_last(self):
    return self.cur if not self.eof() else self.tokens[-1]

  def eof(self):
    return self.idx >= len(self.tokens)
  
  def save_idx(self):
    return self.idx

  def update_idx(self, new_idx):
    self.idx = new_idx
  
  def advance(self, count=1):
    self.idx += count

  def get_expecting_error_msg(self, method, args):
    return f"expected '{args[0]}'" if method.__name__ == 'match_token' else f"expected '{method.__name__.replace('match_', '')}'"

  def expect(self, method, *args):
    if not (matches := method(*args)).unwrap():
      self.report(self.get_expecting_error_msg(method, args), self.cur.pos)
      self.update_idx(new_idx := self.idx + 1)
      return Out(False, new_idx=new_idx, node=BadNode(self.cur_or_last()))
    
    self.update_idx(matches.new_idx)
    return matches
  
  def expect_any(self, *methods_and_args):
    for method, args in methods_and_args:
      if (matches := method(*args)).unwrap():
        self.update_idx(matches.new_idx)
        return matches
    
    self.report(
      f"expected one of '{' '.join([self.get_expecting_error_msg(method, args) for method, args in methods_and_args])}'",
      self.cur.pos
    )
    return Out(False, new_idx=self.idx + 1, node=None)

  def match_token(self, kind):
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

    return Out(True, new_idx=new_idx, type=IntTypeNode(self.convert_types_chain_to_single(types_chain, pos), pos))

  def match_type(self):
    if (matches_int_type := self.match_int_type()).unwrap():
      return matches_int_type
    
    return Out(False)

  def collect_fn_param_decl(self):
    type = self.expect(self.match_type).type
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

  def match_block(self):
    if not (_ := self.match_token('{')).unwrap():
      return Out(False)
    
    start_pos = self.cur.pos
    old_idx = self.save_idx()
    nodes = []

    self.advance()

    while not self.match_token('}'):
      nodes.append(self.expect(self.match_expr))

      if not (matches_colon := self.match_token(';')).unwrap() and not (matches_rbrace := self.match_on_idx(self.idx - 1, self.match_token, '}')).unwrap():
        self.report("expected ';'", matches_colon.node.pos)
    
    end_pos = self.cur.pos
    self.expect(self.match_token, '}')
    new_idx = self.save_idx_and_update(old_idx)

    return Out(True, new_idx=new_idx, node=ContainerNode(nodes, extend_pos(start_pos, end_pos)))

  def save_idx_and_update(self, old_idx):
    new_idx = self.save_idx()
    self.update_idx(old_idx)

    return new_idx

  def match_typed_node(self, matched_type):
    old_idx = self.save_idx_and_update(matched_type.new_idx)
    decl_type = matched_type.type
    decl_name = self.expect(self.match_token, 'id').node
    
    match self.cur.kind:
      case '(': # fn decl
        params = self.collect_fn_params_decl()
        block = self.expect_any((self.match_block, []), (self.match_token, [';'])).node

        node = FnNode(decl_type, decl_name, params, block if isinstance(block, ContainerNode) else None)

      case ';' | '=': # var decl
        self.advance()

        expr = self.expect(self.match_expr).node if self.bck.kind == '=' else None
        self.expect(self.match_token, ';')

        node = VarNode(decl_type, decl_name, expr)
        
      
      case _:
        return Out(False)
    
    return Out(True, new_idx=self.save_idx_and_update(old_idx), node=node)

  def match_term(self):
    if (matched_type := self.match_type()).unwrap():
      return self.match_typed_node(matched_type)
    
    if (matches_digit := self.match_token('digit')).unwrap():
      return matches_digit
    
    if (matches_id := self.match_token('id')).unwrap():
      return matches_id
    
    return Out(False)

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

  def match_expr(self):
    for plugin_matches_node in plugin_call('match_next_node', self.match_expr):
      if plugin_matches_node.unwrap():
        return plugin_matches_node

    return self.match_bin_or_term(
      lambda: self.match_bin_or_term(self.match_term, ['*', '/']),
      ['+', '-']
    )

  def gen(self):
    self.output = []

    while not self.eof():
      node = self.expect(self.match_expr).node

      self.output.append(node)

    return CompilerResult(self.errors_bag, ContainerNode(self.output, self.global_pos))