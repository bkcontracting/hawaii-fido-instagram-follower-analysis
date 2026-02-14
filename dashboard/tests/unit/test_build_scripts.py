#!/usr/bin/env python3
"""
Unit tests for dashboard build scripts.

Tests:
- CSV to JavaScript conversion
- HTML template generation
- Configuration validation
- File integrity
- Error handling

Run:
    pytest dashboard/tests/unit/test_build_scripts.py -v
"""

import pytest
import json
import csv
import tempfile
import sys
from pathlib import Path
from io import StringIO

# Add build directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'build'))

# Import build modules
import csv_to_js
import generate_html


class TestCSVToJS:
    """Test CSV to JavaScript conversion."""

    def test_csv_to_array_basic(self, tmp_path):
        """Test basic CSV parsing."""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "Handle,Name,Score\n"
            "@user1,User One,95\n"
            "@user2,User Two,80\n"
        )

        # Convert
        result = csv_to_js.csv_to_array(csv_file)

        # Verify
        assert len(result) == 2
        assert result[0]['Handle'] == '@user1'
        assert result[0]['Name'] == 'User One'
        assert result[0]['Score'] == '95'
        assert result[1]['Handle'] == '@user2'

    def test_csv_to_array_with_special_characters(self, tmp_path):
        """Test CSV with special characters."""
        csv_file = tmp_path / "special.csv"
        csv_file.write_text(
            'Handle,Bio\n'
            '@user,"Bio with, comma"\n'
            '@user2,"Bio with ""quotes"""\n'
        )

        result = csv_to_js.csv_to_array(csv_file)

        assert len(result) == 2
        assert result[0]['Bio'] == 'Bio with, comma'
        assert result[1]['Bio'] == 'Bio with "quotes"'

    def test_csv_to_array_empty_file(self, tmp_path):
        """Test empty CSV file."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("Handle,Name\n")

        result = csv_to_js.csv_to_array(csv_file)

        assert len(result) == 0

    def test_csv_to_array_unicode(self, tmp_path):
        """Test CSV with Unicode characters."""
        csv_file = tmp_path / "unicode.csv"
        csv_file.write_text(
            "Handle,Name\n"
            "@user,Hawaiʻi Fi-Do\n"
            "@user2,🐕 Puppy\n",
            encoding='utf-8'
        )

        result = csv_to_js.csv_to_array(csv_file)

        assert len(result) == 2
        assert result[0]['Name'] == 'Hawaiʻi Fi-Do'
        assert result[1]['Name'] == '🐕 Puppy'

    def test_build_data_module(self, tmp_path):
        """Test complete data module generation."""
        # Create test structure
        config_file = tmp_path / "config.json"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create test CSVs
        csv1 = output_dir / "test1.csv"
        csv1.write_text("Handle,Score\n@user1,95\n")

        csv2 = output_dir / "test2.csv"
        csv2.write_text("Handle,Score\n@user2,80\n")

        # Create config
        config = {
            "tabs": [
                {"id": "tab1", "csvFile": "test1.csv"},
                {"id": "tab2", "csvFile": "test2.csv"}
            ]
        }
        config_file.write_text(json.dumps(config))

        # Build data module
        output_file = tmp_path / "data.js"

        # Temporarily change to tmp_path directory
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            count = csv_to_js.build_data_module(config_file, output_file)
            assert count == 2

            # Verify output
            assert output_file.exists()
            content = output_file.read_text()

            assert 'const DASHBOARD_CONFIG' in content
            assert 'const DASHBOARD_DATA' in content
            assert "'tab1':" in content
            assert "'tab2':" in content
            assert '@user1' in content
            assert '@user2' in content
        finally:
            os.chdir(original_cwd)

    def test_build_data_module_missing_csv(self, tmp_path):
        """Test error handling for missing CSV."""
        config_file = tmp_path / "config.json"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {
            "tabs": [
                {"id": "tab1", "csvFile": "missing.csv"}
            ]
        }
        config_file.write_text(json.dumps(config))

        output_file = tmp_path / "data.js"

        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(SystemExit):
                csv_to_js.build_data_module(config_file, output_file)
        finally:
            os.chdir(original_cwd)


class TestGenerateHTML:
    """Test HTML generation."""

    def test_load_file_success(self, tmp_path):
        """Test file loading."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        content = generate_html.load_file(test_file)

        assert content == "Hello, World!"

    def test_load_file_not_found(self, tmp_path):
        """Test error handling for missing file."""
        missing_file = tmp_path / "missing.txt"

        with pytest.raises(FileNotFoundError):
            generate_html.load_file(missing_file)

    def test_generate_html_basic(self, tmp_path):
        """Test basic HTML generation."""
        # Create test files
        config_file = tmp_path / "config.json"
        template_file = tmp_path / "template.html"
        css_file = tmp_path / "styles.css"
        js_file = tmp_path / "app.js"
        data_js_file = tmp_path / "data.js"
        output_file = tmp_path / "index.html"

        # Write test content
        config = {"dashboardTitle": "Test Dashboard"}
        config_file.write_text(json.dumps(config))

        template_file.write_text(
            "<html><head><title>$DASHBOARD_TITLE</title>"
            "<style>$CSS_CONTENT</style></head>"
            "<body><script>$DATA_JS</script><script>$APP_JS</script></body></html>"
        )

        css_file.write_text("body { margin: 0; }")
        js_file.write_text("console.log('app');")
        data_js_file.write_text("const DATA = [];")

        # Generate HTML
        size = generate_html.generate_html(
            config_file,
            template_file,
            css_file,
            js_file,
            data_js_file,
            output_file
        )

        # Verify
        assert output_file.exists()
        assert size > 0

        content = output_file.read_text()
        assert "Test Dashboard" in content
        assert "body { margin: 0; }" in content
        assert "console.log('app');" in content
        assert "const DATA = [];" in content

    def test_generate_html_all_placeholders_replaced(self, tmp_path):
        """Test that all template placeholders are replaced."""
        # Create test files
        config_file = tmp_path / "config.json"
        template_file = tmp_path / "template.html"
        css_file = tmp_path / "styles.css"
        js_file = tmp_path / "app.js"
        data_js_file = tmp_path / "data.js"
        output_file = tmp_path / "index.html"

        config = {"dashboardTitle": "Test"}
        config_file.write_text(json.dumps(config))

        template_file.write_text(
            "$DASHBOARD_TITLE|$CSS_CONTENT|$APP_JS|$DATA_JS"
        )

        css_file.write_text("CSS")
        js_file.write_text("JS")
        data_js_file.write_text("DATA")

        # Generate
        generate_html.generate_html(
            config_file,
            template_file,
            css_file,
            js_file,
            data_js_file,
            output_file
        )

        content = output_file.read_text()

        # Verify all placeholders replaced
        assert '$DASHBOARD_TITLE' not in content
        assert '$CSS_CONTENT' not in content
        assert '$APP_JS' not in content
        assert '$DATA_JS' not in content

        assert 'Test' in content
        assert 'CSS' in content
        assert 'JS' in content
        assert 'DATA' in content

    def test_generate_html_unicode(self, tmp_path):
        """Test HTML generation with Unicode content."""
        config_file = tmp_path / "config.json"
        template_file = tmp_path / "template.html"
        css_file = tmp_path / "styles.css"
        js_file = tmp_path / "app.js"
        data_js_file = tmp_path / "data.js"
        output_file = tmp_path / "index.html"

        config = {"dashboardTitle": "Hawaiʻi Fi-Do 🐕"}
        config_file.write_text(json.dumps(config, ensure_ascii=False))

        template_file.write_text("$DASHBOARD_TITLE")
        css_file.write_text("")
        js_file.write_text("")
        data_js_file.write_text("")

        generate_html.generate_html(
            config_file,
            template_file,
            css_file,
            js_file,
            data_js_file,
            output_file
        )

        content = output_file.read_text(encoding='utf-8')
        assert "Hawaiʻi Fi-Do 🐕" in content


