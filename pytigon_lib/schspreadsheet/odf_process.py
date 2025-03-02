import re
import shutil
import base64
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree, html
from xml.sax.saxutils import escape
from pytigon_lib.schfs.vfstools import delete_from_zip

OFFICE_URN = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
TABLE_URN = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
TEXT_URN = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


def attr_get(attrs, key):
    """Get attribute value by key suffix."""
    for k in attrs.keys():
        if k.endswith(key):
            return attrs[k]
    return None


def transform_str(s):
    """Transform string by replacing special characters."""
    return s.replace("***", '"').replace("**", "'")


def inner_html(elem):
    return (elem.text or "") + "".join(
        [html.tostring(child).decode("utf-8") for child in elem.iterchildren()]
    )


class OdfDocTransform:
    """Transform ODF files."""

    def __init__(self, file_name_in, file_name_out=None):
        """Initialize OdfDocTransform with input and output file names."""
        self.file_name_in = file_name_in
        self.file_name_out = file_name_out or file_name_in.replace("_", "")
        self.process_tables = None
        self.doc_type = 1
        self.buf = None
        self.auto_cells = False

    def set_doc_type(self, doc_type):
        """Set document type: 0 - other, 1 - spreadsheet, 2 - writer."""
        self.doc_type = doc_type

    def set_process_tables(self, tables):
        """Set tables to process."""
        self.process_tables = tables

    def column_number(self):
        """Return template string for column increment."""
        return "{{ tbl.IncCol }}"

    def row_number(self, il=1):
        return """{{ tbl|args:%d|call:'IncRow' }}{{ tbl|args:1|call:'SetCol' }}""" % il

    def clear_row_col(self):
        return """{{ tbl|args:1|call:'SetRow' }}{{ tbl|args:1|call:'SetCol' }}"""

    def doc_process(self, doc, debug):
        """Process document type 2 (writer)."""
        pass

    def spreadsheet_process(self, doc, debug):
        """Process spreadsheet document."""
        self._process_annotations(doc, debug)
        self._process_table_cells(doc, debug)
        self._process_table_rows(doc)
        self._process_tables(doc)

    def _handle_annotation(self, comment_elem, comment_txt):
        """
        Handle annotations by processing comment text and inserting XML elements.

        This function processes the given comment text to determine the level of
        annotation and any positional offsets. It splits the comment text into
        individual values if necessary and inserts corresponding XML elements
        into the parent or grandparent nodes of the provided comment element.

        Args:
            comment_elem (etree.Element): The XML element representing the comment.
            comment_txt (str): The text content of the comment to be processed.

        The function supports annotations that begin with '^' or '$' to indicate
        hierarchical levels, and uses '@' to split the comment text into multiple
        parts for insertion at different positions.
        """

        parent = comment_elem.getparent()
        level = 0
        if comment_txt.startswith("."):
            if comment_elem is not None:
                if "table-cell" in comment_elem.tag:
                    for child in comment_elem.getchildren():
                        if "annotation" not in child.tag:
                            comment_elem.remove(child)
                    new_cell = etree.Element(TEXT_URN + "p")
                    new_cell.text = comment_txt[1:]
                    comment_elem.append(new_cell)
                else:
                    for child in comment_elem.getchildren():
                        if child.tag.endswith("v"):
                            comment_elem.remove(child)
                    comment_elem.append(
                        etree.XML("<is><t>%s</t></is>" % escape(comment_txt[1:]))
                    )
                    comment_elem.attrib["t"] = "inlineStr"
            return

        while comment_txt.startswith("^") or comment_txt.startswith("$"):
            level += 1
            offset = 0 if comment_txt.startswith("^") else 1
            comment_txt = comment_txt[1:]
        if "@" in comment_txt:
            x = comment_txt.split("@")
            values = [[x[0], level, 0], [x[1], level, 1]]
        else:
            values = [[comment_txt, level, 0]]

        for v, level, offset in values:
            if level < 1:
                parent.insert(
                    parent.index(comment_elem) + offset,
                    etree.XML("<tmp>%s</tmp>" % escape(v)),
                )
            else:
                gparent = parent
                while level > 0:
                    p = gparent
                    gparent = p.getparent()
                    level -= 1
                gparent.insert(
                    gparent.index(p) + offset,
                    etree.XML("<tmp>%s</tmp>" % escape(v)),
                )

    def _process_annotations(self, doc, debug):
        """Process annotations in the document."""
        for e in doc.findall(".//{*}annotation/{*}p"):
            element = e.getparent()
            data = e.text
            if not data:
                data = ""
                for txt in e.itertext():
                    if txt:
                        data += txt
            data = data.strip()
            if data and (
                data.startswith("^") or data.startswith("$") or data.startswith(".")
            ):
                self._handle_annotation(element.getparent(), data)
            parent = element.getparent()
            parent.remove(element)

    def _process_table_cells(self, doc, debug):
        """Process table cells in the document."""
        for element in doc.findall(".//{*}table-cell"):
            self._handle_repeated_columns(element)
            if attr_get(element.attrib, "value-type") == "string":
                self._handle_string_cell(element, debug)

    def _handle_repeated_columns(self, element):
        """Handle repeated columns in table cells."""
        nr = attr_get(element.attrib, "number-columns-repeated")
        if nr and int(nr) > 1000:
            element.set(TABLE_URN + "number-columns-repeated", "1000")

    def _handle_string_cell(self, element, debug):
        """Handle string type table cells."""
        txt = (
            etree.tostring(element, method="text", encoding="utf-8")
            .decode("utf-8")
            .strip()
        )
        if any(item in txt for item in (":=", ":*", ":?", "{{", "}}", "{%", "%}")):
            txt = transform_str(txt)
            if txt.startswith(":="):
                self._create_formula_cell(element, txt, debug)
            elif txt.startswith(":?"):
                self.auto_cells = True
                self._create_auto_cell(element, txt, debug)
            else:
                self._create_value_cell(element, txt, debug)

    def _create_formula_cell(self, element, txt, debug):
        """Create a new cell with a formula."""
        new_cell = etree.Element(TABLE_URN + "table-cell")
        new_cell.set(OFFICE_URN + "value-type", "float")
        new_cell.set(OFFICE_URN + "value", "0")
        new_cell.set(TABLE_URN + "formula", "of:=" + txt[2:])
        new_text = etree.Element(OFFICE_URN + "p")
        new_cell.append(new_text)
        if debug:
            self._add_annotation(new_cell, txt[2:].replace("^", ""))
        self._set_cell_style(element, new_cell)
        self._replace_cell(element, new_cell)

    def _create_value_cell(self, element, txt, debug):
        """Create a new cell with a value."""
        new_cell = etree.Element(TABLE_URN + "table-cell")
        if txt.startswith(":0"):
            new_cell.set(OFFICE_URN + "value-type", "float")
            new_cell.set(OFFICE_URN + "value", str(txt[2:]))
            new_text = etree.Element(TEXT_URN + "p")
            new_text.text = str(txt[2:])
            new_cell.append(new_text)
        else:
            new_cell.set(OFFICE_URN + "value-type", "string")
            new_text = etree.Element(TEXT_URN + "p")
            new_text.text = txt[2:] if txt.startswith(":*") else txt
            new_cell.append(new_text)
        if debug:
            self._add_annotation(new_cell, txt[2:] if txt.startswith(":*") else txt)
        self._set_cell_style(element, new_cell)
        self._replace_cell(element, new_cell)

    def _create_auto_cell(self, element, txt, debug):
        """Create a new cell with a value."""
        new_cell = etree.Element(TABLE_URN + "table-cell")
        new_cell.set(OFFICE_URN + "value-type", "string")
        new_text = etree.Element(TEXT_URN + "vauto")
        new_text.text = txt[2:] if txt.startswith(":?") else txt
        new_cell.append(new_text)
        if debug:
            self._add_annotation(new_cell, txt[2:] if txt.startswith(":?") else txt)
        self._set_cell_style(element, new_cell)
        self._replace_cell(element, new_cell)

    def _add_annotation(self, cell, text):
        """Add annotation to a cell."""
        new_annotate = etree.Element(OFFICE_URN + "annotation")
        new_text_a = etree.Element(TEXT_URN + "p")
        new_text_a.text = text
        new_annotate.append(new_text_a)
        cell.append(new_annotate)

    def _set_cell_style(self, element, new_cell):
        """Set style for a new cell."""
        style_name = attr_get(element.attrib, "style-name")
        if style_name:
            new_cell.set(TABLE_URN + "style-name", style_name)

    def _replace_cell(self, element, new_cell):
        """Replace old cell with a new one."""
        new_cell2 = etree.Element("tmp")
        new_cell2.append(new_cell)
        new_cell2.text = self.column_number()
        parent = element.getparent()
        parent[parent.index(element)] = new_cell2

    def _process_table_rows(self, doc):
        """Process table rows in the document."""
        for element in doc.findall(".//{*}table-row"):
            self._handle_repeated_rows(element)

    def _handle_repeated_rows(self, element):
        """Handle repeated rows in table."""
        nr = attr_get(element.attrib, "number-rows-repeated")
        nr = int(nr) if nr else 1
        if nr > 1000:
            element.set(TABLE_URN + "number-rows-repeated", "1000")
        new_cell = etree.Element("tmp")
        parent = element.getparent()
        parent[parent.index(element)] = new_cell
        new_cell.append(element)
        new_cell.text = self.row_number(nr)

    def _process_tables(self, doc):
        """Process tables in the document."""
        for element in doc.findall(".//{*}table"):
            self._reset_row_col(element)
            if (
                self.process_tables
                and attr_get(element.attrib, "name") not in self.process_tables
            ):
                self._remove_table(element)

    def _reset_row_col(self, element):
        """Reset row and column for a table."""
        new_cell = etree.Element("tmp")
        new_cell.text = self.clear_row_col()
        parent = element.getparent()
        parent[parent.index(element)] = new_cell
        new_cell.append(element)

    def _remove_table(self, element):
        """Remove a table from the document."""
        new_cell = etree.Element("tmp")
        parent = element.getparent()
        parent[parent.index(element)] = new_cell

    def process_template(self, doc_str, context):
        """Process template with context."""
        pass

    def extended_transformation(self, xml_name, script):
        """Apply extended transformation using a script."""
        xml = etree.fromstring(self.buf.encode("utf-8"))
        script(self, xml)
        self.buf = etree.tostring(xml, encoding="utf-8", xml_declaration=True).decode(
            "utf-8"
        )

    def repair_xml(self, sheet):
        auto_list = sheet.findall(".//{*}vauto")
        for pos in auto_list:
            parent = pos.getparent()
            txt = pos.text
            parent.remove(pos)
            if txt != "" and txt != None:
                if len(txt) == 10 and txt[4] == "-" and txt[7] == "-":
                    try:
                        new_text = etree.Element(TEXT_URN + "p")
                        parent.append(new_text)
                        parent.set(OFFICE_URN + "value-type", "date")
                        parent.set(OFFICE_URN + "date-value", txt[:10])
                        continue
                    except:
                        pass
                try:
                    x = float(txt)
                    new_text = etree.Element(TEXT_URN + "p")
                    parent.append(new_text)
                    parent.set(OFFICE_URN + "value-type", "float")
                    parent.set(OFFICE_URN + "value", txt)
                    continue
                except:
                    pass
                new_text = etree.Element(TEXT_URN + "p")
                new_text.text = escape(txt)
                parent.append(new_text)

    def process(self, context, debug):
        """Transform input file using context and debug mode."""
        try:
            shutil.copyfile(self.file_name_in, self.file_name_out)
            with ZipFile(self.file_name_out, "r") as z:
                doc_content = z.read("content.xml").decode("utf-8")

            if delete_from_zip(self.file_name_out, ["content.xml"]) == 0:
                return

            doc = etree.fromstring(
                doc_content.replace("&apos;", "'")
                .replace("_start_", "{{")
                .replace("_end_", "}}")
                .encode("utf-8")
            )

            if self.doc_type == 1:
                self.spreadsheet_process(doc, debug)
            elif self.doc_type == 2:
                self.doc_process(doc, debug)

            doc_str = (
                etree.tostring(doc, encoding="utf-8", xml_declaration=True)
                .decode("utf-8")
                .replace("<tmp>", "")
                .replace("</tmp>", "")
            )

            doc_str = re.sub(r"\^(.*?\(.*?\))", r"${\1}", doc_str)

            if "expr_escape" in context:
                doc_str = doc_str.replace("{{", "{% expr_escape ").replace("}}", " %}")

            x = self.process_template(doc_str, context) or doc_str

            if self.auto_cells:
                root = etree.XML(x.encode("utf-8"))
                self.repair_xml(root)
                x = etree.tostring(root, encoding="utf-8").decode("utf-8")

            files = []
            if "[[[" in x and "]]]" in x:
                data = [pos.split("]]]")[0] for pos in x.split("[[[")[1:]]
                data2 = [pos.split("]]]")[-1] for pos in x.split("[[[")]
                fdata = []
                for i, pos in enumerate(data, 1):
                    x = pos.split(",", 1)
                    ext = x[0].split(";")[0].split("/")[-1]
                    name = f"Pictures/pytigon_{i}.{ext}"
                    fdata.append(name)
                    files.append([name, x, ext])
                data3 = [None] * (len(data) + len(data2))
                data3[::2] = data2
                data3[1::2] = fdata
                x = "".join(data3)

            self.buf = x

            if "extended_transformations" in context:
                for pos in context["extended_transformations"]:
                    self.extended_transformation(pos[0], pos[1])

            with ZipFile(self.file_name_out, "a", ZIP_DEFLATED) as z:
                z.writestr("content.xml", self.buf.encode("utf-8"))
                for pos in files:
                    z.writestr(pos[0], base64.b64decode(pos[1].encode("utf-8")))

            return 1
        except Exception as e:
            print(f"Error processing file: {e}")
            return 0


if __name__ == "__main__":
    x = OdfDocTransform("./test.ods", "./test_out.ods")
    context = {"test": 1, "object_list": ["x1", "x2", "x3"]}
    x.process(context, False)
