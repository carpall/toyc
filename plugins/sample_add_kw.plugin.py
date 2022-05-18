from plugin import Plugin

class MyPlugin(Plugin):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    
    self.lexer_module.KEYWORDS.append('my_keyword')
  
  def on_error_report(self, component, method, error):
    print(f'reporting error from {component}.{method}: {error.msg}')