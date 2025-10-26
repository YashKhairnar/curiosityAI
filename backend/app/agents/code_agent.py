from uagents import Agent, Context, Model, Protocol
from uagents.setup import fund_agent_if_low
import os
import json
from pathlib import Path
from typing import List, Dict
import google.generativeai as genai


# Define message models
class ProjectRequest(Model):
    summary: str

class CodeSample(Model):
    filename: str
    language: str
    content: str

class ProjectResponse(Model):
    status: str
    project_path: str
    files_created: List[str]
    message: str

class DetailedProjectResponse(Model):
    status: str
    title: str
    approach: str
    stack: str
    code_samples: List[Dict]
    documentation: str
    message: str

# Create the agent with HTTP endpoint
code_generator = Agent(
    name="code_generator",
    seed="code_generator_seed_phrase_123",
    port=os.getenv("CODE_AGENT_PORT", 8001),
    endpoint=[f"http://127.0.0.1:{os.getenv('CODE_AGENT_PORT', 8001)}/submit"]
)

# Fund the agent if needed (for testnet)
fund_agent_if_low(code_generator.wallet.address())

class CodebaseGenerator:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
        self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL"))
        
        # Configure generation parameters
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192,
        }
    
    def generate_project_structure(self, summary: str) -> Dict:
        """Generate project structure using Gemini from a single summary string"""
        prompt = f"""Given this project summary, create a complete folder structure and list of files needed.

User summary: {summary}

Return a STRICT JSON object with this structure (no markdown fences, no commentary):
{{
    "project_name": "snake_case_name",
    "folders": ["folder1", "folder2/subfolder"],
    "files": {{
        "path/to/file.py": "purpose of this file",
        ...
    }}
}}

Make it production-ready with proper separation of concerns."""

        response = self.model.generate_content(
            prompt,
            generation_config=self.generation_config
        )
        
        response_text = response.text
        # Extract JSON from response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        return json.loads(response_text[start:end])
    
    def generate_file_content(self, file_path: str, purpose: str, 
                            project_context: str, language: str) -> str:
        """Generate content for a specific file"""
        prompt = f"""Generate production-ready code for this file:

File: {file_path}
Purpose: {purpose}
Language: {language}
Project Context: {project_context}

Requirements:
- Include proper imports
- Add docstrings/comments
- Follow best practices and design patterns
- Include error handling
- Make it complete and functional

Return only the code, no explanations."""

        response = self.model.generate_content(
            prompt,
            generation_config=self.generation_config
        )
        
        return response.text.strip()
    
    def generate_documentation(self, project_name: str, description: str, 
                             structure: Dict) -> str:
        """Generate README documentation"""
        prompt = f"""Create a comprehensive README.md for this project:

Project: {project_name}
Description: {description}
Structure: {json.dumps(structure, indent=2)}

Include:
- Project overview
- Features
- Installation instructions
- Usage examples
- Project structure explanation

Use proper Markdown formatting."""

        response = self.model.generate_content(
            prompt,
            generation_config=self.generation_config
        )
        
        return response.text.strip()
    
    def create_project(self, summary: str) -> Dict:
        """Generate project structure and code from a single summary without creating files"""
        structure = self.generate_project_structure(summary)
        project_name = structure['project_name']
        
        project_context = summary

        
        # Generate code samples for each file
        code_samples = []
        for file_path, purpose in structure['files'].items():
            print(f"Generating {file_path}...")
            # Determine language from file extension for better prompts
            file_ext = Path(file_path).suffix.lstrip('.')
            lang_map = {
                'py': 'python',
                'js': 'javascript',
                'ts': 'typescript',
                'jsx': 'javascript',
                'tsx': 'typescript',
                'java': 'java',
                'cpp': 'cpp',
                'c': 'c',
                'go': 'go',
                'rs': 'rust',
                'rb': 'ruby',
                'php': 'php',
                'html': 'html',
                'css': 'css',
                'json': 'json',
                'yaml': 'yaml',
                'yml': 'yaml',
                'md': 'markdown',
                'sh': 'bash',
            }
            file_language = lang_map.get(file_ext, 'auto')

            content = self.generate_file_content(
                file_path, purpose, project_context, file_language
            )
            
            # Clean up code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                # Remove first line (```language) and last line (```)
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
            
            code_samples.append({
                "filename": file_path,
                "language": file_language,
                "content": content
            })
        
        print("Generating documentation...")
        documentation = self.generate_documentation(
            project_name, summary, structure
        )
        
        # Clean up documentation if it has code blocks
        if documentation.startswith('```'):
            lines = documentation.split('\n')
            documentation = '\n'.join(lines[1:-1]) if len(lines) > 2 else documentation
        
        # Return structured result
        return {
            "title": project_name.replace('_', ' ').title(),
            "approach": summary,
            "stack": f"auto-detected with {', '.join(structure.get('folders', [])[:3])} structure",
            "code_samples": code_samples,
            "documentation": documentation
        }

