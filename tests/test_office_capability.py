import os
import tempfile
import unittest

from windows_agent.office_capability import OfficeCOMCapability


class Counter:
    def __init__(self, value=0):
        self.Count = value


class FakeExcelRange:
    def __init__(self, value=None, rows=2, columns=2):
        self._value = value
        self.Rows = Counter(rows)
        self.Columns = Counter(columns)

    @property
    def Value(self):
        return self._value

    @Value.setter
    def Value(self, value):
        self._value = value


class FakeSheet:
    def __init__(self):
        self.Name = "Sheet1"
        self._range = FakeExcelRange()

    def Range(self, address):
        return self._range


class FakeWorksheets:
    def __init__(self):
        self.sheet = FakeSheet()
        self.Count = 1

    def __call__(self, name):
        return self.sheet


class FakeWorkbook:
    def __init__(self):
        self.Name = "Book1.xlsx"
        self.ReadOnly = False
        self.Worksheets = FakeWorksheets()


class FakeCollection:
    def __init__(self, document):
        self.document = document

    def Add(self):
        return self.document

    def Open(self, *args, **kwargs):
        return self.document


class FakeExcelApp:
    def __init__(self, workbook=None):
        self.Visible = False
        self.Workbooks = FakeCollection(workbook or FakeWorkbook())
        self.AutomationSecurity = 0


class FakeTextRange:
    def __init__(self, owner):
        self.owner = owner

    def InsertAfter(self, value):
        self.owner.Text += value

    def Collapse(self, direction):
        self.direction = direction

    def InsertParagraphAfter(self):
        self.owner.Text += "\n"

    @property
    def Find(self):
        return FakeFind(self.owner)


class FakeFind:
    def __init__(self, owner):
        self.owner = owner

    def Execute(self, FindText, ReplaceWith, Replace):
        if FindText not in self.owner.Text:
            return False
        self.owner.Text = self.owner.Text.replace(FindText, ReplaceWith)
        return True


class FakeTables:
    def __init__(self):
        self.Count = 0
        self.last_dimensions = None

    def Add(self, insertion_range, rows, columns):
        self.Count += 1
        self.last_dimensions = (rows, columns)
        return object()


class FakeWordDocument:
    def __init__(self):
        self.Name = "Document1.docx"
        self.ReadOnly = False
        self._content = ""
        self.Content = FakeTextRange(self)
        self.Tables = FakeTables()

    @property
    def ContentText(self):
        return self._content

    @property
    def Text(self):
        return self._content

    @Text.setter
    def Text(self, value):
        self._content = value


# Make the Word content object expose COM's .Text property while keeping
# document.Content.Text and document.Content.InsertAfter on the same object.
FakeTextRange.Text = property(
    lambda self: self.owner._content,
    lambda self, value: setattr(self.owner, "_content", value),
)


class FakeWordApp:
    def __init__(self, document=None):
        self.Visible = False
        self.Documents = FakeCollection(document or FakeWordDocument())


class FakeSlideTextRange:
    def __init__(self):
        self.Text = ""


class FakeSlideTextFrame:
    def __init__(self):
        self.TextRange = FakeSlideTextRange()


class FakeShape:
    def __init__(self):
        self.TextFrame = FakeSlideTextFrame()
        self.HasTextFrame = True


class FakeShapes:
    def __init__(self):
        self.Title = FakeShape()
        self._body = FakeShape()

    def Placeholders(self, index):
        return self._body


class FakeSlide:
    def __init__(self):
        self.Shapes = FakeShapes()


class FakeSlides:
    def __init__(self):
        self.Count = 0
        self.last_slide = None

    def Add(self, index, layout):
        self.Count += 1
        self.last_slide = FakeSlide()
        return self.last_slide


class FakePresentation:
    def __init__(self):
        self.ReadOnly = False
        self.Slides = FakeSlides()


class FakePresentations(FakeCollection):
    pass


class FakePowerPointApp:
    def __init__(self, presentation=None):
        self.Visible = False
        self.Presentations = FakePresentations(presentation or FakePresentation())