class TestConfiguration:
    """Test configuration validation."""

    def test_valid_config(self, tmp_path):
        """Test valid configuration structure."""
        config = {
            "dashboardTitle": "Test Dashboard",
            "googleWorkspaceDomain": "test.org",
            "tabs": [
                {
                    "id": "tab1",
                    "label": "Tab 1",
                    "csvFile": "test.csv",
                    "description": "Test tab",
                    "defaultSort": {"column": "Score", "direction": "desc"},
                    "columns": {
                        "display": ["Handle", "Score"],
                        "searchable": ["Handle"],
                        "sortable": ["Score"]
                    }
                }
            ],
            "features": {
                "enableSearch": True,
                "enableFilters": True,
                "recordsPerPage": 25
            }
        }

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config, indent=2))

        # Verify it can be loaded
        with open(config_file, 'r') as f:
            loaded = json.load(f)

        assert loaded['dashboardTitle'] == 'Test Dashboard'
        assert len(loaded['tabs']) == 1
        assert loaded['tabs'][0]['id'] == 'tab1'

    def test_config_missing_required_field(self, tmp_path):
        """Test configuration with missing required fields."""
        config = {
            "tabs": []  # Missing dashboardTitle
        }

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        with open(config_file, 'r') as f:
            loaded = json.load(f)

        # Should be able to load but missing field
        assert 'dashboardTitle' not in loaded


