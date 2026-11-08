"""
Vyom Office COM capability.

The API-first Office execution boundary is informed by Microsoft UFO²'s
application-specific WinCOM receiver pattern. This is an independent Vyom
implementation, not a wholesale copy of UFO's agent runtime.

The provider keeps Office automation behind Vyom's validated capability
executor. Model output is data only; arbitrary code, shell commands and
macro execution are never accepted here.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


class OfficeCOMCapability:
    """Optional native automation provider for installed Microsoft Office apps."""

    name = "office_com"
    capability_name = name
    description = (
        "Native COM automation for Microsoft Word, Excel and PowerPoint. "
        "Uses visible application instances and read-back verification."
    )

    _APP_CONFIG = {
        "word": {
            "progid": "Word.Application",
            "extensions": {".docx", ".doc", ".rtf", ".txt"},
            "collection": "Documents",
            "active_property": "ActiveDocument",
        },
        "excel": {
            "progid": "Excel.Application",
            "extensions": {".xlsx", ".xls", ".xlsm", ".csv"},
            "collection": "Workbooks",
            "active_property": "ActiveWorkbook",
        },
        "powerpoint": {
            "progid": "PowerPoint.Application",
            "extensions": {".pptx", ".ppt"},
            "collection": "Presentations",
            "active_property": "ActivePresentation",
        },
    }
    _EXTENSION_TO_APP = {
        extension: app_name
        for app_name, config in _APP_CONFIG.items()
        for extension in config["extensions"]
    }
    _CREATE_EXTENSIONS = {
        "word": {".docx"},
        "excel": {".xlsx"},
        "powerpoint": {".pptx"},
    }
    _EXCEL_RANGE = re.compile(
        r"^\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?$",
        re.IGNORECASE,
    )
    _MAX_READ_CHARS = 24000
    _MAX_EXCEL_CELLS = 2500
    _MAX_WORD_TEXT = 30000

    def __init__(
        self,
        dispatch_factory=None,
        platform_name: Optional[str] = None,
    ):
        # dispatch_factory is an injection point for deterministic tests.
        # Production COM imports stay lazy so non-Windows imports remain safe.
        self._dispatch_factory = dispatch_factory
        self._platform_name = platform_name or sys.platform
        self._applications: Dict[str, Any] = {}
        self._documents: Dict[str, Any] = {}
        self._document_paths: Dict[str, str] = {}

        self._handlers = {
            "office_open_document": self._open_document,
            "office_create_document": self._create_document,
            "office_read_document": self._read_document,
            "office_save_document": self._save_document,
            "excel_read_range": self._excel_read_range,
            "excel_write_range": self._excel_write_range,
            "word_append_text": self._word_append_text,
            "word_replace_text": self._word_replace_text,
            "word_insert_table": self._word_insert_table,
            "powerpoint_add_slide": self._powerpoint_add_slide,
        }

    def supported_actions(self) -> List[str]:
        return sorted(self._handlers)

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(action, dict):
            return self._failure("invalid_action", "Office action must be an object.")

        action_name = str(action.get("action") or "").strip().lower()
        handler = self._handlers.get(action_name)
        if handler is None:
            return self._failure(
                "unsupported_action",
                "Office capability does not support the requested operation.",
            )

        if self._platform_name != "win32":
            return self._failure(
                "platform_unsupported",
                "Native Office automation is available only on Windows.",
            )

        args = action.get("args")
        if not isinstance(args, dict):
            args = {}

        try:
            return handler(args)
        except Exception as error:
            # COM errors may contain document contents or user paths. Keep the
            # runtime result useful without echoing arbitrary exception text.
            return self._failure(
                "office_com_error",
                "The Office operation failed (" + type(error).__name__ + ").",
            )

    @staticmethod
    def _failure(stage: str, message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "stage": stage,
            "message": message,
            "verification": {"verified": False, "reason": stage},
        }

    @staticmethod
    def _success(
        message: str,
        *,
        stage: str,
        method: str,
        result: Any = None,
    ) -> Dict[str, Any]:
        payload = {
            "success": True,
            "stage": stage,
            "message": message,
            "verification": {
                "verified": True,
                "method": method,
            },
        }
        if result is not None:
            payload["result"] = result
        return payload

    def _connect(self, app_name: str):
        app_name = str(app_name or "").strip().lower()
        config = self._APP_CONFIG.get(app_name)
        if config is None:
            raise ValueError("Unsupported Office application.")

        existing = self._applications.get(app_name)
        if existing is not None:
            return existing

        if self._dispatch_factory is not None:
            application = self._dispatch_factory(config["progid"])
        else:
            try:
                from win32com.client import DispatchEx, GetActiveObject
            except Exception as error:
                raise RuntimeError("pywin32 COM support is not installed.") from error

            try:
                application = GetActiveObject(config["progid"])
            except Exception:
                application = DispatchEx(config["progid"])

        # Keep the user able to see and supervise all Office operations.
        application.Visible = True
        if app_name == "excel":
            try:
                # Prevent workbook macros from running when opened by Vyom.
                application.AutomationSecurity = 3
                application.AskToUpdateLinks = False
            except Exception:
                pass

        self._applications[app_name] = application
        return application

    @staticmethod
    def _absolute_path(value: Any) -> str:
        path = str(value or "").strip().strip('"').strip("'")
        if not path:
            raise ValueError("A document path is required.")
        if not os.path.isabs(path):
            raise ValueError("Use an absolute Windows document path.")
        return os.path.normpath(path)

    def _app_for_path(self, path: str) -> str:
        extension = os.path.splitext(path)[1].lower()
        app_name = self._EXTENSION_TO_APP.get(extension)
        if not app_name:
            raise ValueError("This Office document extension is not supported.")
        return app_name

    @staticmethod
    def _document_collection(application: Any, app_name: str):
        return getattr(
            application,
            OfficeCOMCapability._APP_CONFIG[app_name]["collection"],
        )

    def _open_document(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = self._absolute_path(args.get("path") or args.get("target"))
        if not os.path.isfile(path):
            return self._failure("document_not_found", "The requested document does not exist.")

        app_name = self._app_for_path(path)
        application = self._connect(app_name)
        collection = self._document_collection(application, app_name)
        read_only = bool(args.get("read_only", True))

        if app_name == "excel":
            document = collection.Open(
                path,
                UpdateLinks=0,
                ReadOnly=read_only,
                AddToMru=False,
            )
        elif app_name == "word":
            document = collection.Open(
                FileName=path,
                ReadOnly=read_only,
                AddToRecentFiles=False,
            )
        else:
            document = collection.Open(
                FileName=path,
                ReadOnly=read_only,
                WithWindow=True,
            )

        self._documents[app_name] = document
        self._document_paths[app_name] = path
        document_name = str(getattr(document, "Name", os.path.basename(path)))
        if not document_name:
            return self._failure("document_identity_missing", "Office opened the file but did not expose its identity.")

        return self._success(
            "Opened " + document_name + " in " + app_name + ".",
            stage="office_document_opened",
            method="COM_document_identity_readback",
            result={"application": app_name, "path": path, "read_only": read_only},
        )

    def _create_document(self, args: Dict[str, Any]) -> Dict[str, Any]:
        app_name = str(args.get("application") or "").strip().lower()
        if app_name not in self._APP_CONFIG:
            return self._failure(
                "invalid_office_application",
                "Choose Word, Excel or PowerPoint for the new document.",
            )

        path = self._absolute_path(args.get("path"))
        extension = os.path.splitext(path)[1].lower()
        if extension not in self._CREATE_EXTENSIONS[app_name]:
            return self._failure(
                "unsupported_create_extension",
                "New files must use .docx, .xlsx or .pptx for the selected application.",
            )
        if os.path.exists(path):
            return self._failure(
                "target_exists",
                "The destination already exists. Vyom will not overwrite it during document creation.",
            )
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            return self._failure("destination_missing", "The destination folder does not exist.")

        application = self._connect(app_name)
        collection = self._document_collection(application, app_name)
        document = collection.Add()

        if app_name == "word":
            document.SaveAs2(path, FileFormat=16)
        elif app_name == "excel":
            document.SaveAs(path, FileFormat=51)
        else:
            document.SaveAs(path, FileFormat=24)

        if not os.path.isfile(path):
            return self._failure(
                "create_verification_failed",
                "Office returned from Save As, but the new file was not found.",
            )

        self._documents[app_name] = document
        self._document_paths[app_name] = path
        return self._success(
            "Created a new " + app_name + " document.",
            stage="office_document_created",
            method="file_exists_after_office_save_as",
            result={"application": app_name, "path": path},
        )

    def _current_document(self, app_name: str):
        app_name = str(app_name or "").strip().lower()
        if app_name not in self._APP_CONFIG:
            raise ValueError("Choose Word, Excel or PowerPoint.")

        document = self._documents.get(app_name)
        if document is not None:
            return document

        application = self._connect(app_name)
        active_property = self._APP_CONFIG[app_name]["active_property"]
        document = getattr(application, active_property, None)
        if document is None:
            raise LookupError("No active Office document is available.")
        self._documents[app_name] = document
        return document

    @staticmethod
    def _plain(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, tuple):
            return [OfficeCOMCapability._plain(item) for item in value]
        if isinstance(value, list):
            return [OfficeCOMCapability._plain(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _read_content(self, app_name: str, document: Any) -> Any:
        if app_name == "word":
            return str(document.Content.Text or "")[:self._MAX_READ_CHARS]

        if app_name == "excel":
            sheets = []
            worksheet_collection = document.Worksheets
            count = min(int(worksheet_collection.Count), 8)
            for index in range(1, count + 1):
                sheet = worksheet_collection(index)
                used = sheet.UsedRange
                values = self._plain(used.Value)
                sheets.append({
                    "name": str(sheet.Name),
                    "values": values,
                })
            return sheets

        slides = []
        slide_collection = document.Slides
        count = min(int(slide_collection.Count), 40)
        for index in range(1, count + 1):
            slide = slide_collection(index)
            items = []
            shapes = slide.Shapes
            for shape_index in range(1, min(int(shapes.Count), 80) + 1):
                shape = shapes(shape_index)
                try:
                    if bool(shape.HasTextFrame) and bool(shape.TextFrame.HasText):
                        text_value = str(shape.TextFrame.TextRange.Text or "").strip()
                        if text_value:
                            items.append(text_value[:2000])
                except Exception:
                    continue
            slides.append({"slide": index, "text": items})
        return slides

    def _read_document(self, args: Dict[str, Any]) -> Dict[str, Any]:
        app_name = str(args.get("application") or "").strip().lower()
        if not app_name and args.get("path"):
            app_name = self._app_for_path(self._absolute_path(args["path"]))
            opened = self._open_document({"path": args["path"], "read_only": True})
            if not opened.get("success"):
                return opened

        document = self._current_document(app_name)
        content = self._read_content(app_name, document)
        return self._success(
            "Read the active " + app_name + " document.",
            stage="office_document_read",
            method="COM_document_content_readback",
            result={"application": app_name, "content": content},
        )

    def _excel_sheet(self, args: Dict[str, Any]):
        document = self._current_document("excel")
        sheet_name = args.get("sheet_name") or 1
        return document.Worksheets(sheet_name)

    def _excel_range(self, args: Dict[str, Any]):
        address = str(args.get("range_address") or "").strip()
        if not self._EXCEL_RANGE.fullmatch(address):
            raise ValueError("Use a bounded A1-style range such as A1 or A1:C10.")
        return self._excel_sheet(args).Range(address.upper())

    def _excel_read_range(self, args: Dict[str, Any]) -> Dict[str, Any]:
        address = str(args.get("range_address") or "").strip()
        cell_range = self._excel_range(args)
        values = self._plain(cell_range.Value)
        if isinstance(values, list):
            if len(values) > self._MAX_EXCEL_CELLS:
                return self._failure("range_too_large", "The requested range is too large.")
        return self._success(
            "Read the requested Excel range.",
            stage="excel_range_read",
            method="COM_range_value_readback",
            result={
                "sheet_name": str(args.get("sheet_name") or ""),
                "range_address": address.upper(),
                "values": values,
            },
        )

    @classmethod
    def _validate_values(cls, raw: Any) -> Tuple[Tuple[Any, ...], ...]:
        if not isinstance(raw, list) or not raw or not all(isinstance(row, list) for row in raw):
            raise ValueError("Excel values must be a non-empty two-dimensional array.")
        row_count = len(raw)
        col_count = max((len(row) for row in raw), default=0)
        if col_count == 0 or row_count * col_count > cls._MAX_EXCEL_CELLS:
            raise ValueError("The Excel write is empty or exceeds the cell limit.")

        rows = []
        for row in raw:
            if len(row) != col_count:
                raise ValueError("Every Excel row must have the same number of values.")
            values = []
            for value in row:
                if isinstance(value, str) and len(value) > 4096:
                    raise ValueError("An Excel cell value exceeds the text limit.")
                if not (value is None or isinstance(value, (str, int, float, bool))):
                    raise ValueError("Excel values must be plain text, numbers, booleans or null.")
                values.append(value)
            rows.append(tuple(values))
        return tuple(rows)

    def _excel_write_range(self, args: Dict[str, Any]) -> Dict[str, Any]:
        values = self._validate_values(args.get("values"))
        cell_range = self._excel_range(args)
        document = self._current_document("excel")
        if bool(getattr(document, "ReadOnly", False)):
            return self._failure("document_read_only", "The active workbook is read-only. Reopen it with read_only=false before editing.")

        cell_range.Value = values
        read_back = self._plain(cell_range.Value)
        expected = self._plain(values)
        if read_back != expected:
            return self._failure(
                "excel_write_verification_failed",
                "Excel did not return the values that Vyom wrote.",
            )
        return self._success(
            "Updated the requested Excel cells.",
            stage="excel_range_written",
            method="COM_range_readback_match",
            result={"range_address": str(args.get("range_address") or "").upper(), "values": read_back},
        )

    def _word_document_for_edit(self):
        document = self._current_document("word")
        if bool(getattr(document, "ReadOnly", False)):
            raise PermissionError("The active Word document is read-only.")
        return document

    def _word_append_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        text = str(args.get("text") or "")
        if not text or len(text) > self._MAX_WORD_TEXT:
            return self._failure("invalid_word_text", "Provide non-empty text within the Word text limit.")
        document = self._word_document_for_edit()
        document.Content.InsertAfter(text)
        read_back = str(document.Content.Text or "")
        if text not in read_back:
            return self._failure("word_append_verification_failed", "The appended text was not found in Word after the action.")
        return self._success(
            "Appended text to the Word document.",
            stage="word_text_appended",
            method="Word_Content_text_readback",
            result={"characters_appended": len(text)},
        )

    def _word_replace_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        find_text = str(args.get("find_text") or "")
        replace_text = str(args.get("replace_text") or "")
        if not find_text or len(find_text) > 2000 or len(replace_text) > self._MAX_WORD_TEXT:
            return self._failure("invalid_word_replace", "Provide a search phrase and replacement within the supported limits.")
        document = self._word_document_for_edit()
        finder = document.Content.Find
        found = bool(finder.Execute(
            FindText=find_text,
            ReplaceWith=replace_text,
            Replace=2,
        ))
        read_back = str(document.Content.Text or "")
        if not found or find_text in read_back:
            return self._failure("word_replace_verification_failed", "Word could not verify the requested replacement.")
        return self._success(
            "Replaced the requested text in Word.",
            stage="word_text_replaced",
            method="Word_Find_Replace_readback",
            result={"replaced_text": replace_text},
        )

    def _word_insert_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rows = args.get("rows")
        columns = args.get("columns")
        if not isinstance(rows, int) or isinstance(rows, bool) or not 1 <= rows <= 50:
            return self._failure("invalid_table_size", "Word tables must contain between 1 and 50 rows.")
        if not isinstance(columns, int) or isinstance(columns, bool) or not 1 <= columns <= 20:
            return self._failure("invalid_table_size", "Word tables must contain between 1 and 20 columns.")

        document = self._word_document_for_edit()
        before = int(document.Tables.Count)
        insertion_range = document.Content
        insertion_range.Collapse(0)
        insertion_range.InsertParagraphAfter()
        document.Tables.Add(insertion_range, rows, columns)
        after = int(document.Tables.Count)
        if after != before + 1:
            return self._failure("word_table_verification_failed", "Word did not report the new table.")
        return self._success(
            "Inserted a table in the Word document.",
            stage="word_table_inserted",
            method="Word_table_count_readback",
            result={"rows": rows, "columns": columns, "table_count": after},
        )

    def _powerpoint_add_slide(self, args: Dict[str, Any]) -> Dict[str, Any]:
        title = str(args.get("title") or "").strip()
        body = str(args.get("body") or "").strip()
        if not title or len(title) > 500 or len(body) > 5000:
            return self._failure("invalid_slide_text", "A slide title is required; title/body text exceeds the supported limit.")

        document = self._current_document("powerpoint")
        if bool(getattr(document, "ReadOnly", False)):
            return self._failure("document_read_only", "The active presentation is read-only. Reopen it with read_only=false before editing.")

        slides = document.Slides
        before = int(slides.Count)
        layout = args.get("layout", 2)
        if not isinstance(layout, int) or isinstance(layout, bool) or not 1 <= layout <= 12:
            return self._failure("invalid_slide_layout", "Choose a PowerPoint layout number from 1 to 12.")

        slide = slides.Add(before + 1, layout)
        try:
            slide.Shapes.Title.TextFrame.TextRange.Text = title
        except Exception:
            return self._failure("slide_title_unavailable", "The selected slide layout has no title placeholder.")
        if body:
            try:
                slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = body
            except Exception:
                return self._failure("slide_body_unavailable", "The selected slide layout has no body placeholder.")

        after = int(slides.Count)
        title_read_back = str(slide.Shapes.Title.TextFrame.TextRange.Text or "")
        if after != before + 1 or title_read_back != title:
            return self._failure("slide_verification_failed", "PowerPoint did not verify the new slide and title.")
        return self._success(
            "Added a slide to the PowerPoint presentation.",
            stage="powerpoint_slide_added",
            method="PowerPoint_slide_count_and_title_readback",
            result={"slide_index": after, "title": title},
        )

    def _save_document(self, args: Dict[str, Any]) -> Dict[str, Any]:
        app_name = str(args.get("application") or "").strip().lower()
        if not app_name and args.get("path"):
            app_name = self._app_for_path(self._absolute_path(args["path"]))
        document = self._current_document(app_name)

        requested_path = args.get("path")
        if requested_path:
            path = self._absolute_path(requested_path)
            if os.path.exists(path):
                current_path = self._document_paths.get(app_name, "")
                same_path = bool(current_path) and os.path.normcase(path) == os.path.normcase(current_path)
                if not same_path:
                    return self._failure(
                        "target_exists",
                        "The save destination already exists. Vyom will not overwrite a different file.",
                    )
                document.Save()
            else:
                extension = os.path.splitext(path)[1].lower()
                if extension not in self._CREATE_EXTENSIONS[app_name]:
                    return self._failure("unsupported_save_extension", "Save As supports .docx, .xlsx or .pptx.")
                parent = os.path.dirname(path)
                if not os.path.isdir(parent):
                    return self._failure("destination_missing", "The destination folder does not exist.")
                if app_name == "word":
                    document.SaveAs2(path, FileFormat=16)
                elif app_name == "excel":
                    document.SaveAs(path, FileFormat=51)
                else:
                    document.SaveAs(path, FileFormat=24)
                self._document_paths[app_name] = path
        else:
            document.Save()

        saved_path = self._document_paths.get(app_name, "")
        if saved_path and not os.path.isfile(saved_path):
            return self._failure("save_verification_failed", "The saved Office file could not be found.")
        return self._success(
            "Saved the active " + app_name + " document.",
            stage="office_document_saved",
            method="COM_save_and_path_readback",
            result={"application": app_name, "path": saved_path or None},
        )
