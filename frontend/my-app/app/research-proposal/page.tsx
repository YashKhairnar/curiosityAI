"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

export default function ResearchProposalPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const dataParam = searchParams.get("data");
  
  const [proposal, setProposal] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<any>(null);

  useEffect(() => {
    if (!dataParam) {
      setError("No data provided");
      setIsLoading(false);
      return;
    }

    try {
      const decoded = JSON.parse(decodeURIComponent(dataParam));
      setFormData(decoded);
      generateProposal(decoded);
    } catch (error) {
      console.error('Error parsing data:', error);
      setError("Invalid data provided");
      setIsLoading(false);
    }
  }, [dataParam]);

  const generateProposal = async (data: any) => {
    try {
      setIsLoading(true);
      
      // For now, we'll generate a mock proposal since the research agent doesn't have an HTTP endpoint
      // In production, you'd call: http://localhost:8001/api/research-proposal
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const mockProposal = {
        title: data.topic,
        abstract: `This research explores ${data.topic}, building upon existing methodologies and frameworks to advance our understanding in this domain.`,
        introduction: `## Introduction\n\nThe field of ${data.topic} has gained significant attention in recent years. This research aims to investigate key aspects and contribute novel insights to the existing body of knowledge.\n\n${data.summary}`,
        literature_review: `## Literature Review\n\nSeveral seminal works have established foundational principles in ${data.topic}. Recent advances in computational methods and data availability have opened new research directions.`,
        methodology: `## Methodology\n\nThis research will employ a mixed-methods approach, combining quantitative analysis with qualitative assessment to provide comprehensive insights.`,
        expected_outcomes: `## Expected Outcomes\n\nThis research is expected to contribute:\n- Novel insights into ${data.topic}\n- Practical applications and recommendations\n- Foundation for future research directions`,
        timeline: `## Timeline\n\n- Months 1-3: Literature review and methodology design\n- Months 4-6: Data collection and initial analysis\n- Months 7-9: Deep analysis and interpretation\n- Months 10-12: Documentation and dissemination`,
        references: [
          {
            title: "Recent Advances in the Field",
            authors: "Smith, J., et al.",
            year: "2024",
            url: "https://example.org/paper1",
            citation_count: "150",
            abstract: "This paper provides a comprehensive overview..."
          },
          {
            title: "Methodological Frameworks",
            authors: "Johnson, A., Williams, B.",
            year: "2023",
            url: "https://example.org/paper2",
            citation_count: "89",
            abstract: "A detailed examination of methodological approaches..."
          }
        ],
        generated_at: new Date().toISOString()
      };
      
      setProposal(mockProposal);
    } catch (error) {
      console.error('Error generating proposal:', error);
      setError('Failed to generate research proposal');
    } finally {
      setIsLoading(false);
    }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
        <div className="max-w-4xl w-full glass rounded-xl p-8 text-center">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">⚠</span>
          </div>
          <h2 className="text-2xl font-semibold text-white mb-2">Error</h2>
          <p className="text-red-300 mb-6">{error}</p>
          <Button 
            onClick={() => router.back()}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button 
            onClick={() => router.back()}
            variant="outline"
            className="mb-4 text-slate-300 border-slate-700 hover:bg-slate-800"
          >
            ← Back
          </Button>
          <h1 className="text-3xl font-semibold text-white">Research Proposal</h1>
          <p className="text-slate-400 mt-2">Generated research proposal with references and methodology</p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="glass rounded-xl p-12 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-blue-400 mx-auto mb-4" />
            <p className="text-slate-300 font-medium">Generating your research proposal...</p>
          </div>
        )}

        {/* Proposal Content */}
        {!isLoading && proposal && (
          <div className="space-y-6">
            {/* Title */}
            <div className="glass rounded-xl p-8">
              <h2 className="text-3xl font-bold text-white mb-2">{proposal.title}</h2>
              <p className="text-slate-400 text-sm">Generated on: {new Date(proposal.generated_at).toLocaleDateString()}</p>
            </div>

            {/* Abstract */}
            <div className="glass rounded-xl p-6">
              <h3 className="text-xl font-semibold text-white mb-4">Abstract</h3>
              <p className="text-slate-300 whitespace-pre-wrap leading-relaxed">{proposal.abstract}</p>
            </div>

            {/* Sections */}
            {[
              { title: "Introduction", content: proposal.introduction },
              { title: "Literature Review", content: proposal.literature_review },
              { title: "Methodology", content: proposal.methodology },
              { title: "Expected Outcomes", content: proposal.expected_outcomes },
              { title: "Timeline", content: proposal.timeline },
            ].map((section, index) => (
              <div key={index} className="glass rounded-xl p-6">
                <div className="text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {section.content}
                </div>
              </div>
            ))}

            {/* References */}
            {proposal.references && proposal.references.length > 0 && (
              <div className="glass rounded-xl p-6">
                <h3 className="text-xl font-semibold text-white mb-4">References</h3>
                <div className="space-y-4">
                  {proposal.references.map((ref: any, index: number) => (
                    <div key={index} className="bg-slate-800/50 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <span className="text-blue-400 font-medium text-sm">{index + 1}.</span>
                        <div className="flex-1">
                          <h4 className="text-white font-medium mb-1">{ref.title}</h4>
                          <p className="text-slate-400 text-sm mb-2">
                            {ref.authors} ({ref.year}) • {ref.citation_count} citations
                          </p>
                          <p className="text-slate-300 text-sm mb-2">{ref.abstract}</p>
                          <a 
                            href={ref.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300 text-sm"
                          >
                            {ref.url} ↗
                          </a>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Export Options */}
            <div className="glass rounded-xl p-6">
              <h3 className="text-xl font-semibold text-white mb-4">Export</h3>
              <div className="flex gap-3">
                <Button 
                  onClick={() => window.print()}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Print / Save as PDF
                </Button>
                <Button 
                  onClick={() => {
                    const content = JSON.stringify(proposal, null, 2);
                    const blob = new Blob([content], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'research-proposal.json';
                    a.click();
                  }}
                  className="bg-slate-700 hover:bg-slate-600 text-white"
                >
                  Download JSON
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
