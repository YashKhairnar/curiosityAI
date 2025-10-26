"use client";

import PlotlyVisualization from "@/components/plotly-visualization";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AudioLines, SendHorizontal, Loader2, Sparkles, Brain, Zap } from "lucide-react";
import { useState } from "react";
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

  const handleGetStarted=async()=>{
    const res = await fetch('http://localhost:9000/api/v1/generator', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        summary: enhancedIdea?.enhanced_idea,
      })
    })
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error('Error:', error));
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
    <div className="relative flex h-screen flex-col overflow-hidden bg-gradient-fey">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-neon-blue/10 rounded-full blur-3xl animate-float"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-neon-purple/10 rounded-full blur-3xl animate-float" style={{animationDelay: '1s'}}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-neon-pink/5 rounded-full blur-3xl animate-pulse"></div>
      </div>

      <div className="flex-1 overflow-y-auto pb-32 relative z-10">
        <div className="mx-auto w-full max-w-4xl px-6 py-8">
          {showChart ? (
            <div className="mb-8 space-y-8 animate-fade-in-up">
              {/* 3D Visualization */}
              <div className="glass rounded-2xl p-6 shadow-neon-glow-lg border border-white/10">
                <div className="mb-4 flex items-center gap-3">
                  <Brain className="h-6 w-6 text-neon-blue animate-pulse" />
                  <h2 className="text-xl font-semibold text-white">Research Landscape</h2>
                </div>
                <PlotlyVisualization data={embeddingData} />
              </div>

              {/* Enhanced Ideas Section */}
              <div className="space-y-6">
                {isLoading ? (
                  <Card className="glass border-neon-blue/30">
                    <CardContent className="flex items-center justify-center py-16">
                      <div className="flex flex-col items-center gap-4">
                        <div className="relative">
                          <Loader2 className="h-12 w-12 animate-spin text-neon-blue" />
                          <Sparkles className="h-6 w-6 text-neon-purple absolute -top-1 -right-1 animate-bounce-subtle" />
                        </div>
                        <p className="text-sm text-dark-300 font-medium">
                          Generating research ideas...
                        </p>
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-neon-blue rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                          <div className="w-2 h-2 bg-neon-purple rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                          <div className="w-2 h-2 bg-neon-pink rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ) : enhancedIdea ? (
                  <Card className="glass border-neon-blue/30 hover:border-neon-blue/50 transition-all duration-500">
                    <CardHeader>
                      <div className="flex items-center gap-3 mb-2">
                        <Zap className="h-5 w-5 text-neon-blue animate-pulse" />
                        <CardTitle className="text-xl gradient-text">
                          {enhancedIdea.enhanced_idea}
                        </CardTitle>
                      </div>
                      <CardDescription className="text-dark-300">
                        AI-enhanced research idea
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-dark-200">
                        {enhancedIdea.enhanced_idea}
                      </p>
                    </CardContent>
                    <CardFooter>
                      <div className="flex gap-3">
                        <Button 
                          variant="neon" 
                          size="lg" 
                          onClick={()=>{handleGetStarted()}}
                          className="shimmer"
                        >
                          <Sparkles className="h-4 w-4" />
                          Get Started
                        </Button>
                      </div>
                    </CardFooter>
                  </Card>
                ) : (
                  <div className="glass rounded-2xl p-8 text-center border border-white/10">
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-16 h-16 rounded-full bg-dark-800/50 flex items-center justify-center">
                        <Brain className="h-8 w-8 text-dark-400" />
                      </div>
                      <p className="text-sm text-dark-300">
                        No ideas generated yet. Enter topics and hit Send to get started.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Error Display */}
              {error && (
                <div className="glass rounded-2xl border border-red-500/50 bg-red-900/20 p-6 text-sm text-red-300 backdrop-blur-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                    <p className="font-semibold">Error:</p>
                  </div>
                  <p className="mt-2">{error}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center min-h-[60vh]">
              <div className="text-center max-w-2xl mx-auto animate-fade-in-up">
                <div className="mb-8">
                  <div className="inline-flex items-center gap-3 mb-6">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-neon-blue to-neon-purple flex items-center justify-center">
                      <Brain className="h-6 w-6 text-white" />
                    </div>
                    <h1 className="text-4xl font-bold gradient-text">
                      Curiosity AI
                    </h1>
                  </div>
                  <p className="text-xl text-dark-300 mb-2 font-medium">
                    Research Idea Generator
                  </p>
                  <p className="text-dark-400 leading-relaxed">
                    Enter research topics to explore the landscape and discover new ideas with AI-powered insights
                  </p>
                </div>
                
                <div className="glass rounded-2xl p-6 text-left border border-white/10 max-w-md mx-auto">
                  <div className="flex items-center gap-2 mb-4">
                    <Sparkles className="h-4 w-4 text-neon-blue" />
                    <p className="font-semibold text-white">Example topics:</p>
                  </div>
                  <ul className="space-y-2 text-dark-300">
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-neon-blue rounded-full"></div>
                      Machine learning, computer vision
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-neon-purple rounded-full"></div>
                      Climate change, renewable energy
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-neon-pink rounded-full"></div>
                      Neuroscience, brain imaging
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Input Footer */}
      <footer className="fixed inset-x-0 bottom-0 z-20 border-t border-white/10 glass backdrop-blur-xl">
        <div className="mx-auto w-full max-w-4xl px-6 py-6">
          <div className="flex items-end gap-3 rounded-2xl border border-white/20 glass p-3 backdrop-blur-xl">
            <Input
              value={researchTopics}
              placeholder="Enter research topics separated by commas (e.g., machine learning, climate change, neuroscience)"
              className="flex-1 resize-none border-none bg-transparent text-sm focus-visible:ring-0 text-white placeholder:text-dark-400"
              onChange={(e) => setResearchTopics(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <Button
              size="icon"
              variant={isRecordingVoice ? "destructive" : "glass"}
              className={`h-12 w-12 shrink-0 ${
                isRecordingVoice
                  ? "animate-pulse"
                  : "hover:shadow-neon-glow"
              }`}
              onClick={handleVoiceToggle}
              disabled={isLoading}
              title={
                isRecordingVoice ? "Stop voice input" : "Start voice input"
              }
            >
              <AudioLines className="h-5 w-5" />
            </Button>
            <Button
              size="icon"
              variant="neon"
              className="h-12 w-12 shrink-0 shimmer"
              onClick={onSend}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <SendHorizontal className="h-5 w-5" />
              )}
            </Button>
          </div>
          
          {/* Voice keywords display */}
          {(researchTopicsVoice.length > 0 || voiceError) && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs animate-fade-in-up">
              {researchTopicsVoice.map((k) => (
                <span
                  key={k}
                  className="rounded-full bg-neon-blue/20 px-3 py-1.5 text-neon-blue border border-neon-blue/30 backdrop-blur-sm"
                >
                  {k}
                </span>
              ))}
              {voiceError && (
                <span className="rounded-full bg-red-500/20 px-3 py-1.5 text-red-400 border border-red-500/30 backdrop-blur-sm">
                  {voiceError}
                </span>
              )}
            </div>
          )}
        </div>
      </footer>
    </div>
  );
}