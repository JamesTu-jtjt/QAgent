# MindMeister to TestRail Uploader

Uploads a `.mm` MindMeister/FreeMind mind map to TestRail as sections and test cases.

#### Rules: 
- Children of the core node are sections; sections can nest arbitrarily (subnodes will be added as subsections).
- A node becomes a Test Case if:
  * it has no child <node>, OR
  * it has a child <node> with empty/missing TEXT ("untitled")
- Test Case Title = node TEXT
- Test Case Description:
  * Prefer NOTE html from the node's own <richcontent TYPE="NOTE">
  * Else, empty.


## Prerequisites
- Python 3.10+
- TestRail account with API access
- `.mm` file exported from MindMeister

Install dependencies:
```bash
pip install python-dotenv
````

(Ensure `testrail` client and `utils.py` are available in your project.)

## Setup

Create a `.env` file:

```ini
TESTRAIL_URL="https://appier.testrail.io/"
TESTRAIL_USER="you@company.com"
TESTRAIL_PASSWORD_OR_KEY="YOUR_API_KEY"
```

## Usage

### Import test cases

```bash
python mindmeister_to_testrail.py \
  --mm_path path/to/mindmap.mm \
  --project_id 123 \
  --suite_id 456
```

### If you wish to re-run the code to add the cases to testrail after test case modification

Uncomment in `__main__`:

```python
uploader.delete_all_sections() # clears test suite before adding test cases
```

Run the same command as above.

## Notes

* Top-level nodes in the mind map become sections; leaf/untitled-child nodes become cases.
* Case descriptions come from NOTE content in the `.mm` file.
* Cases are created in the `custom_steps` field by default—adjust in `_process_as_case` if needed.