class OfficeCOMCapabilityTests(unittest.TestCase):

    def test_supported_actions_advertise_office_and_document_operations(self):
        provider = OfficeCOMCapability(platform_name="win32")
        actions = set(provider.supported_actions())
        self.assertIn("office_open_document", actions)
        self.assertIn("excel_write_range", actions)
        self.assertIn("word_insert_table", actions)
        self.assertIn("powerpoint_add_slide", actions)

    def test_non_windows_fails_closed_without_loading_com(self):
        provider = OfficeCOMCapability(platform_name="linux")
        result = provider.execute({"action": "office_open_document", "args": {"path": "/tmp/a.xlsx"}})
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "platform_unsupported")

    def test_create_document_saves_new_xlsx_and_refuses_overwrite(self):
        workbook = FakeWorkbook()

        class SaveableWorkbook(FakeWorkbook):
            def SaveAs(self, path, FileFormat):
                with open(path, "wb") as handle:
                    handle.write(b"workbook")

        saveable = SaveableWorkbook()
        app = FakeExcelApp(saveable)
        provider = OfficeCOMCapability(
            dispatch_factory=lambda progid: app,
            platform_name="win32",
        )
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "research.xlsx")
            result = provider.execute({
                "action": "office_create_document",
                "args": {"application": "excel", "path": path},
            })
            self.assertTrue(result["success"], result)
            self.assertTrue(os.path.isfile(path))
            self.assertTrue(app.Visible)
            second = provider.execute({
                "action": "office_create_document",
                "args": {"application": "excel", "path": path},
            })
            self.assertFalse(second["success"])
            self.assertEqual(second["stage"], "target_exists")

    def test_excel_write_range_requires_read_write_document_and_verifies_readback(self):
        app = FakeExcelApp()
        provider = OfficeCOMCapability(
            dispatch_factory=lambda progid: app,
            platform_name="win32",
        )
        provider._applications["excel"] = app
        provider._documents["excel"] = app.Workbooks.document

        result = provider.execute({
            "action": "excel_write_range",
            "args": {
                "range_address": "A1:B2",
                "sheet_name": "Sheet1",
                "values": [[1, 2], [3, 4]],
            },
        })
        self.assertTrue(result["success"], result)
        self.assertTrue(result["verification"]["verified"])
        self.assertEqual(
            result["result"]["values"],
            [[1, 2], [3, 4]],
        )

    def test_excel_rejects_oversized_or_ragged_values(self):
        provider = OfficeCOMCapability(platform_name="win32")
        with self.assertRaises(ValueError):
            provider._validate_values([[1, 2], [3]])
        with self.assertRaises(ValueError):
            provider._validate_values([[1] * 51 for _ in range(51)])

    def test_word_append_and_replace_are_verified_by_readback(self):
        app = FakeWordApp()
        provider = OfficeCOMCapability(
            dispatch_factory=lambda progid: app,
            platform_name="win32",
        )
        provider._applications["word"] = app
        provider._documents["word"] = app.Documents.document

        appended = provider.execute({
            "action": "word_append_text",
            "args": {"text": "Vyom report"},
        })
        self.assertTrue(appended["success"], appended)

        replaced = provider.execute({
            "action": "word_replace_text",
            "args": {"find_text": "Vyom", "replace_text": "Vyom AI"},
        })
        self.assertTrue(replaced["success"], replaced)
        self.assertIn("Vyom AI report", app.Documents.document.Content.Text)

    def test_word_table_dimensions_are_bounded_and_verified(self):
        app = FakeWordApp()
        provider = OfficeCOMCapability(
            dispatch_factory=lambda progid: app,
            platform_name="win32",
        )
        provider._applications["word"] = app
        provider._documents["word"] = app.Documents.document

        result = provider.execute({
            "action": "word_insert_table",
            "args": {"rows": 3, "columns": 4},
        })
        self.assertTrue(result["success"], result)
        self.assertEqual(app.Documents.document.Tables.last_dimensions, (3, 4))

    def test_powerpoint_add_slide_verifies_slide_count_and_title(self):
        presentation = FakePresentation()
        app = FakePowerPointApp(presentation)
        provider = OfficeCOMCapability(
            dispatch_factory=lambda progid: app,
            platform_name="win32",
        )
        provider._applications["powerpoint"] = app
        provider._documents["powerpoint"] = presentation

        result = provider.execute({
            "action": "powerpoint_add_slide",
            "args": {"title": "Vyom Research", "body": "Findings"},
        })
        self.assertTrue(result["success"], result)
        self.assertEqual(presentation.Slides.Count, 1)
        self.assertEqual(
            presentation.Slides.last_slide.Shapes.Title.TextFrame.TextRange.Text,
            "Vyom Research",
        )
        self.assertEqual(
            presentation.Slides.last_slide.Shapes.Placeholders(2).TextFrame.TextRange.Text,
            "Findings",
        )

    def test_excel_range_syntax_is_bounded(self):
        provider = OfficeCOMCapability(platform_name="win32")
        self.assertIsNotNone(provider._EXCEL_RANGE.fullmatch("A1:C20"))
        self.assertIsNone(provider._EXCEL_RANGE.fullmatch("A1;DROP TABLE"))
        self.assertIsNone(provider._EXCEL_RANGE.fullmatch("A1:ZZZZ999999"))


if __name__ == "__main__":
    unittest.main()