# Initialize generator
generator = CodebaseGenerator()

# Create a protocol for HTTP handling
http_protocol = Protocol(name="http_protocol")

@http_protocol.on_message(model=ProjectRequest)
async def handle_project_request(ctx: Context, sender: str, msg: ProjectRequest):
    ctx.logger.info(f"Received project request: {msg.summary}")
    
    try:
        project_data = generator.create_project(summary=msg.summary)
        
        file_names = [cs["filename"] for cs in project_data.get("code_samples", [])]
        
        response = ProjectResponse(
            status="success",
            project_path=project_data.get("title", "Generated Project"),
            files_created=file_names,
            message=f"Project generated successfully: {project_data.get('title', 'Project')}"
        )
        
        await ctx.send(sender, response)
        ctx.logger.info(f"Project generated: {project_data.get('title')}")
        
    except Exception as e:
        ctx.logger.error(f"Error creating project: {str(e)}")
        response = ProjectResponse(
            status="error",
            project_path="",
            files_created=[],
            message=f"Error: {str(e)}"
        )
        await ctx.send(sender, response)

# Include the protocol
code_generator.include(http_protocol)

@code_generator.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Code Generator Agent started")
    ctx.logger.info(f"Agent address: {code_generator.address}")
    ctx.logger.info(f"HTTP endpoint: http://127.0.0.1:8001/submit")

@code_generator.on_rest_post("/generate", ProjectRequest, ProjectResponse)
async def handle_rest_request(ctx: Context, req: ProjectRequest) -> ProjectResponse:
    """REST endpoint for project generation"""
    ctx.logger.info(f"REST request received: {req.summary}")
    
    try:
        project_data = generator.create_project(summary=req.summary)
        
        file_names = [cs["filename"] for cs in project_data.get("code_samples", [])]
        
        return ProjectResponse(
            status="success",
            project_path=project_data.get("title", "Generated Project"),
            files_created=file_names,
            message=f"Project generated successfully: {project_data.get('title', 'Project')}"
        )
        
    except Exception as e:
        ctx.logger.error(f"Error: {str(e)}")
        return ProjectResponse(
            status="error",
            project_path="",
            files_created=[],
            message=f"Error: {str(e)}"
        )

@code_generator.on_rest_post("/generate/detailed", ProjectRequest, DetailedProjectResponse)
async def handle_detailed_request(ctx: Context, req: ProjectRequest) -> DetailedProjectResponse:
    """REST endpoint for detailed project generation with full code samples"""
    ctx.logger.info(f"Detailed REST request received: {req.summary}")
    
    try:
        project_data = generator.create_project(summary=req.summary)
        
        return DetailedProjectResponse(
            status="success",
            title=project_data.get("title", "Generated Project"),
            approach=project_data.get("approach", ""),
            stack=project_data.get("stack", ""),
            code_samples=project_data.get("code_samples", []),
            documentation=project_data.get("documentation", ""),
            message=f"Project generated successfully: {project_data.get('title', 'Project')}"
        )
        
    except Exception as e:
        ctx.logger.error(f"Error: {str(e)}")
        return DetailedProjectResponse(
            status="error",
            title="",
            approach="",
            stack="",
            code_samples=[],
            documentation="",
            message=f"Error: {str(e)}"
        )

if __name__ == "__main__":
    code_generator.run()