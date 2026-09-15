from html.parser import HTMLParser
from pathlib import Path
import unittest


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.by_id = {}
        self.assets = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.by_id[attrs["id"]] = attrs
        if tag == "script":
            self.assets.append(attrs.get("src", ""))
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.assets.append(attrs.get("href", ""))


class FilePickerMarkupTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Elements((Path(__file__).resolve().parents[1] / "static/index.html").read_text())

    def test_document_picker_uses_explicit_non_media_mime_types(self):
        picker = self.page.by_id["documentInput"]
        types = set(picker["accept"].split(","))
        self.assertTrue({"application/pdf", "application/zip", "text/plain"} <= types)
        self.assertTrue(all(value.startswith(("application/", "text/")) for value in types))
        self.assertNotIn("application/octet-stream", types)
        self.assertTrue(all("*" not in value for value in types))

    def test_all_files_picker_has_no_filter_and_both_support_multiple(self):
        self.assertNotIn("accept", self.page.by_id["fileInput"])
        for name in ("fileInput", "documentInput"):
            picker = self.page.by_id[name]
            self.assertEqual(picker["type"], "file")
            self.assertIn("multiple", picker)
            self.assertNotIn("capture", picker)
            self.assertTrue(picker["aria-label"])

    def test_assets_are_same_origin_and_cache_versioned_together(self):
        self.assertEqual(len(self.page.assets), 2)
        for asset in self.page.assets:
            self.assertTrue(asset.startswith("/static/"))
            self.assertTrue(asset.endswith("?v=20260915-file-picker"))


if __name__ == "__main__":
    unittest.main()
