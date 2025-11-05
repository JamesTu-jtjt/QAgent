"""
Example demonstrating how to use the refactored classes in a backend API context.

This file shows how to integrate all the test planning classes into a Flask/FastAPI backend
or any other web framework.
"""

import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Import all the refactored classes
from prd_to_specs import PRDExtractor
from parse_figma_frame import FigmaFrameParser
from summarize_figma_data import FigmaSummarizer
from generate_test_plan import TestPlanGenerator
from generate_detailed_tests import DetailedTestGenerator
from json_to_md_formatter import MarkdownFormatter


class TestPlanningAPI:
    """
    Main API class that orchestrates the entire test planning workflow.
    
    This class demonstrates how to use all the refactored classes together
    to create a complete test planning pipeline.
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None, figma_token: Optional[str] = None):
        """
        Initialize the TestPlanningAPI with all required services.
        
        Args:
            gemini_api_key: Gemini API key for AI operations
            figma_token: Figma access token for design parsing
        """
        # Load environment variables if not provided
        if gemini_api_key is None or figma_token is None:
            load_dotenv()
            if gemini_api_key is None:
                gemini_api_key = os.getenv("GEMINI_API_KEY")
            if figma_token is None:
                figma_token = os.getenv("FIGMA_ACCESS_TOKEN")
        
        # Initialize all service classes
        self.prd_extractor = PRDExtractor(api_key=gemini_api_key)
        self.figma_parser = FigmaFrameParser(access_token=figma_token)
        self.figma_summarizer = FigmaSummarizer(api_key=gemini_api_key)
        self.test_plan_generator = TestPlanGenerator(api_key=gemini_api_key)
        self.detailed_test_generator = DetailedTestGenerator(api_key=gemini_api_key)
        self.markdown_formatter = MarkdownFormatter()
    
    def extract_prd_context(self, prd_file_path: str) -> Dict[str, Any]:
        """
        Extract structured context from a PRD file.
        
        Args:
            prd_file_path: Path to PRD file (PDF or text)
            
        Returns:
            Extracted PRD context
        """
        return self.prd_extractor.extract_prd_from_file(prd_file_path)
    
    def parse_figma_design(self, figma_url: str) -> Dict[str, Any]:
        """
        Parse Figma design and extract interactive components.
        
        Args:
            figma_url: Figma design URL
            
        Returns:
            Parsed Figma data
        """
        return self.figma_parser.parse_figma_frame_from_url(figma_url)
    
    def summarize_figma_data(self, figma_data: Dict[str, Any]) -> str:
        """
        Generate natural language summary from Figma data.
        
        Args:
            figma_data: Parsed Figma data
            
        Returns:
            Generated summary
        """
        # Save figma data temporarily for the summarizer
        temp_path = "temp_figma_data.json"
        self.figma_parser.save_figma_data(figma_data, temp_path)
        
        try:
            summary = self.figma_summarizer.generate_figma_summary(temp_path)
            return summary
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def generate_test_plan(self, prd_context: Dict[str, Any], figma_summary: str = "") -> Dict[str, Any]:
        """
        Generate test plan from PRD context and optional Figma summary.
        
        Args:
            prd_context: Extracted PRD context
            figma_summary: Generated Figma summary (optional)
            
        Returns:
            Generated test plan
        """
        # Save PRD context temporarily
        temp_prd_path = "temp_prd_context.json"
        self.prd_extractor.save_prd_context(prd_context, temp_prd_path)
        
        # Save Figma summary temporarily (or create empty file if no summary)
        temp_figma_path = "temp_figma_summary.txt"
        if figma_summary:
            self.figma_summarizer.save_figma_summary(figma_summary, temp_figma_path)
        else:
            with open(temp_figma_path, "w") as f:
                f.write("No Figma data provided")
        
        try:
            test_plan = self.test_plan_generator.generate_test_plan_from_files(
                context_path=temp_prd_path,
                figma_path=temp_figma_path
            )
            return test_plan
        finally:
            # Clean up temporary files
            for temp_file in [temp_prd_path, temp_figma_path]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    def generate_detailed_tests(self, test_plan: Dict[str, Any], figma_summary: str = "") -> Dict[str, Any]:
        """
        Generate detailed test cases from test plan.
        
        Args:
            test_plan: Generated test plan
            figma_summary: Figma summary for context (optional)
            
        Returns:
            Detailed test suite
        """
        # Save test plan temporarily as markdown
        temp_test_plan_path = "temp_test_plan.md"
        self.markdown_formatter.convert_test_plan(test_plan, temp_test_plan_path)
        
        # Save Figma summary temporarily (or create empty file if no summary)
        temp_figma_path = "temp_figma_summary.txt"
        if figma_summary:
            self.figma_summarizer.save_figma_summary(figma_summary, temp_figma_path)
        else:
            with open(temp_figma_path, "w") as f:
                f.write("No Figma data provided")
        
        try:
            detailed_tests = self.detailed_test_generator.generate_detailed_test_suite(
                test_plan_path=temp_test_plan_path,
                figma_summary_path=temp_figma_path
            )
            return detailed_tests
        finally:
            # Clean up temporary files
            for temp_file in [temp_test_plan_path, temp_figma_path]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    def convert_to_markdown(self, data: Dict[str, Any], data_type: str) -> str:
        """
        Convert JSON data to Markdown format.
        
        Args:
            data: JSON data to convert
            data_type: Type of data ('test_plan' or 'test_suite')
            
        Returns:
            Markdown formatted string
        """
        if data_type == "test_plan":
            return self.markdown_formatter.convert_test_plan_json_to_md(data)
        elif data_type == "test_suite":
            return self.markdown_formatter.convert_test_suite_json_to_md(data)
        else:
            raise ValueError("data_type must be 'test_plan' or 'test_suite'")
    
    def run_complete_workflow(self, 
                            prd_file_path: str, 
                            figma_url: str = "",
                            output_dir: str = "output") -> Dict[str, Any]:
        """
        Run the complete test planning workflow.
        
        Args:
            prd_file_path: Path to PRD file
            figma_url: Figma design URL (optional)
            output_dir: Directory to save output files
            
        Returns:
            Dictionary containing all generated outputs
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        print("Step 1: Extracting PRD context...")
        prd_context = self.extract_prd_context(prd_file_path)
        self.prd_extractor.save_prd_context(prd_context, f"{output_dir}/prd_context.json")
        
        # Step 2: Parse Figma design (optional)
        figma_data = None
        figma_summary = ""
        if figma_url and figma_url.strip():
            print("Step 2: Parsing Figma design...")
            figma_data = self.parse_figma_design(figma_url)
            self.figma_parser.save_figma_data(figma_data, f"{output_dir}/figma_data.json")
            
            print("Step 3: Summarizing Figma data...")
            figma_summary = self.summarize_figma_data(figma_data)
            self.figma_summarizer.save_figma_summary(figma_summary, f"{output_dir}/figma_summary.txt")
        else:
            print("Step 2: Skipping Figma parsing (no URL provided)")
            # Create empty figma files for consistency
            with open(f"{output_dir}/figma_data.json", "w") as f:
                json.dump({}, f)
            with open(f"{output_dir}/figma_summary.txt", "w") as f:
                f.write("No Figma data provided")
        
        print("Step 4: Generating test plan...")
        test_plan = self.generate_test_plan(prd_context, figma_summary)
        self.test_plan_generator.save_test_plan(test_plan, f"{output_dir}/test_plan.json")
        
        print("Step 5: Converting test plan to Markdown...")
        test_plan_md = self.convert_to_markdown(test_plan, "test_plan")
        with open(f"{output_dir}/test_plan.md", "w") as f:
            f.write(test_plan_md)
        
        print("Step 6: Generating detailed test cases...")
        detailed_tests = self.generate_detailed_tests(test_plan, figma_summary)
        self.detailed_test_generator.save_test_suite(detailed_tests, f"{output_dir}/test_suite.json")
        
        print("Step 7: Converting detailed tests to Markdown...")
        test_suite_md = self.convert_to_markdown(detailed_tests, "test_suite")
        with open(f"{output_dir}/test_suite.md", "w") as f:
            f.write(test_suite_md)
        
        return {
            "prd_context": prd_context,
            "figma_data": figma_data,
            "figma_summary": figma_summary,
            "test_plan": test_plan,
            "detailed_tests": detailed_tests,
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
