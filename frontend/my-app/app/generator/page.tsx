"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

export default function GeneratorPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const summary = searchParams.get("summary");
  
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feasibilityData, setFeasibilityData] = useState<any>(null);
  const [isFeasibilityLoading, setIsFeasibilityLoading] = useState(false);
  const [showGithubForm, setShowGithubForm] = useState(false);
  const [githubToken, setGithubToken] = useState("");
  const [githubUsername, setGithubUsername] = useState("");
  const [repoName, setRepoName] = useState("");
  const [isPushing, setIsPushing] = useState(false);
  const [references, setReferences] = useState<any[]>([]);
  const [isFetchingReferences, setIsFetchingReferences] = useState(false);
  const [isGeneratingProposal, setIsGeneratingProposal] = useState(false);

  useEffect(() => {
    if (!summary) {
      setError("No summary provided");
      setIsLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        const response = await fetch('http://localhost:9000/api/v1/generator', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            summary: summary,
            num_research_titles: 5
          })
        });
        
        if (!response.ok) {
          throw new Error('Failed to generate project ideas');
        }
        
        const result = await response.json();
        setData(result);
      } catch (error) {
        console.error('Error generating ideas:', error);
        setError('Failed to generate project ideas. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [summary]);

  const checkFeasibility = async () => {
    if (!data?.ideas) return;
    
    setIsFeasibilityLoading(true);
    try {
      const response = await fetch('http://localhost:5010/feasibility', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          title: data.ideas.title || (summary?.split('\n')[0] || 'Project'),
          summary: data.ideas.approach || summary || ''
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to check feasibility');
      }
      
      const result = await response.json();
      setFeasibilityData(result);
    } catch (error) {
      console.error('Error checking feasibility:', error);
      alert('Failed to check feasibility. Please try again.');
    } finally {
      setIsFeasibilityLoading(false);
    }
  };

  const fetchReferences = async () => {
    if (!data?.ideas) return;
    
    setIsFetchingReferences(true);
    try {
      const textToSearch = data.ideas.approach || summary || data.ideas.title || '';
      
      const response = await fetch('http://0.0.0.0:8007/references', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          text: textToSearch,
          max_references: 5,
          fast: true,
          budget_ms: 10000
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch references');
      }
      
      const result = await response.json();
      setReferences(result.links || []);
    } catch (error) {
      console.error('Error fetching references:', error);
      alert('Failed to fetch references. Please try again.');
    } finally {
      setIsFetchingReferences(false);
    }
  };

  const generateResearchProposal = async () => {
    if (!data?.ideas) return;
    
    setIsGeneratingProposal(true);
    try {
      const topic = data.ideas.title || summary || 'Research Project';
      const proposalSummary = data.ideas.approach || summary || '';
      
      // Navigate to the research proposal page with data
      const encodedData = encodeURIComponent(JSON.stringify({
        topic,
        summary: proposalSummary
      }));
      router.push(`/research-proposal?data=${encodedData}`);
    } catch (error) {
      console.error('Error generating proposal:', error);
      alert('Failed to generate research proposal. Please try again.');
    } finally {
      setIsGeneratingProposal(false);
    }
  };

  const pushToGithub = async () => {
    if (!githubToken || !githubUsername || !repoName) {
      alert('Please fill in all fields');
      return;
    }
    
    if (!data?.ideas) {
      alert('No project data to push');
      return;
    }

    setIsPushing(true);
    try {
      // Prepare files for GitHub
      const files: any[] = [];
      
      // Add README
      if (data.ideas.documentation) {
        files.push({
          path: 'README.md',
          content: data.ideas.documentation
        });
      }
      
      // Add code files
      if (data.ideas.code_samples) {
        data.ideas.code_samples.forEach((code: any) => {
          files.push({
            path: code.filename,
            content: code.content
          });
        });
      }

      const response = await fetch('http://localhost:9000/api/v1/github/push', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: githubToken,
          owner: githubUsername,
          repo_name: repoName,
          files: files,
          visibility: 'public'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to push to GitHub');
      }

      const result = await response.json();
      alert(`Successfully pushed to GitHub!\n\nRepository: ${result.repo_url}`);
      setShowGithubForm(false);
    } catch (error) {
      console.error('Error pushing to GitHub:', error);
      alert(error instanceof Error ? error.message : 'Failed to push to GitHub. Please try again.');
    } finally {
      setIsPushing(false);
    }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
        <div className="max-w-4xl w-full">
          <div className="glass rounded-xl p-8 text-center">
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
          <h1 className="text-3xl font-semibold text-white">Project Generator</h1>
          <p className="text-slate-400 mt-2">Generated research ideas and project suggestions</p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="glass rounded-xl p-12 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-blue-400 mx-auto mb-4" />
            <p className="text-slate-300 font-medium">Generating your project ideas...</p>
          </div>
        )}

        {/* Results */}
        {!isLoading && data && (
          <div className="space-y-6">
            {/* Research Titles */}
            {data.research_titles && data.research_titles.length > 0 && (
              <div className="glass rounded-xl p-6">
                <h2 className="text-xl font-semibold text-white mb-4">
                  Research Proposal Titles ({data.research_titles.length})
                </h2>
                <div className="space-y-2">
                  {data.research_titles.map((title: string, index: number) => (
                    <div 
                      key={index}
                      className="bg-slate-800/50 rounded-lg p-4 flex items-start gap-3"
                    >
                      <span className="text-blue-400 font-medium">{index + 1}.</span>
                      <p className="text-slate-200 flex-1">{title}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Project Details */}
            {data.coding_related && data.ideas && (
              <div className="glass rounded-xl p-6">
                {/* Title */}
                {data.ideas.title && (
                  <div className="mb-6">
                    <h3 className="text-2xl font-bold text-white mb-2">{data.ideas.title}</h3>
                  </div>
                )}

                {/* Summary/Approach */}
                {data.ideas.approach && (
                  <div className="mb-6 bg-slate-800/50 rounded-lg p-5">
                    <h4 className="text-lg font-semibold text-white mb-3">Summary</h4>
                    <div className="text-slate-300 whitespace-pre-wrap text-sm leading-relaxed">
                      {data.ideas.approach}
                    </div>
                  </div>
                )}

                {/* Documentation */}
                {data.ideas.documentation && (
                  <div className="mb-6 bg-slate-800/50 rounded-lg p-5">
                    <h4 className="text-lg font-semibold text-white mb-3">Documentation</h4>
                    <div className="text-slate-300 whitespace-pre-wrap text-sm leading-relaxed">
                      {data.ideas.documentation}
                    </div>
                  </div>
                )}

                {/* Code Samples */}
                {data.ideas.code_samples && data.ideas.code_samples.length > 0 && (
                  <div className="mb-6">
                    <h4 className="text-lg font-semibold text-white mb-4">
                      Code Samples ({data.ideas.code_samples.length})
                    </h4>
                    <div className="space-y-4">
                      {data.ideas.code_samples.map((code: any, index: number) => (
                        <div 
                          key={index}
                          className="bg-slate-800/50 rounded-lg overflow-hidden"
                        >
                          <div className="bg-slate-700/50 px-4 py-2 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-blue-400 font-medium">📄</span>
                              <span className="text-white font-medium text-sm">{code.filename}</span>
                              {code.language && (
                                <span className="text-slate-400 text-xs bg-slate-600 px-2 py-0.5 rounded">
                                  {code.language}
                                </span>
                              )}
                            </div>
                          </div>
                          <pre className="bg-slate-900 p-4 overflow-x-auto text-xs text-slate-200">
                            <code>{code.content}</code>
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Stack */}
                {data.ideas.stack && (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4">
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400 font-medium">⚙️</span>
                      <span className="text-emerald-300 text-sm font-medium">Stack:</span>
                      <span className="text-emerald-200 text-sm">{data.ideas.stack}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Non-coding message */}
            {!data.coding_related && (
              <div className="glass rounded-xl p-6 bg-blue-500/10 border border-blue-500/20">
                <p className="text-blue-300 text-center">
                  {data.message || "The idea doesn't look primarily coding-related. No code/doc generated."}
                </p>
              </div>
            )}

            {/* Feasibility Section */}
            {data.coding_related && data.ideas && (
              <div className="glass rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">Feasibility Analysis</h2>
                  {!feasibilityData && (
                    <Button 
                      onClick={checkFeasibility}
                      disabled={isFeasibilityLoading}
                      className="bg-purple-600 hover:bg-purple-700 text-white"
                    >
                      {isFeasibilityLoading ? 'Analyzing...' : 'Analyze Feasibility'}
                    </Button>
                  )}
                </div>

                {feasibilityData && (
                  <div className="space-y-4">
                    <div className="bg-slate-800/50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-300 font-medium">Overall Score</span>
                        <span className={`text-2xl font-bold ${
                          feasibilityData.aggregate.passes_threshold 
                            ? 'text-green-400' 
                            : 'text-red-400'
                        }`}>
                          {feasibilityData.aggregate.overall.toFixed(1)}/100
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className={`px-2 py-1 rounded ${
                          feasibilityData.aggregate.passes_threshold 
                            ? 'bg-green-500/20 text-green-300' 
                            : 'bg-red-500/20 text-red-300'
                        }`}>
                          {feasibilityData.aggregate.passes_threshold ? 'PASS' : 'FAIL'}
                        </span>
                        <span className="text-slate-400">Threshold: {feasibilityData.aggregate.threshold}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {feasibilityData.breakdown.map((item: any, index: number) => (
                        <div key={index} className="bg-slate-800/50 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-white font-medium capitalize">{item.parameter}</span>
                            <span className="text-blue-400 font-semibold">{item.score.toFixed(1)}</span>
                          </div>
                          <p className="text-slate-400 text-xs">{item.rationale}</p>
                          <div className="mt-2 text-xs text-slate-500">Confidence: {(item.confidence * 100).toFixed(0)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* References Section */}
            {data.coding_related && data.ideas && (
              <div className="glass rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">Research References</h2>
                  {references.length === 0 && (
                    <Button 
                      onClick={fetchReferences}
                      disabled={isFetchingReferences}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white"
                    >
                      {isFetchingReferences ? 'Fetching...' : 'Get References'}
                    </Button>
                  )}
                </div>

                {references.length > 0 && (
                  <div className="space-y-3">
                    <p className="text-slate-400 text-sm mb-4">
                      Found {references.length} relevant references for your research topic
                    </p>
                    <div className="space-y-2">
                      {references.map((ref: string, index: number) => (
                        <div 
                          key={index}
                          className="bg-slate-800/50 rounded-lg p-3 hover:bg-slate-800 transition-colors"
                        >
                          <a 
                            href={ref} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="flex items-center gap-3 group"
                          >
                            <span className="text-blue-400 text-lg group-hover:text-blue-300">🔗</span>
                            <span className="text-blue-400 hover:text-blue-300 text-sm flex-1 truncate group-hover:underline">
                              {ref}
                            </span>
                            <span className="text-slate-400 text-xs">↗</span>
                          </a>
                        </div>
                      ))}
                    </div>
                    {references.length === 10 && (
                      <p className="text-slate-500 text-xs text-center mt-2">
                        Showing top 10 references. More may be available.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Research Proposal Section */}
            {data.coding_related && data.ideas && (
              <div className="glass rounded-xl p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-white">Research Proposal</h2>
                    <p className="text-slate-400 text-sm mt-1">Generate a complete research proposal with references</p>
                  </div>
                  <Button 
                    onClick={generateResearchProposal}
                    disabled={isGeneratingProposal}
                    className="bg-purple-600 hover:bg-purple-700 text-white"
                  >
                    {isGeneratingProposal ? 'Generating...' : 'Generate Research Proposal'}
                  </Button>
                </div>
              </div>
            )}

            {/* GitHub Push Section */}
            {data.coding_related && data.ideas && (
              <div className="glass rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">Push to GitHub</h2>
                  {!showGithubForm && (
                    <Button 
                      onClick={() => setShowGithubForm(true)}
                      className="bg-green-600 hover:bg-green-700 text-white"
                    >
                      Push to GitHub
                    </Button>
                  )}
                </div>

                {showGithubForm && (
                  <div className="space-y-4 bg-slate-800/50 rounded-lg p-4">
                    <div>
                      <label className="block text-sm font-medium text-white mb-2">GitHub Username</label>
                      <input
                        type="text"
                        value={githubUsername}
                        onChange={(e) => setGithubUsername(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                        placeholder="your-username"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-white mb-2">GitHub Token</label>
                      <input
                        type="password"
                        value={githubToken}
                        onChange={(e) => setGithubToken(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                        placeholder="ghp_xxxxxxxxxxxx"
                      />
                      <p className="text-xs text-slate-400 mt-1">Create a token at github.com/settings/tokens</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-white mb-2">Repository Name</label>
                      <input
                        type="text"
                        value={repoName}
                        onChange={(e) => setRepoName(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                        placeholder="my-awesome-project"
                      />
                    </div>
                    <div className="flex gap-3">
                      <Button 
                        onClick={pushToGithub}
                        disabled={isPushing || !githubToken || !githubUsername || !repoName}
                        className="bg-green-600 hover:bg-green-700 text-white flex-1"
                      >
                        {isPushing ? 'Pushing...' : 'Push to GitHub'}
                      </Button>
                      <Button 
                        onClick={() => setShowGithubForm(false)}
                        className="bg-slate-700 hover:bg-slate-600 text-white"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
