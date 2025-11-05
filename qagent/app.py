from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
import os
import json
import tempfile
import shutil
from werkzeug.utils import secure_filename
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append('backend')

# Import the refactored classes
try:
    from backend.prd_to_specs import PRDExtractor
    from backend.parse_figma_frame import FigmaFrameParser
    from backend.summarize_figma_data import FigmaSummarizer
    from backend.generate_test_plan import TestPlanGenerator
    from backend.generate_detailed_tests import DetailedTestGenerator
    from backend.json_to_md_formatter import MarkdownFormatter
    BACKEND_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Backend classes not available: {e}")
    BACKEND_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

# Configuration
# UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'md'}

# Create directories if they don't exist
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_prompt_template_path(template_name):
    """Get the correct path to prompt template files"""
    base_path = Path(__file__).parent
    return str(base_path / "backend" / "prompt_templates" / template_name)

def check_api_keys():
    """Check if required API keys are available in environment or .env file"""
    # First try loading from .env file
    load_dotenv()
    
    gemini_key = os.environ.get('GEMINI_API_KEY')
    figma_token = os.environ.get('FIGMA_ACCESS_TOKEN')
    
    # Check both system environment and .env file
    missing_keys = []
    if not gemini_key:
        missing_keys.append('GEMINI_API_KEY')
    if not figma_token:
        missing_keys.append('FIGMA_ACCESS_TOKEN')
    
    return missing_keys

