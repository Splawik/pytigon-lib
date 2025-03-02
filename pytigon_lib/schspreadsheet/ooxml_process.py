import zipfile
import shutil
import os
import datetime
from xml.sax.saxutils import escape
from lxml import etree
from django.template import Context
from pytigon_lib.schspreadsheet.odf_process import OdfDocTransform
from pytigon_lib.schfs.vfstools import delete_from_zip
import dateutil.parser

SECTION_WIDTH = ord("Z") - ord("A") + 1


def transform_str(s):
    """Replace special characters in the string."""
    return s.replace("***", '"').replace("**", "'")


def filter_attr(tab, attr, value):
    """Filter elements in `tab` based on the attribute `attr` and `value`."""
    check_type = 0
    ret = []
    if value.startswith("*"):
        check_type = 1
    if value.endswith("*"):
        check_type = 3 if check_type == 1 else 2

    for pos in tab:
        if attr in pos.attrib:
            if (
                (check_type == 0 and pos.attrib[attr] == value)
                or (check_type == 1 and pos.attrib[attr].endswith(value[1:]))
                or (check_type == 2 and pos.attrib[attr].startswith(value[:-1]))
                or (check_type == 3 and value[1:-1] in pos.attrib[attr])
            ):
                ret.append(pos)
    return ret


def col_row(excel_addr):
    """Convert Excel address to column, row, and column index."""
    if excel_addr[1] >= "0" and excel_addr[1] <= "9":
        col = excel_addr[0].upper()
        row = int(excel_addr[1:])
    else:
        col = excel_addr[:2].upper()
        row = int(excel_addr[2:])

    col_as_int = (
        (ord(col[0]) - ord("A") + 1) * SECTION_WIDTH + (ord(col[1]) - ord("A")) + 1
        if len(col) > 1
        else ord(col[0]) - ord("A") + 1
    )
    return col, row, col_as_int


def make_col_row(col, row):
    """Convert column index and row to Excel address."""
    _col, _row, col_as_int = col_row("Z1")
    if col > col_as_int:
        x1 = (col - 1) // col_as_int
        x2 = (col - 1) % col_as_int
        return chr(ord("A") + x1 - 1) + chr(ord("A") + x2) + str(row)
    else:
        return chr(ord("A") + col - 1) + str(row)


def key_for_addr(excel_addr):
    """Generate a key for sorting Excel addresses."""
    col, row, col_as_int = col_row(excel_addr)
    return row * 1000 + col_as_int


def date_to_float(d):
    """Convert datetime to Excel date format."""
    dt = d - datetime.datetime(1899, 12, 30)
    return dt.days + dt.seconds / 86400


