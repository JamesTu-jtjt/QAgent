import os
import argparse
from testrail import *
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from dotenv import load_dotenv


class TestRailAPI:
    """A simple client to interact with the TestRail API."""
    def __init__(self, base_url: str, user: str, password: str):
        self.client = APIClient(base_url=base_url)
        self.client.user = user
        self.client.password = password


    def add_section(self, project_id: int, data: Dict[str, any]) -> Dict:
        """Adds a new section to a specific project and suite.
        payload example:
        {
            'suite_id': int,
            'name': str,
            'parent_id': int (optional, default 0)
        }
        """
        return self.client.send_post(f'add_section/{project_id}', data)
    
    def add_case(self, section_id: int, data: Dict[str, Any]) -> Dict:
        """Adds a new test case to a specific section.
        {
            "title": "Verify successful display of BB Broadcast performance report.",
            "refs": "TC-BB-BR-001",
            "custom_preconds": "Preconditions: ...",
            "type_id": 7,
            "priority_id": 4,
            "labels": ["From Mindmeister"],
            "custom_steps_separated": [
                {
                "content": "1. Step 1.",
                "expected": "Expected result of Step 1."
                },
                {
                "content": "2. Step 2.",
                "expected": "Expected result of Step 2."
                }
            ]
        }
        """
        return self.client.send_post(f'add_case/{section_id}', data)

    def get_sections(self, project_id: str, suite_id: str) -> List[Dict]:
        """Gets all sections for a given project and suite."""
        return self.client.send_get(f'get_sections/{project_id}&suite_id={suite_id}')
    
    def delete_section(self, section_id: int) -> Dict:
        """Deletes a section by its ID."""
        return self.client.send_post(f'delete_section/{section_id}', {'soft': 0})


def _is_node(elem: ET.Element) -> bool:
    return elem.tag.lower() == "node"

def _node_text(n: ET.Element) -> str:
    return (n.attrib.get("TEXT") or "").strip()

def _child_nodes(n: ET.Element) -> list[ET.Element]:
    # Only real <node> elements; ignore <font>, <edge>, etc.
    return [c for c in list(n) if _is_node(c)]

def _has_untitled_child(n: ET.Element) -> bool:
    return any(_node_text(c) == "" for c in _child_nodes(n))

def _note_html(n: ET.Element) -> str | None:
    # Return inner HTML of <richcontent TYPE="NOTE"> as a string.
    # Many MindMeister notes are wrapped inside an <html> element.
    for rc in n.findall("richcontent"):
        if (rc.attrib.get("TYPE") or "").upper() == "NOTE":
            parts = []
            for child in list(rc):
                parts.append(ET.tostring(child, encoding="unicode"))
            if parts:
                return "".join(parts)
            # Fallback if no child tags, just text
            txt = (rc.text or "").strip()
            return txt or None
    return None

def _pick_description(n: ET.Element) -> str:
    """Prefer the node's own NOTE; else an untitled child's NOTE; else empty."""
    own = _note_html(n)
    if own:
        return own
    for c in _child_nodes(n):
        if _node_text(c) == "":
            child_note = _note_html(c)
            if child_note:
                return child_note
    return ""