class TestPlannerDemo:
    """Demo class that orchestrates the test planning workflow"""
    
    def __init__(self):
        if not BACKEND_AVAILABLE:
            raise RuntimeError("Backend classes are not available")
        
        # Check for missing API keys
        missing_keys = check_api_keys()
        if missing_keys:
            print(f"Warning: Missing API keys: {', '.join(missing_keys)}")
            print("The application will run in demo mode with mock data")
            self.demo_mode = True
        else:
            self.demo_mode = False
        
        # Initialize all the service classes
        try:
            self.prd_extractor = PRDExtractor()
            self.figma_parser = FigmaFrameParser()
            self.figma_summarizer = FigmaSummarizer()
            self.test_plan_generator = TestPlanGenerator()
            self.detailed_test_generator = DetailedTestGenerator()
            self.markdown_formatter = MarkdownFormatter()
        except Exception as e:
            print(f"Error initializing backend classes: {e}")
            self.demo_mode = True
    
    def run_workflow(self, prd_file_path, figma_url, output_dir, trust_mode=True):
        """Run the complete test planning workflow"""
        try:
            if self.demo_mode:
                return self._run_demo_workflow(prd_file_path, figma_url, output_dir, trust_mode)
            if trust_mode:
                return self._run_trust_workflow(prd_file_path, figma_url, output_dir)
            else:
                return self._run_checkpoint_workflow(prd_file_path, figma_url, output_dir)
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _run_trust_workflow(self, prd_file_path, figma_url, output_dir):
        """Run workflow in trust mode (automatic)"""
        # Step 1: Extract PRD context
        print("Step 1: Extracting PRD context...")
        prd_context = self.prd_extractor.extract_prd_from_file(
            prd_file_path, 
            get_prompt_template_path("prd_reader.yaml")
        )
        self.prd_extractor.save_prd_context(prd_context, f"{output_dir}/prd_context.json")
        
        # Step 2: Parse Figma design (optional)
        figma_data = None
        figma_summary = ""
        if figma_url and figma_url.strip():
            print("Step 2: Parsing Figma design...")
            figma_data = self.figma_parser.parse_figma_frame_from_url(figma_url)
            self.figma_parser.save_figma_data(figma_data, f"{output_dir}/figma_data.json")
            
            # Step 3: Summarize Figma data
            print("Step 3: Summarizing Figma data...")
            figma_summary = self.figma_summarizer.generate_figma_summary(
                f"{output_dir}/figma_data.json",
                get_prompt_template_path("uiux_consultant.yaml")
            )
            self.figma_summarizer.save_figma_summary(figma_summary, f"{output_dir}/figma_summary.txt")
        else:
            print("Step 2: Skipping Figma parsing (no URL provided)")
            # Create empty figma files for consistency
            with open(f"{output_dir}/figma_data.json", "w") as f:
                json.dump({}, f)
            with open(f"{output_dir}/figma_summary.txt", "w") as f:
                f.write("No Figma data provided")
        
        # Step 4: Generate test plan
        print("Step 4: Generating test plan...")
        test_plan = self.test_plan_generator.generate_test_plan_from_files(
            context_path=f"{output_dir}/prd_context.json",
            figma_path=f"{output_dir}/figma_summary.txt",
            prompt_path=get_prompt_template_path("test_planner.yaml")
        )
        self.test_plan_generator.save_test_plan(test_plan, f"{output_dir}/test_plan.json")
        
        # Step 5: Convert test plan to Markdown
        print("Step 5: Converting test plan to Markdown...")
        test_plan_md = self.markdown_formatter.convert_test_plan_json_to_md(test_plan)
        with open(f"{output_dir}/test_plan.md", "w") as f:
            f.write(test_plan_md)
        
        # # Detailed Test Cases are Deprecated for now
        # # Step 6: Generate detailed test cases
        # print("Step 6: Generating detailed test cases...")
        # detailed_tests = self.detailed_test_generator.generate_detailed_test_suite(
        #     test_plan_path=f"{output_dir}/test_plan.md",
        #     prompt_file_path=get_prompt_template_path("test_designer.yaml"),
        #     figma_summary_path=f"{output_dir}/figma_summary.txt",
        #     max_test_cases=3
        # )
        # self.detailed_test_generator.save_test_suite(detailed_tests, f"{output_dir}/test_suite.json")
        
        # # Step 7: Convert detailed tests to Markdown
        # print("Step 7: Converting detailed tests to Markdown...")
        # test_suite_md = self.markdown_formatter.convert_test_suite_json_to_md(detailed_tests)
        # with open(f"{output_dir}/test_suite.md", "w") as f:
        #     f.write(test_suite_md)
        detailed_tests = {"WIP": "Detailed test cases."}
        self.detailed_test_generator.save_test_suite(detailed_tests, f"{output_dir}/test_suite.json")
        with open(f"{output_dir}/test_suite.md", "w") as f:
            f.write("WIP: " + detailed_tests['WIP'])


        return {
            "success": True,
            "prd_context": prd_context,
            "figma_data": figma_data,
            "figma_summary": figma_summary,
            "test_plan": test_plan,
            "detailed_tests": detailed_tests,
            "trust_mode": True,
            "output_files": {
                "prd_context": f"{output_dir}/prd_context.json",
                "figma_data": f"{output_dir}/figma_data.json",
                "figma_summary": f"{output_dir}/figma_summary.txt",
                "test_plan_json": f"{output_dir}/test_plan.json",
                "test_plan_md": f"{output_dir}/test_plan.md",
                "test_suite_json": f"{output_dir}/test_suite.json",
                "test_suite_md": f"{output_dir}/test_suite.md"
            }
        }
    
    def _run_checkpoint_workflow(self, prd_file_path, figma_url, output_dir):
        """Run workflow in checkpoint mode (manual review)"""
        # Step 1: Extract PRD context
        print("Step 1: Extracting PRD context...")
        prd_context = self.prd_extractor.extract_prd_from_file(
            prd_file_path, 
            get_prompt_template_path("prd_reader.yaml")
        )
        self.prd_extractor.save_prd_context(prd_context, f"{output_dir}/prd_context.json")
        
        # Save workflow state for checkpoint
        workflow_state = {
            "session_id": os.path.basename(output_dir),
            "prd_file_path": prd_file_path,
            "figma_url": figma_url,
            "output_dir": output_dir,
            "current_step": 1,
            "prd_context": prd_context
        }
        
        with open(f"{output_dir}/workflow_state.json", "w") as f:
            json.dump(workflow_state, f, indent=2)
        
        return {
            "success": True,
            "workflow_state": workflow_state,
            "checkpoint": 1,
            "content": json.dumps(prd_context, indent=2),
            "original_content": json.dumps(prd_context, indent=2),
            "content_type": "PRD Context",
            "trust_mode": False
        }
    
    def continue_checkpoint_workflow(self, session_id, checkpoint, content=None):
        """Continue workflow from a specific checkpoint"""
        output_dir = os.path.join(OUTPUT_FOLDER, session_id)
        
        # Load workflow state
        with open(f"{output_dir}/workflow_state.json", "r") as f:
            workflow_state = json.load(f)
        
        # Update content if provided
        if content:
            if checkpoint == 1:
                # Update PRD context
                updated_context = json.loads(content)
                workflow_state["prd_context"] = updated_context
                self.prd_extractor.save_prd_context(updated_context, f"{output_dir}/prd_context.json")
            elif checkpoint == 2:
                # Update Figma summary
                with open(f"{output_dir}/figma_summary.txt", "w") as f:
                    f.write(content)
            elif checkpoint == 3:
                # For test plan, we need to convert markdown back to JSON
                # This is a simplified approach - in production you might want more robust parsing
                try:
                    # Try to parse as JSON first (in case user pasted JSON)
                    updated_test_plan = json.loads(content)
                except json.JSONDecodeError:
                    # If it's markdown, we'll need to regenerate the test plan
                    # For now, we'll save the markdown and regenerate JSON
                    with open(f"{output_dir}/test_plan.md", "w") as f:
                        f.write(content)
                    
                    # Regenerate JSON from the updated markdown
                    # This is a simplified approach - you might want more sophisticated parsing
                    updated_test_plan = workflow_state.get("test_plan", {})
                
                self.test_plan_generator.save_test_plan(updated_test_plan, f"{output_dir}/test_plan.json")
                test_plan_md = self.markdown_formatter.convert_test_plan_json_to_md(updated_test_plan)
                with open(f"{output_dir}/test_plan.md", "w") as f:
                    f.write(test_plan_md)
        
        # Continue from checkpoint
        if checkpoint == 1:
            # Step 2: Parse Figma design (optional)
            figma_data = None
            figma_summary = ""
            if workflow_state.get("figma_url") and workflow_state["figma_url"].strip():
                print("Step 2: Parsing Figma design...")
                figma_data = self.figma_parser.parse_figma_frame_from_url(workflow_state["figma_url"])
                self.figma_parser.save_figma_data(figma_data, f"{output_dir}/figma_data.json")
                
                # Step 3: Summarize Figma data
                print("Step 3: Summarizing Figma data...")
                figma_summary = self.figma_summarizer.generate_figma_summary(
                    f"{output_dir}/figma_data.json",
                    get_prompt_template_path("uiux_consultant.yaml")
                )
                self.figma_summarizer.save_figma_summary(figma_summary, f"{output_dir}/figma_summary.txt")
            else:
                print("Step 2: Skipping Figma parsing (no URL provided)")
                # Create empty figma files for consistency
                with open(f"{output_dir}/figma_data.json", "w") as f:
                    json.dump({}, f)
                with open(f"{output_dir}/figma_summary.txt", "w") as f:
                    f.write("No Figma data provided")
            
            # Update workflow state
            workflow_state["current_step"] = 2
            workflow_state["figma_data"] = figma_data
            workflow_state["figma_summary"] = figma_summary
            
            with open(f"{output_dir}/workflow_state.json", "w") as f:
                json.dump(workflow_state, f, indent=2)
            
            return {
                "success": True,
                "workflow_state": workflow_state,
                "checkpoint": 2,
                "content": figma_summary,
                "original_content": figma_summary,
                "content_type": "Figma Summary",
                "trust_mode": False
            }
            
        elif checkpoint == 2:
            # Step 4: Generate test plan
            print("Step 4: Generating test plan...")
            test_plan = self.test_plan_generator.generate_test_plan_from_files(
                context_path=f"{output_dir}/prd_context.json",
                figma_path=f"{output_dir}/figma_summary.txt",
                prompt_path=get_prompt_template_path("test_planner.yaml")
            )
            self.test_plan_generator.save_test_plan(test_plan, f"{output_dir}/test_plan.json")
            
            # Convert to markdown for easier editing
            test_plan_md = self.markdown_formatter.convert_test_plan_json_to_md(test_plan)
            with open(f"{output_dir}/test_plan.md", "w") as f:
                f.write(test_plan_md)
            
            # Update workflow state
            workflow_state["current_step"] = 3
            workflow_state["test_plan"] = test_plan
            
            with open(f"{output_dir}/workflow_state.json", "w") as f:
                json.dump(workflow_state, f, indent=2)
                f.close()
            
            return {
                "success": True,
                "workflow_state": workflow_state,
                "checkpoint": 3,
                "content": test_plan_md,
                "original_content": test_plan_md,
                "content_type": "Test Plan",
                "trust_mode": False
            }
            
        elif checkpoint == 3:
            # # Step 5: Generate detailed test cases
            # print("Step 5: Generating detailed test cases...")
            # detailed_tests = self.detailed_test_generator.generate_detailed_test_suite(
            #     test_plan_path=f"{output_dir}/test_plan.md",
            #     prompt_file_path=get_prompt_template_path("test_designer.yaml"),
            #     figma_summary_path=f"{output_dir}/figma_summary.txt",
            #     max_test_cases=3
            # )
            # self.detailed_test_generator.save_test_suite(detailed_tests, f"{output_dir}/test_suite.json")
            
            # # Step 6: Convert detailed tests to Markdown
            # print("Step 6: Converting detailed tests to Markdown...")
            # test_suite_md = self.markdown_formatter.convert_test_suite_json_to_md(detailed_tests)
            # with open(f"{output_dir}/test_suite.md", "w") as f:
            #     f.write(test_suite_md)

            detailed_tests = {"WIP": "Detailed test cases."}
            self.detailed_test_generator.save_test_suite(detailed_tests, f"{output_dir}/test_suite.json")
            with open(f"{output_dir}/test_suite.md", "w") as f:
                f.write("WIP: " + detailed_tests['WIP'])
            
            # Load all results for final display
            with open(f"{output_dir}/prd_context.json", "r") as f:
                prd_context = json.load(f)

            with open(f"{output_dir}/figma_data.json", "r") as f:
                figma_data = json.load(f)
            
            with open(f"{output_dir}/figma_summary.txt", "r") as f:
                figma_summary = f.read()
            
            with open(f"{output_dir}/test_plan.json", "r") as f:
                test_plan = json.load(f)
            
            return {
                "success": True,
                "prd_context": prd_context,
                "figma_summary": figma_summary,
                "figma_data": figma_data,
                "test_plan": test_plan,
                "detailed_tests": detailed_tests,
                "trust_mode": False,
                "output_files": {
                    "prd_context": f"{output_dir}/prd_context.json",
                    "figma_data": f"{output_dir}/figma_data.json",
                    "figma_summary": f"{output_dir}/figma_summary.txt",
                    "test_plan_json": f"{output_dir}/test_plan.json",
                    "test_plan_md": f"{output_dir}/test_plan.md",
                    "test_suite_json": f"{output_dir}/test_suite.json",
                    "test_suite_md": f"{output_dir}/test_suite.md"
                }
            }
    
    def _run_demo_workflow(self, prd_file_path, figma_url, output_dir, trust_mode=True):
        """Run demo workflow with mock data"""
        # Import demo mode functionality
        from demo_mode import create_mock_data
        
        # Generate mock data
        mock_data = create_mock_data()
        
        if trust_mode:
            # Save mock data to files
            with open(f"{output_dir}/prd_context.json", 'w') as f:
                json.dump(mock_data['prd_context'], f, indent=2)
            
            with open(f"{output_dir}/test_plan.json", 'w') as f:
                json.dump(mock_data['test_plan'], f, indent=2)
            
            with open(f"{output_dir}/test_suite.json", 'w') as f:
                json.dump(mock_data['detailed_tests'], f, indent=2)
            
            with open(f"{output_dir}/figma_summary.txt", 'w') as f:
                f.write(mock_data['figma_summary'])
            
            # Convert to markdown
            test_plan_md = self.markdown_formatter.convert_test_plan_json_to_md(mock_data['test_plan'])
            with open(f"{output_dir}/test_plan.md", 'w') as f:
                f.write(test_plan_md)
            
            test_suite_md = self.markdown_formatter.convert_test_suite_json_to_md(mock_data['detailed_tests'])
            with open(f"{output_dir}/test_suite.md", 'w') as f:
                f.write(test_suite_md)
            
            return {
                "success": True,
                "prd_context": mock_data['prd_context'],
                "test_plan": mock_data['test_plan'],
                "detailed_tests": mock_data['detailed_tests'],
                "figma_summary": mock_data['figma_summary'],
                "test_plan_md": test_plan_md,
                "test_suite_md": test_suite_md,
                "demo_mode": True,
                "trust_mode": True,
                "output_files": {
                    "prd_context": f"{output_dir}/prd_context.json",
                    "figma_data": f"{output_dir}/figma_data.json",
                    "figma_summary": f"{output_dir}/figma_summary.txt",
                    "test_plan_json": f"{output_dir}/test_plan.json",
                    "test_plan_md": f"{output_dir}/test_plan.md",
                    "test_suite_json": f"{output_dir}/test_suite.json",
                    "test_suite_md": f"{output_dir}/test_suite.md"
                }
            }
        else:
            # Demo checkpoint mode
            session_id = os.path.basename(output_dir)
            workflow_state = {
                "session_id": session_id,
                "prd_file_path": prd_file_path,
                "figma_url": figma_url,
                "output_dir": output_dir,
                "current_step": 1,
                "prd_context": mock_data['prd_context'],
                "demo_mode": True
            }
            
            with open(f"{output_dir}/workflow_state.json", "w") as f:
                json.dump(workflow_state, f, indent=2)
            
            return {
                "success": True,
                "workflow_state": workflow_state,
                "checkpoint": 1,
                "content": json.dumps(mock_data['prd_context'], indent=2),
                "original_content": json.dumps(mock_data['prd_context'], indent=2),
                "content_type": "PRD Context",
                "trust_mode": False,
                "demo_mode": True
            }

