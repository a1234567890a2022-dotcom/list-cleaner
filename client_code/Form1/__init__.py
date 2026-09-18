from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.media


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    # Allow several files at once (you can also tick "multiple" in the Properties panel)
    self.file_loader_1.multiple = True

  @handle("button_1_click", "click")
  def button_1_click_click(self, **event_args):
    """Send uploaded files to the server and download the cleaned ZIP."""
    files = self.file_loader_1.files
    if not files:
      alert("Please upload at least one file first.")
      return

    original_text = self.button_1.text
    self.button_1.enabled = False
    self.button_1.text = "Processing..."

    try:
      result = anvil.server.call('process_files', files)

      if result['zip'] is not None:
        anvil.media.download(result['zip'])
        self.file_loader_1.clear()

      if result['messages']:
        alert("\n".join(result['messages']), title="Notes")

    except Exception as e:
      alert(f"Something went wrong: {e}")

    finally:
      self.button_1.enabled = True
      self.button_1.text = original_text