class MindMeisterUploader:
    """
    Parses a MindMeister .mm XML file and uploads its content as sections and
    test cases to TestRail, following rules:
    - Children of the core node are sections (can nest).
    - A node under a section is a test case if it has no subnodes OR has an untitled subnode.
    - Test case description comes from NOTE html (own NOTE first, else untitled child NOTE).
    """
    def __init__(self, mm_path: str, project_id: int, suite_id: int):
        self.mm_path = mm_path
        self.project_id = project_id
        self.suite_id = suite_id

        load_dotenv()
        testrail_url = os.getenv("TESTRAIL_URL")
        testrail_user = os.getenv("TESTRAIL_USER")
        testrail_key = os.getenv("TESTRAIL_PASSWORD_OR_KEY")

        if not all([testrail_url, testrail_user, testrail_key]):
            raise ValueError("TESTRAIL_URL, TESTRAIL_USER, and TESTRAIL_PASSWORD_OR_KEY must be set in .env file.")

        self.api = TestRailAPI(testrail_url, testrail_user, testrail_key)

    def _parse_mm_xml_file(self) -> ET.Element:
        """Parses the .mm XML file and returns the core <node>."""
        try:
            tree = ET.parse(self.mm_path)
            root = tree.getroot()             # <map ...>
            core = root.find("node") or root  # sometimes the root is itself <node>
            if core is None or core.tag.lower() != "node":
                raise ValueError("Invalid .mm format: could not find the root <node>.")
            return core
        except ET.ParseError:
            print(f"Error: The file '{self.mm_path}' is not a valid XML file.")
            exit(1)
        except FileNotFoundError:
            print(f"Error: The file '{self.mm_path}' was not found.")
            exit(1)

    def _create_or_get_section(self, name: str, parent_id: int | None) -> int:
        """Create a section (optionally nested) and return its id. No dedupe here—caller handles reuse."""
        payload = {"suite_id": self.suite_id, "name": name}
        if parent_id:
            payload["parent_id"] = parent_id
        new_section = self.api.add_section(self.project_id, payload)
        return new_section["id"]

    def _process_as_case(self, node: ET.Element, parent_section_id: int):
        title = _node_text(node) or "(Untitled)"
        description = _pick_description(node)
        if description != "":
            title = "*" + title 
            if '<body>' in description:
                description = description.split('<body>')[1].split('</body>')[0]
        case_payload = {
            "title": title,
            "labels": ["From MindMeister"],
            "template_id": 1,
            "custom_steps": description
        }

        result = self.api.add_case(parent_section_id, case_payload)
        print(f"      -> Uploaded case C{result['id']}: {result['title']}")

    def _process_node_recursively(self, node: ET.Element, parent_section_id: int):
        """
        Decide whether this node is a Section or a Case:
          - If it has NO child nodes -> CASE
          - If it has ANY untitled child node -> CASE
          - Otherwise -> SECTION (create subsection and recurse)
        """
        title = _node_text(node) or "Untitled Node"
        kids = _child_nodes(node)

        is_case = (len(kids) == 0) or _has_untitled_child(node)

        if is_case:
            print(f"    -> Creating test case: {title}")
            try:
                self._process_as_case(node, parent_section_id)
            except Exception as e:
                print(f"      -> FAILED to upload test case '{title}'. Error: {e}")
            return

        # Otherwise treat as a (sub)section and recurse into its child nodes
        print(f"  - Creating subsection: {title}")
        try:
            new_section_id = self._create_or_get_section(title, parent_section_id)
        except Exception as e:
            print(f"  - FAILED to create subsection '{title}'. Error: {e}")
            return

        for child in kids:
            self._process_node_recursively(child, new_section_id)

    def _traverse_and_upload(self, core_node: ET.Element):
        """
        Top-level children of core are Sections.
        We will create (or reuse) those sections, then process their children.
        """
        # Optional: fetch existing sections if you want to reuse by name
        try:
            print("Fetching existing sections from TestRail...")
            resp = self.api.get_sections(self.project_id, self.suite_id)
            existing_sections = resp.get("sections", [])
            # Reuse only at top level by name; nested matching can be added if desired
            top_name_to_id = {s["name"]: s["id"] for s in existing_sections if s.get("parent_id") in (0, None)}
            print(f"Found {len(existing_sections)} total sections ({len(top_name_to_id)} top-level).")
        except Exception as e:
            print(f"Error fetching sections from TestRail (continuing with fresh create): {e}")
            top_name_to_id = {}

        # Each direct <node> under core is a top-level Section by your rule
        for top in _child_nodes(core_node):
            section_name = _node_text(top) or "Unnamed Section"
            print(f"\n--- Top-Level Section: {section_name} ---")

            section_id = top_name_to_id.get(section_name)
            if not section_id:
                print(f"Creating top-level section '{section_name}' ...")
                try:
                    section_id = self._create_or_get_section(section_name, parent_id=None)
                except Exception as e:
                    print(f"FAILED to create section '{section_name}'. Error: {e}")
                    continue
            else:
                print(f"Reusing existing top-level section '{section_name}' (ID {section_id})")

            # Process the children of this section. Each child can become a case or a nested section.
            for child in _child_nodes(top):
                self._process_node_recursively(child, section_id)

    def run(self):
        print(f"Starting upload from '{self.mm_path}'...")
        core_node = self._parse_mm_xml_file()
        self._traverse_and_upload(core_node)
        print("\nUpload process complete.")


    def delete_all_sections(self):
        existing_sections = self.api.get_sections(self.project_id, self.suite_id)
        ids = [section['id'] for section in existing_sections['sections']]
        print(f"Deleting all sections in project {self.project_id} suite {self.suite_id}...")
        for id in ids: 
            existing_sections = self.api.get_sections(self.project_id, self.suite_id)
            id_updated = [section['id'] for section in existing_sections['sections']]
            if id not in id_updated: 
                continue
            self.api.delete_section(id)
        print(f"Deleted {len(ids)} sections.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload test cases from a MindMeister .mm file to TestRail.")
    parser.add_argument("--mm_path", help="Path to the input MindMeister .mm file.")
    parser.add_argument("--project_id", required=True, type=int, help="The ID of the project in TestRail.")
    parser.add_argument("--suite_id", required=True, type=int, help="The ID of the test suite in TestRail.")
    args = parser.parse_args()

    uploader = MindMeisterUploader(args.mm_path, args.project_id, args.suite_id)
    # uploader.delete_all_sections() # clears test suite before adding test cases
    uploader.run()
