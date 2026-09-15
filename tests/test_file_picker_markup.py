from html.parser import HTMLParser
from pathlib import Path
import unittest


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.by_id = {}
        self.tags_by_id = {}
        self.file_inputs = []
        self.assets = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.by_id[attrs["id"]] = attrs
            self.tags_by_id[attrs["id"]] = tag
        if tag == "input" and attrs.get("type") == "file":
            self.file_inputs.append(attrs)
        if tag == "script":
            self.assets.append(attrs.get("src", ""))
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.assets.append(attrs.get("href", ""))


class FilePickerMarkupTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Elements((Path(__file__).resolve().parents[1] / "static/index.html").read_text())

    def test_only_one_unrestricted_picker_is_rendered(self):
        self.assertEqual(len(self.page.file_inputs), 1)
        self.assertNotIn("accept", self.page.by_id["fileInput"])
        for name in ("documentInput", "fileType", "chooseFileBtn"):
            self.assertNotIn(name, self.page.by_id)

    def test_picker_supports_multiple_without_capture(self):
        picker = self.page.by_id["fileInput"]
        self.assertEqual(picker["type"], "file")
        self.assertIn("multiple", picker)
        self.assertNotIn("capture", picker)
        self.assertEqual(picker["aria-label"], "选择文件")
        self.assertNotIn("hidden", picker)
        self.assertNotIn("tabindex", picker)

    def test_original_drop_zone_is_a_native_label(self):
        self.assertEqual(self.page.tags_by_id["dropZone"], "label")

    def test_assets_are_same_origin_and_cache_versioned_together(self):
        self.assertEqual(len(self.page.assets), 2)
        for asset in self.page.assets:
            self.assertTrue(asset.startswith("/static/"))
            self.assertTrue(asset.endswith("?v=20260915-universal-picker"))


if __name__ == "__main__":
    unittest.main()