# Initialize the demo planner
try:
    demo_planner = TestPlannerDemo()
    PLANNER_AVAILABLE = True
except Exception as e:
    print(f"Error initializing planner: {e}")
    demo_planner = None
    PLANNER_AVAILABLE = False

@app.route('/')
def index():
    """Main page with upload form"""
    if not PLANNER_AVAILABLE:
        flash('Test planner is not available. Please check your configuration.')
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and Figma URL"""
    if not PLANNER_AVAILABLE:
        flash('Test planner is not available. Please check your configuration.')
        return redirect(url_for('index'))
    
    if 'prd_file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['prd_file']
    figma_url = request.form.get('figma_url', '').strip()
    trust_mode = request.form.get('trust_mode') == 'on'
    
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    # Figma URL is now optional
    if not figma_url:
        print('No Figma URL provided - proceeding without Figma data')
    
    if file and allowed_file(file.filename):
        # Create a unique output directory
        import uuid
        session_id = str(uuid.uuid4())[:8]
        output_dir = os.path.join(OUTPUT_FOLDER, session_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(output_dir, filename)
        file.save(file_path)
        
        # Run the workflow
        result = demo_planner.run_workflow(file_path, figma_url, output_dir, trust_mode)
        
        if result['success']:
            if trust_mode:
                # Trust mode - redirect to results page
                return redirect(url_for('results', session_id=session_id))
            else:
                # Checkpoint mode - show first checkpoint
                return render_template('checkpoint.html',
                                     session_id=session_id,
                                     checkpoint_step=result['checkpoint'],
                                     content=result['content'],
                                     original_content=result['original_content'],
                                     content_type=result['content_type'],
                                     checkpoint_title="PRD Context Review",
                                     checkpoint_description="Review and modify the extracted PRD information",
                                     checkpoint_icon="file-alt")
        else:
            flash(f'Error: {result["error"]}')
            return redirect(url_for('index'))
    
    flash('Invalid file type')
    return redirect(url_for('index'))

@app.route('/checkpoint/<session_id>/<int:checkpoint>', methods=['GET', 'POST'])
def checkpoint_proceed(session_id, checkpoint):
    """Handle checkpoint review and proceed to next step (Unified for demo and backend)"""
    output_dir = os.path.join(OUTPUT_FOLDER, session_id)
    if not os.path.exists(output_dir):
        flash('Session not found')
        return redirect(url_for('index'))

    # Use demo mode if planner is in demo mode
    demo_mode = getattr(demo_planner, 'demo_mode', False)

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        action = request.form.get('action', 'proceed')
        if not content:
            flash('Content cannot be empty')
            return redirect(request.url)
        if action == 'skip':
            content = None
        if demo_mode:
            # Demo mode: just save content to file
            if checkpoint == 1 and content:
                with open(os.path.join(output_dir, 'prd_context.json'), 'w') as f:
                    f.write(content)
            elif checkpoint == 2 and content:
                with open(os.path.join(output_dir, 'figma_summary.txt'), 'w') as f:
                    f.write(content)
            elif checkpoint == 3 and content:
                with open(os.path.join(output_dir, 'test_plan.md'), 'w') as f:
                    f.write(content)
            if checkpoint < 3:
                return redirect(url_for('checkpoint_proceed', session_id=session_id, checkpoint=checkpoint+1))
            else:
                return redirect(url_for('results', session_id=session_id))
        else:
            # Backend mode: use planner's checkpoint logic
            result = demo_planner.continue_checkpoint_workflow(session_id, checkpoint, content)
            if result['success']:
                if result.get('output_files'):
                    return redirect(url_for('results', session_id=session_id))
                else:
                    checkpoint_info = {
                        2: {
                            "title": "Figma Summary Review",
                            "description": "Review and modify the Figma design analysis",
                            "icon": "palette"
                        },
                        3: {
                            "title": "Test Plan Review",
                            "description": "Review and modify the generated test plan",
                            "icon": "clipboard-list"
                        }
                    }
                    info = checkpoint_info.get(result['checkpoint'])
                    return render_template('checkpoint.html',
                                         session_id=session_id,
                                         checkpoint_step=result['checkpoint'],
                                         content=result['content'],
                                         original_content=result['original_content'],
                                         content_type=result['content_type'],
                                         checkpoint_title=info['title'],
                                         checkpoint_description=info['description'],
                                         checkpoint_icon=info['icon'])
            else:
                flash(f'Error: {result.get("error", "Unknown error")}')
                return redirect(url_for('index'))

    # GET request - show current checkpoint
    try:
        if demo_mode:
            # Demo mode: load content from files
            if checkpoint == 1:
                with open(os.path.join(output_dir, 'prd_context.json'), 'r') as f:
                    content = f.read()
                original_content = content
                content_type = "PRD Context"
                title = "PRD Context Review"
                description = "Review and modify the extracted PRD information"
                icon = "file-alt"
            elif checkpoint == 2:
                with open(os.path.join(output_dir, 'figma_summary.txt'), 'r') as f:
                    content = f.read()
                original_content = content
                content_type = "Figma Summary"
                title = "Figma Summary Review"
                description = "Review and modify the Figma design analysis"
                icon = "palette"
            elif checkpoint == 3:
                with open(os.path.join(output_dir, 'test_plan.md'), 'r') as f:
                    content = f.read()
                original_content = content
                content_type = "Test Plan"
                title = "Test Plan Review"
                description = "Review and modify the generated test plan"
                icon = "clipboard-list"
            else:
                flash('Invalid checkpoint')
                return redirect(url_for('index'))
            return render_template('checkpoint.html',
                                  session_id=session_id,
                                  checkpoint_step=checkpoint,
                                  content=content,
                                  original_content=original_content,
                                  content_type=content_type,
                                  checkpoint_title=title,
                                  checkpoint_description=description,
                                  checkpoint_icon=icon)
        else:
            # Backend mode: load from workflow state
            with open(os.path.join(output_dir, 'workflow_state.json'), 'r') as f:
                workflow_state = json.load(f)
            if checkpoint == 1:
                content = json.dumps(workflow_state['prd_context'], indent=2)
                original_content = content
                content_type = "PRD Context"
                title = "PRD Context Review"
                description = "Review and modify the extracted PRD information"
                icon = "file-alt"
            elif checkpoint == 2:
                with open(os.path.join(output_dir, 'figma_summary.txt'), 'r') as f:
                    content = f.read()
                original_content = content
                content_type = "Figma Summary"
                title = "Figma Summary Review"
                description = "Review and modify the Figma design analysis"
                icon = "palette"
            elif checkpoint == 3:
                with open(os.path.join(output_dir, 'test_plan.md'), 'r') as f:
                    content = f.read()
                original_content = content
                content_type = "Test Plan"
                title = "Test Plan Review"
                description = "Review and modify the generated test plan"
                icon = "clipboard-list"
            else:
                flash('Invalid checkpoint')
                return redirect(url_for('index'))
            return render_template('checkpoint.html',
                                  session_id=session_id,
                                  checkpoint_step=checkpoint,
                                  content=content,
                                  original_content=original_content,
                                  content_type=content_type,
                                  checkpoint_title=title,
                                  checkpoint_description=description,
                                  checkpoint_icon=icon)
    except Exception as e:
        flash(f'Error loading checkpoint: {str(e)}')
        return redirect(url_for('index'))

@app.route('/results/', defaults={'session_id': None})
@app.route('/results/<session_id>')
def results(session_id):
    """Display results for a specific session"""
    # If no session_id in path, try to get it from query parameters
    if session_id is None:
        session_id = request.args.get('session_id')
        if not session_id:
            flash('Session ID is required')
            return redirect(url_for('index'))
        print(f"Redirecting query parameter session_id={session_id} to path URL")
        # Redirect to canonical URL with session_id in path
        return redirect(url_for('results', session_id=session_id))
    
    output_dir = os.path.join(OUTPUT_FOLDER, session_id)
    print(f"Looking for results in directory: {output_dir}")
    
    if not os.path.exists(output_dir):
        print(f"Output directory not found for session ID: {session_id}")
        flash('Results not found for session ID: ' + session_id)
        return redirect(url_for('index'))
    print(f"Found output directory for session ID: {session_id}")
    # Load results from files
    try:
        required_files = {
            'prd_context.json': None,
            'test_plan.json': None,
            'test_suite.json': None,
            'figma_summary.txt': None,
            'test_plan.md': None,
            'test_suite.md': None
        }
        
        # Check all required files exist first
        for filename in required_files:
            file_path = os.path.join(output_dir, filename)
            if not os.path.exists(file_path):
                print(f"Missing required file: {filename}")
            
        # Now load all files
        def validate_json_file(filepath, filename):
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        print(f"JSON Parse Error in {filename} at position {e.pos}:")
                        print(f"Line {e.lineno}, Column {e.colno}")
                        print(f"Error message: {e.msg}")
                        # Show the problematic line and position
                        lines = content.split('\n')
                        if e.lineno <= len(lines):
                            print(f"Problematic line: {lines[e.lineno - 1]}")
                            print(f"                  {' ' * (e.colno - 1)}^")
                        raise
            except Exception as e:
                print(f"Error reading {filename}: {str(e)}")
                raise

        try:
            prd_context = validate_json_file(
                os.path.join(output_dir, 'prd_context.json'),
                'prd_context.json'
            )
        except json.JSONDecodeError as e:
            print(f"Error parsing prd_context.json: {str(e)}")
            raise

        try:
            test_plan = validate_json_file(
                os.path.join(output_dir, 'test_plan.json'),
                'test_plan.json'
            )
        except json.JSONDecodeError as e:
            print(f"Error parsing test_plan.json: {str(e)}")
            raise

        try:
            detailed_tests = validate_json_file(
                os.path.join(output_dir, 'test_suite.json'),
                'test_suite.json'
            )
        except json.JSONDecodeError as e:
            print(f"Error parsing test_suite.json: {str(e)}")
            raise
        
        try:
            with open(os.path.join(output_dir, 'figma_summary.txt'), 'r') as f:
                figma_summary = f.read()
        except Exception as e:
            print(f"Error reading figma_summary.txt: {str(e)}")
            raise
        
        try:
            with open(os.path.join(output_dir, 'test_plan.md'), 'r') as f:
                test_plan_md = f.read()
        except Exception as e:
            print(f"Error reading test_plan.md: {str(e)}")
            raise
        
        try:
            with open(os.path.join(output_dir, 'test_suite.md'), 'r') as f:
                test_suite_md = f.read()
        except Exception as e:
            print(f"Error reading test_suite.md: {str(e)}")
            raise
        
        print(f"Successfully loaded all result files for session ID: {session_id}")
        
        result = {
            "prd_context": prd_context,
            "test_plan": test_plan,
            "detailed_tests": detailed_tests,
            "figma_summary": figma_summary,
            "test_plan_md": test_plan_md,
            "test_suite_md": test_suite_md
        }
        
        try:
            # Validate result data structure before rendering
            print("\nValidating result data structure:")
            for key, value in result.items():
                print(f"Checking {key}:")
                if isinstance(value, (dict, list)):
                    # For JSON data, validate it can be re-serialized
                    try:
                        json.dumps(value)
                        print(f"  ✓ Valid JSON data")
                    except TypeError as e:
                        print(f"  ✗ Invalid JSON data: {str(e)}")
                        raise ValueError(f"Invalid data in {key}: {str(e)}")
                elif isinstance(value, str):
                    print(f"  ✓ Valid string data")
                else:
                    print(f"  ? Unexpected type: {type(value)}")
            
            print("\nAttempting to render template...")
            return render_template('results.html', result=result, session_id=session_id)
        except Exception as e:
            print(f"Error rendering results template: {str(e)}")
            print("Template context:")
            for key, value in result.items():
                print(f"{key}: {type(value)}")
                if isinstance(value, (dict, list)):
                    print(f"Preview: {str(value)[:200]}...")
            flash(f'Error displaying results: {str(e)}')
            return redirect(url_for('index'))
        
    except FileNotFoundError as e:
        print(f"File not found error: {str(e)}")
        flash(str(e))
        return redirect(url_for('index'))
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        flash(f'Error parsing result files: {str(e)}')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Unexpected error loading results: {str(e)}")
        flash(f'Error loading results: {str(e)}')
        return redirect(url_for('index'))

@app.route('/download/<session_id>/<file_type>')
def download_file(session_id, file_type):
    """Download generated files"""
    output_dir = os.path.join(OUTPUT_FOLDER, session_id)
    
    file_mapping = {
        'prd_context': 'prd_context.json',
        'test_plan_json': 'test_plan.json',
        'test_plan_md': 'test_plan.md',
        'test_suite_json': 'test_suite.json',
        'test_suite_md': 'test_suite.md',
        'figma_summary': 'figma_summary.txt'
    }
    
    if file_type not in file_mapping:
        flash('Invalid file type')
        return redirect(url_for('index'))
    
    file_path = os.path.join(output_dir, file_mapping[file_type])
    
    if not os.path.exists(file_path):
        flash('File not found')
        return redirect(url_for('index'))
    
    return send_file(file_path, as_attachment=True)

@app.route('/save_test_plan/<session_id>', methods=['POST'])
def save_test_plan(session_id):
    """Save edited test plan content"""
    output_dir = os.path.join(OUTPUT_FOLDER, session_id)
    
    if not os.path.exists(output_dir):
        return jsonify({'success': False, 'error': 'Session not found'})
    
    try:
        # Get the edited content from the request
        edited_content = request.json.get('content')
        if not edited_content:
            return jsonify({'success': False, 'error': 'No content provided'})
        
        print(f"Received content length: {len(edited_content)}")
        print(f"Content preview: {edited_content[:200]}...")
        
        # Try to parse as JSON first
        try:
            updated_test_plan = json.loads(edited_content)
            print("Successfully parsed JSON")
            
            # Save the JSON file
            json_path = os.path.join(output_dir, 'test_plan.json')
            with open(json_path, 'w') as f:
                json.dump(updated_test_plan, f, indent=2)
            print(f"Saved JSON to: {json_path}")
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return jsonify({'success': False, 'error': f'Invalid JSON format: {str(e)}'})
        
        # Convert the updated JSON to markdown and save
        if demo_planner and hasattr(demo_planner, 'markdown_formatter'):
            try:
                test_plan_md = demo_planner.markdown_formatter.convert_test_plan_json_to_md(updated_test_plan)
                md_path = os.path.join(output_dir, 'test_plan.md')
                with open(md_path, 'w') as f:
                    f.write(test_plan_md)
                print(f"Saved Markdown to: {md_path}")
            except Exception as e:
                print(f"Error converting to markdown: {e}")
                return jsonify({'success': False, 'error': f'Error converting to markdown: {str(e)}'})
        
        return jsonify({
            'success': True, 
            'message': 'Test plan saved successfully',
            'updated_content': edited_content
        })
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/upload_to_testrail/<session_id>', methods=['POST'])
def upload_to_testrail(session_id):
    """Upload test plan to TestRail"""
    output_dir = os.path.join(OUTPUT_FOLDER, session_id)
    
    if not os.path.exists(output_dir):
        return jsonify({'success': False, 'error': 'Session not found'})
    
    try:
        # Get TestRail configuration from request
        data = request.json
        project_id = data.get('project_id')
        suite_id = data.get('suite_id')
        
        if not project_id or not suite_id:
            return jsonify({'success': False, 'error': 'Project ID and Suite ID are required'})
        
        # Check if TestRail credentials are available
        testrail_url = os.environ.get('TESTRAIL_URL')
        testrail_user = os.environ.get('TESTRAIL_USER')
        testrail_key = os.environ.get('TESTRAIL_PASSWORD_OR_KEY')
        
        if not all([testrail_url, testrail_user, testrail_key]):
            return jsonify({
                'success': False, 
                'error': 'TestRail credentials not configured. Please set TESTRAIL_URL, TESTRAIL_USER, and TESTRAIL_PASSWORD_OR_KEY environment variables.'
            })
        
        # Import TestRail uploader
        try:
            from backend.upload_to_testrail import TestRailUploader
        except ImportError as e:
            return jsonify({'success': False, 'error': f'TestRail uploader not available: {str(e)}'})
        
        # Path to the test plan JSON file
        json_path = os.path.join(output_dir, 'test_plan.json')
        
        if not os.path.exists(json_path):
            return jsonify({'success': False, 'error': 'Test plan JSON file not found'})
        
        # Create uploader and upload
        try:
            uploader = TestRailUploader(json_path, int(project_id), int(suite_id))
            uploader.delete_all_sections()
            uploader.upload_test_plan()
            
            # Generate TestRail URL
            testrail_base_url = testrail_url.rstrip('/')
            testrail_suite_url = f"{testrail_base_url}/index.php?/suites/view/{suite_id}"
            
            return jsonify({
                'success': True,
                'message': 'Test plan uploaded to TestRail successfully',
                'testrail_url': testrail_suite_url,
                'project_id': project_id,
                'suite_id': suite_id
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error uploading to TestRail: {str(e)}'})
        
    except Exception as e:
        print(f"Unexpected error in TestRail upload: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health_check():
    """Health check endpoint for deployment"""
    return jsonify({
        "status": "healthy",
        "backend_available": BACKEND_AVAILABLE,
        "planner_available": PLANNER_AVAILABLE,
        "demo_mode": demo_planner.demo_mode if demo_planner else None
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') == 'development'
    load_dotenv()
    
    print("🚀 Starting Test Planner with Trust Mode Toggle")
    print(f"🌐 Access the app at: http://localhost:{port}")
    
    if not BACKEND_AVAILABLE:
        print("⚠️  Backend classes not available - running in demo mode")
    elif demo_planner and demo_planner.demo_mode:
        print("⚠️  Missing API keys - running in demo mode")
    else:
        print("✅ Full functionality available")
    
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=port)