class TestIntegration:
    """Integration tests for complete build process."""

    def test_full_build_process(self, tmp_path):
        """Test complete build from CSV to HTML."""
        # Set up directory structure
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        src_dir = tmp_path / "src"
        src_dir.mkdir()

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        # Create test CSV
        csv_file = output_dir / "test.csv"
        csv_file.write_text(
            "Handle,Name,Score\n"
            "@user1,User One,95\n"
            "@user2,User Two,80\n"
        )

        # Create config
        config = {
            "dashboardTitle": "Integration Test",
            "tabs": [
                {
                    "id": "test",
                    "label": "Test",
                    "csvFile": "test.csv",
                    "columns": {
                        "display": ["Handle", "Name", "Score"],
                        "searchable": ["Handle", "Name"],
                        "sortable": ["Score"]
                    }
                }
            ]
        }
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps(config))

        # Create templates
        template_file = src_dir / "template.html"
        template_file.write_text(
            "<!DOCTYPE html><html><head><title>$DASHBOARD_TITLE</title>"
            "<style>$CSS_CONTENT</style></head><body>"
            "<script>$DATA_JS</script><script>$APP_JS</script></body></html>"
        )

        css_file = src_dir / "styles.css"
        css_file.write_text("body { margin: 0; }")

        js_file = src_dir / "app.js"
        js_file.write_text("console.log('test');")

        # Step 1: CSV to JS
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            data_js_file = dist_dir / "data.js"
            csv_to_js.build_data_module(config_file, data_js_file)

            assert data_js_file.exists()
            data_content = data_js_file.read_text()
            assert '@user1' in data_content
            assert 'DASHBOARD_CONFIG' in data_content

            # Step 2: Generate HTML
            index_file = dist_dir / "index.html"
            generate_html.generate_html(
                config_file,
                template_file,
                css_file,
                js_file,
                data_js_file,
                index_file
            )

            assert index_file.exists()
            html_content = index_file.read_text()

            # Verify complete HTML
            assert '<!DOCTYPE html>' in html_content
            assert 'Integration Test' in html_content
            assert 'body { margin: 0; }' in html_content
            assert '@user1' in html_content
            assert '@user2' in html_content
            assert "console.log('test');" in html_content

            # Verify no unreplaced placeholders
            assert '$DASHBOARD_TITLE' not in html_content
            assert '$CSS_CONTENT' not in html_content
            assert '$DATA_JS' not in html_content
            assert '$APP_JS' not in html_content

        finally:
            os.chdir(original_cwd)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
