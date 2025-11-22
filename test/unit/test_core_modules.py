import unittest
from owrx.command import CommandMapper, Option, Flag


class TestCommandMapper(unittest.TestCase):
    """Test CommandMapper for building shell commands."""

    def test_basic_mapping(self):
        """Test basic option mapping."""
        mapper = CommandMapper()
        mapper.setBase("mycommand")
        mapper.setMappings({"freq": Option("-f"), "gain": Option("-g")})

        result = mapper.map({"freq": 14074000, "gain": 40})
        self.assertIn("mycommand", result)
        self.assertIn("-f 14074000", result)
        self.assertIn("-g 40", result)

    def test_flag_mapping(self):
        """Test flag (boolean) mapping."""
        mapper = CommandMapper()
        mapper.setBase("cmd")
        mapper.setMappings({"verbose": Flag("-v")})

        # Flag present when True
        result = mapper.map({"verbose": True})
        self.assertIn("-v", result)

        # Flag absent when False
        result = mapper.map({"verbose": False})
        self.assertNotIn("-v", result)

    def test_missing_values_ignored(self):
        """Test that missing values don't appear in command."""
        mapper = CommandMapper()
        mapper.setBase("cmd")
        mapper.setMappings({"freq": Option("-f"), "gain": Option("-g")})

        result = mapper.map({"freq": 14074000})
        self.assertIn("-f 14074000", result)
        self.assertNotIn("-g", result)

    def test_chaining(self):
        """Test method chaining."""
        mapper = (
            CommandMapper()
            .setBase("cmd")
            .setMappings({"freq": Option("-f")})
        )
        result = mapper.map({"freq": 100})
        self.assertIn("cmd", result)
        self.assertIn("-f 100", result)


class TestBookmarks(unittest.TestCase):
    """Test bookmark parsing."""

    def test_bookmark_creation(self):
        """Test creating a bookmark."""
        from owrx.bookmarks import Bookmark

        bm = Bookmark({
            "name": "FT8 20m",
            "frequency": 14074000,
            "modulation": "usb"
        })
        self.assertEqual(bm.getName(), "FT8 20m")
        self.assertEqual(bm.getFrequency(), 14074000)
        self.assertEqual(bm.getModulation(), "usb")


class TestModes(unittest.TestCase):
    """Test mode definitions."""

    def test_modes_import(self):
        """Test that modes can be imported."""
        try:
            from owrx.modes import Modes
            # Just verify it imports - full functionality needs pycsdr
            self.assertTrue(True)
        except ImportError as e:
            if "pycsdr" in str(e):
                self.skipTest("pycsdr not available")
            raise


if __name__ == "__main__":
    unittest.main()
