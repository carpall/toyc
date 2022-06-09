from compiler_utils import CompilerComponent, CompilerResult, SourcePosition

class Parser(CompilerComponent):
  def __init__(self, src_info, tokens):
    super().__init__(src_info)

    self.tokens = tokens

  def gen(self):
    return CompilerResult([], BadNode(SourcePosition(self.src_info, 1, 1, 1, None, None)))