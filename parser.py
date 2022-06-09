from compiler_utils import CompilerComponent, CompilerResult
from utils          import Out
from data           import Node

OUT_FALSE = Out(False, node=None)

class macro_dbg:
  def __str__(self):
    return repr(self)
  
  def __repr__(self):
    return f'{type(self).__name__}({self.__dict__})'

class as_field(macro_dbg):
  def __init__(self, name, to_match):
    self.name = name
    self.to_match = to_match

def field(to_match):
  if not isinstance(to_match, str):
    raise Exception("expected str to match")

  return as_field(to_match, to_match)

class one_of(macro_dbg):
  def __init__(self, *one_of_them_to_match):
    self.one_of_them_to_match = one_of_them_to_match

class undefined_seq(macro_dbg):
  def __init__(self, to_match, sep=None, require_sep_at_edges=False):
    self.to_match = to_match
    self.sep = sep
    self.require_sep_at_edges = require_sep_at_edges

class pattern(macro_dbg):
  def __init__(self, kind, *to_match, can_be_matched_alone=True):
    self.kind = kind
    self.to_match = to_match
    self.can_be_matched_alone = can_be_matched_alone

PATTERNS = [
  pattern('type', as_field('kind', one_of('char', 'short', 'int', 'long'))),

  pattern('var', field('type'), field('id'), '=', field('expr'), ';'),

  pattern('fn',
    field('type'),
    field('id'),
    '(',
    as_field('params', undefined_seq(pattern('param', field('type'), field('id')), sep='=', require_sep_at_edges=False)),
    ')',
    as_field('body', 'block')
  )
]

PATTERNS = [
  pattern('x', as_field('type', 'int'), as_field('ids', undefined_seq('id', sep=',')), ';'),
]

class Parser(CompilerComponent):
  def __init__(self, src_info, tokens):
    super().__init__(src_info)

    self.tokens = tokens
    self.idx = 0
  
  @property
  def cur(self):
    return self.cur_plus(0)
  
  def cur_plus(self, count):
    return self.tokens[self.idx + count]
  
  def advance(self, count=1):
    self.idx += count
    return self.idx

  def eof(self):
    return self.idx >= len(self.tokens)

  def has_pattern_for(self, pattern_name):
    for pattern in PATTERNS:
      if pattern.kind == pattern_name:
        return Out(True, pattern=pattern)
    
    return Out(False)

  def match_pattern(self, pattern_to_match):
    match type(pattern_to_match).__name__:
      case 'pattern':
        node = Node(pattern_to_match.kind)

        for step in pattern_to_match.to_match:
          if not (matches := self.match_pattern(step)).unwrap():
            return OUT_FALSE

          if hasattr(matches, 'field_name') and matches.field_name is not None:
            setattr(node, matches.field_name, matches.field_value)
        
        return Out(True, node=node)
      
      case 'as_field':
        return Out(
          (matches := self.match_pattern(pattern_to_match.to_match)).unwrap(),
          field_name=pattern_to_match.name,
          field_value=matches.node)
      
      case 'one_of':
        for to_match in pattern_to_match.one_of_them_to_match:
          if (matches := self.match_pattern(to_match)).unwrap():
            return matches
        
        return OUT_FALSE
      
      case 'undefined_seq':
        nodes = []

        if pattern_to_match.require_sep_at_edges and pattern_to_match.sep is not None:
          if not self.match_pattern(pattern_to_match.sep).unwrap():
            return OUT_FALSE

        while True:
          if len(nodes) > 0 and pattern_to_match.sep is not None:
            if not self.match_pattern(pattern_to_match.sep).unwrap():
              break
          
          if not (matches := self.match_pattern(pattern_to_match.to_match)).unwrap():
            break

          nodes.append(matches.node)
        
        if pattern_to_match.require_sep_at_edges and pattern_to_match.sep is not None:
          if not self.match_pattern(pattern_to_match.sep).unwrap():
            return OUT_FALSE
        
        return Out(True, node=nodes)

      case 'str':
        if (has_pattern := self.has_pattern_for(pattern_to_match)).unwrap():
          return self.match_pattern(has_pattern.pattern)

        if self.cur.kind != pattern_to_match:
          return OUT_FALSE

        self.advance()
        return Out(True, node=self.cur_plus(-1))

      case _:
        raise Exception(f"unexpected pattern type '{type(pattern_to_match)}'")

  def try_parse_node(self):
    matched_nodes = []
    starting_idx = self.idx

    for pattern in PATTERNS:
      if (matches := self.match_pattern(pattern)).unwrap() and pattern.can_be_matched_alone:
        matched_nodes.append((matches.node, self.idx))
      
      self.idx = starting_idx
    
    return Out(len(matched_nodes) == 1, matched_nodes=matched_nodes)

  def parse_node(self):
    match len(matched_nodes := self.try_parse_node().matched_nodes):
      case 0:
        self.report('invalid syntax', self.cur.pos)
        matched_nodes.append((Node('bad'), self.idx + 1))

      case 1:
        pass
      
      case _:
        self.report('ambiguous syntax', self.cur.pos)
    
    self.idx = matched_nodes[0][1]
    return matched_nodes[0][0]

  def gen(self):
    return CompilerResult(self.errors_bag, self.parse_node())