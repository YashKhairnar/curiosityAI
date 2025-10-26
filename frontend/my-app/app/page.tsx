"use client";

import PlotlyVisualization from "@/components/plotly-visualization";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AudioLines, SendHorizontal, Loader2 } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { DataPoint } from "@/types/plotly";
import { useDeepgramVoiceInput } from "@/hooks/useDeepgramVoice";
import { mergeUniqueTopics, parseTopics } from "@/lib/topics";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

export default function ChatPage() {
  const router = useRouter();
  const [researchTopics, setResearchTopics] = useState("");
  const [showChart, setShowChart] = useState(false);
  const [embeddingData, setEmbeddingData] = useState<DataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // single enhanced idea object (API now returns one entry)
  const [enhancedIdea, setEnhancedIdea] = useState<{
    enhanced_idea: string;
  } | null>(null);
  
  const {
    isRecording: isRecordingVoice,
    error: voiceError,
    keywords: researchTopicsVoice,
    toggle: handleVoiceToggle,
  } = useDeepgramVoiceInput();

  console.log("Embedding data loaded:", embeddingData);

  const handleGetStarted = () => {
    if (!enhancedIdea) return;
    
    // Navigate to the generator page with the summary as a query parameter
    const encodedSummary = encodeURIComponent(enhancedIdea.enhanced_idea);
    router.push(`/generator?summary=${encodedSummary}`);
  }
  
  const onSend = async () => {
    const typed = researchTopics.trim() ? parseTopics(researchTopics) : [];
    const allTopics = mergeUniqueTopics(typed, researchTopicsVoice);
    
    if (allTopics.length === 0) {
      setError("Please enter at least one research topic");
      return;
    }

    setIsLoading(true);
    setError(null);
    setEnhancedIdea(null);

    try {
      // Step 1: Extract data
      const response = await fetch("http://localhost:9000/api/v1/extractor", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ keywords: allTopics }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch data: ${response.statusText}`);
      }
      
      const data3d = await response.json();
      console.log("Response from backend:", data3d);

      // Step 2: Get 3D points
      const threeDimPoints = await fetch(
        "http://localhost:9000/api/v1/get3Dpoints",
      );
      
      if (!threeDimPoints.ok) {
        throw new Error(`Failed to get 3D points: ${threeDimPoints.statusText}`);
      }
      
      const threeDimPointsResponse = await threeDimPoints.json();
      const points: unknown = threeDimPointsResponse;
      const arr = Array.isArray(points)
        ? points
        : points && typeof points === "object" && "results" in points
          ? (points as { results: DataPoint[] }).results
          : [];
      
      setEmbeddingData(arr as DataPoint[]);
      setShowChart(true);

      // Step 3: Get enhanced ideas
      const resp = await fetch("http://localhost:9000/api/v1/findIdeas");
      
      if (!resp.ok) {
        throw new Error(`Failed to find ideas: ${resp.statusText}`);
      }
      
      const data = await resp.json();
      
      // Handle several possible shapes
      let firstIdea: { enhanced_idea: string } | null = null;
      if (data) {
        if (
          Array.isArray(data.enhanced_ideas) &&
          data.enhanced_ideas.length > 0
        ) {
          firstIdea = data.enhanced_ideas[0];
        } else if (
          data.enhanced_ideas &&
          typeof data.enhanced_ideas === "object" &&
          "enhanced_idea" in data.enhanced_ideas
        ) {
          firstIdea = data.enhanced_ideas;
        } else if ("enhanced_idea" in data) {
          firstIdea = data as { enhanced_idea: string };
        }
      }
      
      setEnhancedIdea(firstIdea);
      console.log("Generated research idea:", firstIdea);
      setResearchTopics("");
      
    } catch (err) {
      console.error("Error in onSend:", err);
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !isLoading) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-slate-900">
      <div className="relative flex-1 overflow-y-auto pb-32">
        <div className="mx-auto w-full max-w-5xl px-6 py-12">
          {showChart ? (
            <div className="space-y-8">
              {/* Header */}
              <div className="text-center mb-8">
                <h2 className="text-3xl font-semibold text-white mb-2">Research Landscape Analysis</h2>
                <p className="text-slate-400">Interactive 3D visualization of your research topics</p>
              </div>

              {/* 3D Visualization */}
              <div className="glass rounded-xl card-professional">
                <div className="p-6">
                  <div className="mb-4">
                    <h3 className="text-lg font-medium text-white mb-2">Topic Embeddings</h3>
                    <p className="text-sm text-slate-400">Explore the semantic relationships between your research topics</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-4">
                    <PlotlyVisualization data={embeddingData} />
                  </div>
                </div>
              </div>

              {/* Enhanced Ideas Section */}
              <div className="glass rounded-xl card-professional">
                <div className="p-6">
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold text-white mb-2">AI-Generated Research Ideas</h3>
                    <p className="text-slate-400">Discover innovative research directions based on your topics</p>
                  </div>

                  {isLoading ? (
                    <div className="flex items-center justify-center py-16">
                      <div className="flex flex-col items-center gap-4">
                        <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
                        <p className="text-sm text-slate-300 font-medium">
                          Analyzing topics and generating ideas...
                        </p>
                      </div>
                    </div>
                  ) : enhancedIdea ? (
                    <div className="space-y-6">
                      <div className="bg-slate-800/50 rounded-lg p-6 highlight-blue">
                        <div className="flex items-start gap-4">
                          <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                            <span className="text-blue-400 text-lg">💡</span>
                          </div>
                          <div className="flex-1">
                            

                            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
                              {enhancedIdea.enhanced_idea}
                            </p>
                          </div>
                        </div>
                      </div>
                      <div className="flex justify-end">
                        <Button 
                          className="btn-professional bg-blue-600 hover:bg-blue-700 text-white px-6 py-2"
                          onClick={handleGetStarted}
                        >
                          Get Started with the Idea!
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <div className="w-16 h-16 bg-slate-700/50 rounded-lg flex items-center justify-center mx-auto mb-4">
                        <span className="text-2xl">💡</span>
                      </div>
                      <p className="text-slate-300 font-medium">No ideas generated yet</p>
                      <p className="text-sm text-slate-400 mt-1">Enter research topics below to get started</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="glass rounded-lg p-4 status-error">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-red-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-red-400 text-sm">⚠</span>
                    </div>
                    <div>
                      <p className="font-medium text-red-300">Error</p>
                      <p className="text-red-200 text-sm">{error}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <div className="text-center max-w-3xl">
                <div className="mb-12">
                  {/* App Name with Neon Blinking Effect */}
                  <div className="mb-3">
                    <h1 className="text-6xl font-bold mb-2 relative inline-block neon-text">
                      <span className="relative z-10 bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 bg-clip-text text-transparent">
                        CuriosityAI
                      </span>
                      <span className="absolute inset-0 text-6xl font-bold blur-md opacity-75 bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 bg-clip-text text-transparent">
                        CuriosityAI
                      </span>
                      {/* Neon glow effect */}
                      <span className="absolute inset-0 -z-10 blur-2xl opacity-50 bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500"></span>
                    </h1>
                  </div>
                  
                  <p className="text-lg text-slate-300 leading-relaxed max-w-2xl mx-auto">
                    Find and explore <span className="text-purple-400 font-semibold">novel ideas never explored before</span> with AI-powered analysis and visualization
                  </p>
                </div>
                
                <div className="glass rounded-xl p-8 max-w-2xl mx-auto card-professional">
                  <div className="text-left">
                    <h3 className="text-lg font-medium text-white mb-2 flex items-center gap-2">
                      <span className="text-purple-400">✨</span>
                      Discover Unexplored Territories
                    </h3>
                    <p className="text-slate-400 text-sm mb-4">Enter topics to find novel research directions at their intersection</p>
                    <div className="grid gap-3">
                      <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-lg border border-purple-500/20">
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
                        <span className="text-slate-300">Quantum machine learning for drug discovery</span>
                      </div>
                      <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-lg border border-purple-500/20">
                        <div className="w-2 h-2 bg-pink-400 rounded-full animate-pulse"></div>
                        <span className="text-slate-300">Bio-inspired AI architectures, neural interfaces</span>
                      </div>
                      <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-lg border border-purple-500/20">
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
                        <span className="text-slate-300">Synthetic biology, programmable materials</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Input Footer */}
      <footer className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-700/50 bg-slate-900/95 backdrop-blur-xl">
        <div className="mx-auto w-full max-w-5xl px-6 py-6">
          <div className="glass rounded-xl p-4">
            <div className="flex items-center gap-3">
              <Input
                value={researchTopics}
                placeholder="Enter research topics separated by commas (e.g., machine learning, climate change, neuroscience)"
                className="flex-1 resize-none border-none bg-transparent text-sm text-white placeholder:text-slate-400 focus-visible:ring-0 input-professional"
                onChange={(e) => setResearchTopics(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
              />
              <Button
                size="icon"
                className={`h-10 w-10 shrink-0 text-white btn-professional ${
                  isRecordingVoice
                    ? "bg-red-600 hover:bg-red-700 highlight-red"
                    : "bg-slate-700 hover:bg-slate-600"
                }`}
                onClick={handleVoiceToggle}
                disabled={isLoading}
                title={
                  isRecordingVoice ? "Stop voice input" : "Start voice input"
                }
              >
                <AudioLines className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                className="h-10 w-10 shrink-0 bg-blue-600 text-white hover:bg-blue-700 btn-professional highlight-blue"
                onClick={onSend}
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <SendHorizontal className="h-4 w-4" />
                )}
              </Button>
            </div>
            
            {/* Voice keywords display */}
            {(researchTopicsVoice.length > 0 || voiceError) && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {researchTopicsVoice.map((k) => (
                  <span
                    key={k}
                    className="rounded-md bg-emerald-500/10 px-2 py-1 text-emerald-300 text-xs font-medium border border-emerald-500/20"
                  >
                    {k}
                  </span>
                ))}
                {voiceError && (
                  <span className="rounded-md bg-red-500/10 px-2 py-1 text-red-300 text-xs font-medium border border-red-500/20">
                    {voiceError}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}