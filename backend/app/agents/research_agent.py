"""
FetchAI Research Proposal Generation Agent
This agent generates research proposals with references given a topic summary
"""

from uagents import Agent, Context, Model
from typing import List, Dict
import requests
import json
from datetime import datetime

# Define message models
class ResearchRequest(Model):
    topic: str
    summary: str
    num_references: int = 10
    
class ResearchProposal(Model):
    title: str
    abstract: str
    introduction: str
    literature_review: str
    methodology: str
    expected_outcomes: str
    timeline: str
    references: List[Dict[str, str]]
    generated_at: str

# Initialize the agent
research_agent = Agent(
    name="research_proposal_agent",
    seed="research_agent_seed_phrase",
    port=8001,
    endpoint=["http://localhost:8001/submit"]
)

# Helper function to search for academic references
async def search_references(topic: str, num_refs: int = 10) -> List[Dict[str, str]]:
    """
    Search for academic references using public APIs
    In production, you'd use APIs like:
    - Semantic Scholar API
    - CrossRef API
    - arXiv API
    - PubMed API
    """
    references = []
    
    # Example using Semantic Scholar API (free, no key required)
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": topic,
            "limit": num_refs,
            "fields": "title,authors,year,abstract,url,citationCount"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for paper in data.get("data", [])[:num_refs]:
                authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])])
                references.append({
                    "title": paper.get("title", ""),
                    "authors": authors,
                    "year": str(paper.get("year", "")),
                    "url": paper.get("url", ""),
                    "citation_count": str(paper.get("citationCount", 0)),
                    "abstract": paper.get("abstract", "")[:200] + "..."
                })
    except Exception as e:
        print(f"Error fetching references: {e}")
        # Fallback to mock references if API fails
        references = generate_mock_references(topic, num_refs)
    
    return references if references else generate_mock_references(topic, num_refs)

def generate_mock_references(topic: str, num_refs: int) -> List[Dict[str, str]]:
    """Generate mock references as fallback"""
    return [
        {
            "title": f"Recent Advances in {topic}: A Comprehensive Review",
            "authors": "Smith, J., Johnson, A., Brown, K.",
            "year": "2024",
            "url": f"https://example.org/paper_{i}",
            "citation_count": str(100 - i * 5),
            "abstract": f"This paper explores {topic} and its implications..."
        }
        for i in range(num_refs)
    ]

def generate_proposal_content(topic: str, summary: str, references: List[Dict]) -> Dict[str, str]:
    """Generate the research proposal sections"""
    
    # Generate title
    title = f"Research Proposal: {topic}"
    
    # Generate abstract
    abstract = f"""
This research proposal presents a comprehensive study on {topic}. {summary}
The proposed research aims to investigate key aspects, challenges, and potential
solutions in this domain. Through a systematic approach combining theoretical
analysis and practical implementation, this study seeks to contribute valuable
insights to the field. The expected outcomes include novel methodologies,
empirical findings, and recommendations for future research directions.
    """.strip()
    
    # Generate introduction
    introduction = f"""
## 1. Introduction

### 1.1 Background
{topic} has emerged as a critical area of research in recent years. {summary}
The growing importance of this field necessitates deeper investigation into
its fundamental principles, applications, and implications.

### 1.2 Problem Statement
Despite significant progress, several key challenges remain unresolved in {topic}.
These include:
- Limited understanding of core mechanisms
- Insufficient empirical evidence
- Need for robust methodological frameworks
- Gaps in practical implementation strategies

### 1.3 Research Objectives
This research aims to:
1. Conduct a comprehensive review of existing literature
2. Develop novel theoretical frameworks
3. Design and implement empirical studies
4. Validate findings through rigorous analysis
5. Provide actionable recommendations
    """.strip()
    
    # Generate literature review
    lit_review = f"""
## 2. Literature Review

### 2.1 Theoretical Foundations
The field of {topic} is built upon several foundational theories and concepts.
Previous research has established important groundwork, as evidenced by the
extensive body of literature reviewed for this proposal.

### 2.2 Key Studies
Recent studies have made significant contributions to our understanding:

"""
    
    # Add key references to literature review
    for i, ref in enumerate(references[:5], 1):
        lit_review += f"""
**{i}. {ref['title']}** ({ref['year']})
- Authors: {ref['authors']}
- Citations: {ref['citation_count']}
- Key contribution: {ref['abstract']}
"""
    
    lit_review += """
### 2.3 Research Gaps
While existing research has made valuable contributions, several gaps remain:
- Limited scope in certain areas
- Need for updated methodologies
- Insufficient cross-domain integration
- Lack of large-scale empirical validation
    """.strip()
    
    # Generate methodology
    methodology = f"""
## 3. Research Methodology

### 3.1 Research Design
This study will employ a mixed-methods approach combining:
- Systematic literature review
- Theoretical analysis
- Experimental design
- Data collection and analysis
- Validation and verification

### 3.2 Data Collection
Data will be collected through:
1. Primary sources: Surveys, interviews, experiments
2. Secondary sources: Published research, datasets, archives
3. Computational methods: Simulations, modeling, analytics

### 3.3 Analysis Framework
Data analysis will utilize:
- Statistical methods for quantitative data
- Thematic analysis for qualitative insights
- Computational tools and frameworks
- Validation through triangulation

### 3.4 Ethical Considerations
The research will adhere to ethical guidelines including:
- Informed consent from participants
- Data privacy and confidentiality
- Transparent reporting of findings
- Acknowledgment of limitations
    """.strip()
    
    # Generate expected outcomes
    outcomes = f"""
## 4. Expected Outcomes

### 4.1 Theoretical Contributions
- Novel frameworks for understanding {topic}
- Enhanced theoretical models
- Integration of cross-disciplinary insights

### 4.2 Practical Implications
- Actionable recommendations for practitioners
- Implementation guidelines
- Tools and resources for the community

### 4.3 Publications and Dissemination
- Peer-reviewed journal articles (target: 3-5)
- Conference presentations (target: 2-3)
- Open-source tools and datasets
- Community engagement and workshops
    """.strip()
    
    # Generate timeline
    timeline = """
## 5. Research Timeline

**Phase 1: Literature Review (Months 1-3)**
- Systematic review of existing research
- Identification of research gaps
- Refinement of research questions

**Phase 2: Methodology Development (Months 4-6)**
- Design of research framework
- Development of data collection instruments
- Pilot testing and refinement

**Phase 3: Data Collection (Months 7-12)**
- Primary data collection
- Secondary data analysis
- Interim analysis and reporting

**Phase 4: Analysis and Writing (Months 13-18)**
- Comprehensive data analysis
- Validation of findings
- Manuscript preparation

**Phase 5: Dissemination (Months 19-24)**
- Journal submissions
- Conference presentations
- Final report and documentation
    """.strip()
    
    return {
        "title": title,
        "abstract": abstract,
        "introduction": introduction,
        "literature_review": lit_review,
        "methodology": methodology,
        "expected_outcomes": outcomes,
        "timeline": timeline
    }

