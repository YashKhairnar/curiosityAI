# CuriosityAI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CalHacks 2025](https://img.shields.io/badge/CalHacks-2025-blue)](https://calhacks.io/)

## Overview

CuriosityAI is an innovative AI-powered agentic system designed to democratize invention and R&D. Built for CalHacks 12.0 (October 24-26, 2025), it identifies gaps in research and patent landscapes using embedding inversion and retrieval-augmented generation (RAG). Autonomous agents analyze feasibility, generate detailed research proposals, push prototype code to GitHub, and provide curated references for further reading. Leveraging tools like FetchAI, LangChain for AI Agents, Hugging Face for NLP models, Deepgram for Voice agent, and 3D libraries for visualization, this project turns conceptual voids into actionable inventions.

## Features

- **Gap Identification**: Uses GMM or KDE density estimation on embeddings (e.g., from ArXiv/PubChem APIs) to spot low-density regions representing unexplored innovations.
- **Feasibility Analysis**: Agents evaluate novelty, technical viability, and ethical considerations using LLMs like Anthropic's Claude or Groq for fast inference.
- **Research Proposal Generation**: Produces structured proposals with abstracts, methods, impact assessments, and mock experiments via RAG and prompt engineering.
- **Code Pushing to GitHub**: Integrates with GitHub API to auto-generate and commit prototype code (e.g., sketches or scripts) for inventions.
- **References for Further Reading**: Curates academic papers, patents, and resources from Semantic Scholar or X searches.
- **Integrations**: Built with CalHacks sponsors like Fetch.ai (agents), Chroma (vector stores), and Deepgram (voice inputs for accessibility).

## Tech Stack

- **Core Frameworks**: Python, FetchAI, Hugging Face Transformers (embeddings/inversion with Vec2Text), ChromaDB .
- **ML Models**: Gaussian Mixture Models (scikit-learn) for density estimation, LLMs
- **APIs**: ArXiv, PubChem, GitHub, Semantic Scholar.
- **UI/Deployment**: Next.js, 3.js for interactive web app

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

- Built at CalHacks 12.0, 2025
- Team: CuriosityAI