class OOXmlDocTransform(OdfDocTransform):
    """Transform OOXML files (e.g., .xlsx)."""

    def __init__(self, file_name_in, file_name_out=None):
        """Initialize the transformer."""
        super().__init__(file_name_in, file_name_out)
        self.file_name_in = file_name_in
        self.file_name_out = file_name_out or file_name_in.replace("_", "")
        self.zip_file = None
        self.to_update = []
        self.shared_strings = {}
        self.comments = {}

    def get_xml_content(self, xml_name):
        """Retrieve XML content from the zip file or cache."""
        for pos in self.to_update:
            if xml_name == pos[0]:
                return {"data": pos[1], "from_cache": True}

        content = self.zip_file.read(xml_name)
        return {"data": etree.XML(content), "from_cache": False}

    def extended_transformation(self, xml_name, script):
        """Apply extended transformations to the XML content."""
        ret = self.get_xml_content(xml_name)
        xml = ret["data"]
        if script(self, xml) and not ret["from_cache"]:
            self.to_update.append((xml_name, xml))

    def add_comments(self, sheet):
        """
        Add comments to the given sheet based on the stored comments.

        This function iterates through the cells in the provided sheet and adds
        comments from the `self.comments` dictionary to the appropriate cells.
        The comments are added based on their cell references, ensuring that
        comments are placed in the correct order. The function processes each
        comment, splitting it into multiple parts if necessary, and inserts
        these parts at specified positions relative to the existing content
        within the cell's parent element.

        Args:
            sheet (etree.Element): The XML element representing the sheet where
                                comments will be added.

        """
        if self.comments:
            labels = []
            d = sheet.findall(".//c", namespaces=sheet.nsmap)
            for pos in d:
                if "r" in pos.attrib:
                    labels.append(pos.attrib["r"])
            labels.sort(key=key_for_addr)

            for key, value in self.comments.items():
                value2 = value.strip()
                if key in labels:
                    label = key
                else:
                    labels2 = labels + [
                        key,
                    ]
                    labels2.sort(key=key_for_addr)
                    old = None
                    for l in labels2:
                        if l == key:
                            break
                        old = l
                    if old:
                        label = old
                    else:
                        label = labels[0]

                d = filter_attr(
                    sheet.findall(".//c", namespaces=sheet.nsmap), "r", label
                )
                if len(d) > 0:
                    if value2 and (
                        value2.startswith("^")
                        or value2.startswith("$")
                        or value2.startswith(".")
                    ):
                        self._handle_annotation(d[0], value2)

    def shared_strings_to_inline(self, sheet):
        """
        Convert shared string references in a sheet to inline strings or formulas.

        This function processes all cell elements in the given sheet with the
        attribute `t='s'`, which indicates a shared string reference. It retrieves
        the shared string by its ID, modifies the cell element based on specific
        prefixes in the shared string, and converts it to an inline string or
        a formula as appropriate.

        :param sheet: The XML sheet element to process.
        :type sheet: lxml.etree.Element
        """

        d = filter_attr(sheet.findall(".//c", namespaces=sheet.nsmap), "t", "s")
        for pos in d:
            v = pos.find(".//v", namespaces=sheet.nsmap)
            try:
                id = int(v.text)
            except:
                id = -1
            if id >= 0:
                s = self.shared_strings[id]
                if s:
                    if s.startswith(":="):
                        pos.remove(v)
                        pos.attrib.pop("t", None)
                        pos.append(etree.XML("<f>%s</f>" % escape(s[2:])))
                    elif s.startswith(":?"):
                        pos.remove(v)
                        pos.attrib.pop("t", None)
                        pos.append(etree.XML("<vauto>%s</vauto>" % escape(s[2:])))
                    elif s.startswith(":0"):
                        pos.remove(v)
                        pos.attrib["t"] = "n"
                        pos.append(etree.XML("<v>%s</v>" % escape(s[2:])))
                    elif s.startswith(":*"):
                        pos.attrib["t"] = "inlineStr"
                        pos.remove(v)
                        pos.append(etree.XML("<is><t>%s</t></is>" % escape(s[2:])))
                    elif ("{{" in s and "}}" in s) or ("{%" in s and "%}" in s):
                        pos.attrib["t"] = "inlineStr"
                        pos.remove(v)
                        pos.append(etree.XML("<is><t>%s</t></is>" % escape(s)))

    def repair_xml(self, sheet):
        """
        Repairs the XML sheet by reordering and renumbering its elements (rows
        and columns). This is necessary because the XML structure of the OOXML
        file is not always valid after processing through the `OdfDocTransform`
        class. This function should be called after any of the methods of the
        `OdfDocTransform` class.

        :param sheet: The XML sheet element to process.
        :type sheet: lxml.etree.Element
        """
        max_row = 0
        max_col = 0
        d = sheet.findall(".//row", namespaces=sheet.nsmap)
        i = 1
        for row in d:
            if "r" in row.attrib:
                i2 = int(row.attrib["r"])
                if i2 < i:
                    row.attrib["r"] = str(i)
                elif i2 > i:
                    i = i2
            d2 = row.findall(".//c", namespaces=sheet.nsmap)
            j = 1
            for c in d2:
                if "r" in c.attrib:
                    a = c.attrib["r"]
                    _c, _r, c_id = col_row(a)
                    if _r != i or c_id != j:
                        if c_id < j:
                            c_id = j
                        else:
                            j = c_id
                        c.attrib["r"] = make_col_row(c_id, i)
                j += 1
                if j > max_col:
                    max_col = j
            i += 1

        max_row = i - 1
        max_col = max_col - 1
        max_addr = make_col_row(max_col, max_row)

        if max_row > 0 and max_col > 0:
            d = sheet.find(".//dimension", namespaces=sheet.nsmap)
            if d != None:
                if "ref" in d.attrib:
                    addr = d.attrib["ref"]
                    d.attrib["ref"] = "A1:" + max_addr

        auto_list = sheet.findall(".//vauto", namespaces=sheet.nsmap)
        for pos in auto_list:
            parent = pos.getparent()
            txt = pos.text
            parent.remove(pos)
            if txt != "" and txt != None:
                if (
                    (len(txt) == 10 or len(txt) == 19)
                    and txt[4] == "-"
                    and txt[7] == "-"
                ):
                    try:
                        d = dateutil.parser.parse(txt)
                        x = date_to_float(d)
                        parent.append(etree.XML("<v>%f</v>" % x))
                        continue
                    except:
                        pass
                try:
                    x = float(txt)
                    parent.append(etree.XML("<v>%s</v>" % escape(txt)))
                    continue
                except:
                    pass

            parent.attrib["t"] = "inlineStr"
            try:
                if txt:
                    parent.append(etree.XML("<is><t>%s</t></is>" % escape(txt)))
                else:
                    parent.append(etree.XML("<is><t></t></is>"))
            except:
                print(txt)

        c_list = sheet.findall(".//c", namespaces=sheet.nsmap)
        for pos in c_list:
            f = pos.find(".//f", namespaces=sheet.nsmap)
            if f != None:
                v = pos.find(".//v", namespaces=sheet.nsmap)
                if v != None:
                    pos.remove(v)

    def handle_sheet(self, sheet, django_context):
        """Handle sheet transformations."""
        self.shared_strings_to_inline(sheet)
        self.add_comments(sheet)
        sheet_str = etree.tostring(sheet, pretty_print=True).decode("utf-8")
        sheet_str = self.process_template(sheet_str, django_context)
        root = etree.XML(sheet_str)
        self.repair_xml(root)
        return root

    def process(self, context, debug):
        """Process the input file with the given context."""
        django_context = Context(context)
        xlsx = context.get("doc_type", "xlsx") == "xlsx"
        shutil.copyfile(self.file_name_in, self.file_name_out)
        self.to_update = []
        self.zip_file = zipfile.ZipFile(self.file_name_out, "r")

        if xlsx:
            try:
                shared_strings_str = self.zip_file.read("xl/sharedStrings.xml")
                root = etree.XML(shared_strings_str)
                self.shared_strings = [
                    transform_str(
                        etree.tostring(pos, method="text", encoding="utf-8").decode(
                            "utf-8"
                        )
                    )
                    for pos in root.findall(".//si", namespaces=root.nsmap)
                ]
            except KeyError:
                self.shared_strings = []

            id = 1
            while True:
                if (
                    "no_process_sheets" in context
                    and id in context["no_process_sheets"]
                ):
                    id += 1
                    continue
                try:
                    sheet_name = f"xl/worksheets/sheet{id}.xml"
                    sheet_str = self.zip_file.read(sheet_name)
                    sheet = etree.XML(sheet_str)
                    self.comments = {}
                    try:
                        sheet_rels_name = f"xl/worksheets/_rels/sheet{id}.xml.rels"
                        sheet_rels_str = self.zip_file.read(sheet_rels_name)
                        root = etree.XML(sheet_rels_str)
                        d1 = root.findall(".//{*}Relationship", namespaces=root.nsmap)
                        d2 = filter_attr(
                            d1,
                            "Type",
                            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
                        )
                        if d2:
                            comments_name = os.path.normpath(
                                f"xl/worksheets/{d2[0].attrib['Target']}"
                            ).replace("\\", "/")
                            comments_str = self.zip_file.read(comments_name)
                            root = etree.XML(comments_str)
                            for pos in root.findall(
                                ".//{*}comment", namespaces=root.nsmap
                            ):
                                ref = pos.attrib["ref"]
                                for pos2 in pos.findall(
                                    ".//{*}text/{*}r/{*}t", namespaces=root.nsmap
                                ):
                                    if (
                                        "{{" in pos2.text
                                        or "{%" in pos2.text
                                        or pos2.text.startswith("^")
                                        or pos2.text.startswith("$")
                                        or pos2.text.startswith(".")
                                    ):
                                        self.comments[ref] = pos2.text
                                        comment = (
                                            pos2.getparent().getparent().getparent()
                                        )
                                        comment_list = comment.getparent()
                                        comment_list.remove(comment)
                            self.to_update.append((comments_name, root))
                    except KeyError:
                        pass
                    sheet2 = self.handle_sheet(sheet, django_context)
                    self.to_update.append((sheet_name, sheet2))
                except KeyError:
                    break
                id += 1

            if "extended_transformations" in django_context:
                for pos in django_context["extended_transformations"]:
                    self.extended_transformation(pos[0], pos[1])

            self.zip_file.close()
            delete_from_zip(self.file_name_out, [pos[0] for pos in self.to_update])
            with zipfile.ZipFile(self.file_name_out, "a", zipfile.ZIP_DEFLATED) as z:
                for pos in self.to_update:
                    z.writestr(
                        pos[0],
                        etree.tostring(pos[1], pretty_print=True)
                        .decode("utf-8")
                        .replace("<tmp>", "")
                        .replace("</tmp>", ""),
                    )
        else:
            doc_type = context["doc_type"]
            if doc_type == "docx":
                doc_name = "word/document.xml"
                doc_str = self.zip_file.read(doc_name).decode("utf-8")
                doc_str = self.process_template(doc_str, django_context)
                self.to_update.append((doc_name, doc_str))
            elif doc_type == "pptx":
                id = 1
                while True:
                    doc_name = f"ppt/slides/slide{id}.xml"
                    try:
                        doc_str = self.zip_file.read(doc_name).decode("utf-8")
                        doc_str2 = self.process_template(doc_str, django_context)
                        if doc_str != doc_str2:
                            self.to_update.append((doc_name, doc_str2))
                        id += 1
                    except KeyError:
                        break
            else:
                return 0

            self.zip_file.close()
            if self.to_update:
                delete_from_zip(
                    self.file_name_out, [item[0] for item in self.to_update]
                )
                with zipfile.ZipFile(
                    self.file_name_out, "a", zipfile.ZIP_DEFLATED
                ) as z:
                    for item in self.to_update:
                        z.writestr(item[0], item[1].encode("utf-8"))

        return 1


if __name__ == "__main__":
    from django.conf import settings
    import django

    settings.configure(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
            }
        ]
    )
    django.setup()

    x = OOXmlDocTransform("./test/rep_wzr.xlsx", "./test/rep_wzr_out.xlsx")
    context = {"test": 1}
    x.process(context, False)