@research_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Research Proposal Agent started: {research_agent.address}")
    ctx.logger.info("Ready to generate research proposals!")

@research_agent.on_message(model=ResearchRequest)
async def handle_research_request(ctx: Context, sender: str, msg: ResearchRequest):
    """Handle incoming research proposal requests"""
    ctx.logger.info(f"Received research request for topic: {msg.topic}")
    
    try:
        # Search for references
        ctx.logger.info(f"Searching for {msg.num_references} references...")
        references = await search_references(msg.topic, msg.num_references)
        
        # Generate proposal content
        ctx.logger.info("Generating research proposal content...")
        content = generate_proposal_content(msg.topic, msg.summary, references)
        
        # Create the research proposal
        proposal = ResearchProposal(
            title=content["title"],
            abstract=content["abstract"],
            introduction=content["introduction"],
            literature_review=content["literature_review"],
            methodology=content["methodology"],
            expected_outcomes=content["expected_outcomes"],
            timeline=content["timeline"],
            references=references,
            generated_at=datetime.now().isoformat()
        )
        
        # Send the proposal back to the requester
        await ctx.send(sender, proposal)
        ctx.logger.info("Research proposal sent successfully!")
        
        # Save to file
        filename = f"research_proposal_{msg.topic.replace(' ', '_')}.md"
        save_proposal_to_file(proposal, filename)
        ctx.logger.info(f"Proposal saved to {filename}")
        
    except Exception as e:
        ctx.logger.error(f"Error generating proposal: {e}")

def save_proposal_to_file(proposal: ResearchProposal, filename: str):
    """Save the research proposal to a markdown file"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {proposal.title}\n\n")
        f.write(f"*Generated on: {proposal.generated_at}*\n\n")
        f.write("---\n\n")
        f.write("## Abstract\n\n")
        f.write(f"{proposal.abstract}\n\n")
        f.write("---\n\n")
        f.write(f"{proposal.introduction}\n\n")
        f.write(f"{proposal.literature_review}\n\n")
        f.write(f"{proposal.methodology}\n\n")
        f.write(f"{proposal.expected_outcomes}\n\n")
        f.write(f"{proposal.timeline}\n\n")
        f.write("---\n\n")
        f.write("## References\n\n")
        for i, ref in enumerate(proposal.references, 1):
            f.write(f"{i}. **{ref['title']}** ({ref['year']})\n")
            f.write(f"   - Authors: {ref['authors']}\n")
            f.write(f"   - Citations: {ref['citation_count']}\n")
            f.write(f"   - URL: {ref['url']}\n")
            f.write(f"   - Abstract: {ref['abstract']}\n\n")

# Example usage function
def create_sample_request():
    """Create a sample research request for testing"""
    return ResearchRequest(
        topic="Machine Learning in Healthcare",
        summary="This research explores the application of machine learning algorithms "
                "in healthcare diagnostics, focusing on early disease detection and "
                "personalized treatment recommendations.",
        num_references=10
    )

if __name__ == "__main__":
    # Run the agent
    research_agent.run()
    
    # To test the agent, you would send a ResearchRequest message
    # Example in another script:
    """
    from uagents import Agent, Context
    
    client_agent = Agent(name="client", seed="client_seed")
    
    @client_agent.on_event("startup")
    async def send_request(ctx: Context):
        request = ResearchRequest(
            topic="Artificial Intelligence in Education",
            summary="Investigating AI-powered personalized learning systems",
            num_references=10
        )
        await ctx.send("agent1q2...research_agent_address", request)
    
    client_agent.run()
    """