from ._anvil_designer import Form1Template
from anvil import *
import anvil.media
import anvil.server


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.file_loader_1.multiple = True
    self.file_loader_1.file_types = ".csv,.xlsx"
    self.file_loader_1.show_state = True
    self.selection_label.text = "No files selected"
    self.status_label.text = "Ready. Choose a download step after uploading."

  def _download_step(self, server_function, button, progress_message):
    files = self.file_loader_1.files
    if not files:
      self.status_label.text = "Choose at least one CSV or XLSX file first."
      alert("Please choose at least one CSV or XLSX file first.")
      return

    original_text = button.text
    button.enabled = False
    button.text = "Preparing downloads..."
    self.status_label.text = progress_message

    try:
      result = anvil.server.call(server_function, files)
      if not result["ok"]:
        self.status_label.text = result["message"]
        if result["messages"]:
          alert("\n".join(result["messages"]), title="Processing notes")
        return

      for download in result["downloads"]:
        anvil.media.download(download)
      self.status_label.text = result["message"]
      if result["messages"]:
        alert("\n".join(result["messages"]), title="Processing complete")
    finally:
      button.enabled = True
      button.text = original_text

  @handle("columns_button", "click")
  def columns_button_click(self, **event_args):
    """Run the first stage and download the selected-column CSV files."""
    self._download_step(
      "process_columns_files",
      self.columns_button,
      "Selecting and ordering the requested columns...",
    )

  @handle("phones_button", "click")
  def phones_button_click(self, **event_args):
    """Run the second stage and download the Mobile/Wireless CSV files."""
    self._download_step(
      "process_mobile_files",
      self.phones_button,
      "Filtering phone columns to Mobile and Wireless only...",
    )

  @handle("file_loader_1_change", "change")
  def file_loader_1_change(self, **event_args):
    count = len(self.file_loader_1.files)
    self.selection_label.text = (
      f"{count} file{'s' if count != 1 else ''} ready for either step"
      if count else "No files selected"
    )

  @handle("clear_button", "click")
  def clear_button_click(self, **event_args):
    self.file_loader_1.clear()
    self.selection_label.text = "No files selected"
    self.status_label.text = "Ready. Choose a download step after uploading."
