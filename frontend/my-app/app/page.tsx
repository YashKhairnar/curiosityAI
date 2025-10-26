"use client";

import PlotlyVisualization from "@/components/plotly-visualization";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AudioLines, SendHorizontal, Loader2 } from "lucide-react";
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
import { NextResponse } from "next/server";

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
    const res = await fetch('http://localhost:8000/api/v1/generator')
    if(!res){
      return NextResponse.json({
        message : "Could not generate idea !"
      })
    }
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
      const response = await fetch("http://localhost:8000/api/v1/extractor", {
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
        "http://localhost:8000/api/v1/get3Dpoints",
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
      const resp = await fetch("http://localhost:8000/api/v1/findIdeas");
      
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
    <div className="relative flex h-screen flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto pb-32">
        <div className="mx-auto w-full max-w-3xl px-4 py-6">
          {showChart ? (
            <div className="mb-6 space-y-6">
              {/* 3D Visualization */}
              <div className="rounded-lg border bg-white/80 p-4 backdrop-blur-sm dark:bg-zinc-900/80">
                <PlotlyVisualization data={embeddingData} />
              </div>

              {/* Enhanced Ideas Section */}
              <div className="space-y-4">
                {isLoading ? (
                  <Card className="bg-white/60 dark:bg-zinc-900/60">
                    <CardContent className="flex items-center justify-center py-12">
                      <div className="flex flex-col items-center gap-3">
                        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                        <p className="text-sm text-zinc-600 dark:text-zinc-400">
                          Generating research ideas...
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ) : enhancedIdea ? (
                  <Card className="bg-white/60 dark:bg-zinc-900/60">
                    <CardHeader>
                      <CardTitle className="text-lg">
                        {enhancedIdea.enhanced_idea
                          .split(" ")
                          .slice(0, 8)
                          .join(" ") +
                          (enhancedIdea.enhanced_idea.split(" ").length > 8
                            ? "…"
                            : "")}
                      </CardTitle>
                      <CardDescription>AI-enhanced research idea</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
                        {enhancedIdea.enhanced_idea}
                      </p>
                    </CardContent>
                    <CardFooter>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={()=>{handleGetStarted}}>
                          Get started with the Idea !
                        </Button>
                        
                      </div>
                    </CardFooter>
                  </Card>
                ) : (
                  <div className="rounded-lg border bg-white/60 p-6 text-center text-sm text-zinc-600 backdrop-blur-sm dark:bg-zinc-900/60 dark:text-zinc-400">
                    <p>No ideas generated yet. Enter topics and hit Send to get started.</p>
                  </div>
                )}
              </div>

              {/* Error Display */}
              {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
                  <p className="font-semibold">Error:</p>
                  <p>{error}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <h1 className="mb-4 text-3xl font-bold text-zinc-800 dark:text-zinc-100">
                  Research Idea Generator
                </h1>
                <p className="mb-8 text-zinc-600 dark:text-zinc-400">
                  Enter research topics to explore the landscape and discover new ideas
                </p>
                <div className="mx-auto max-w-md space-y-2">
                  <div className="rounded-lg border bg-white/60 p-4 text-left text-sm backdrop-blur-sm dark:bg-zinc-900/60">
                    <p className="mb-2 font-semibold">Example topics:</p>
                    <ul className="list-inside list-disc space-y-1 text-zinc-600 dark:text-zinc-400">
                      <li>Machine learning, computer vision</li>
                      <li>Climate change, renewable energy</li>
                      <li>Neuroscience, brain imaging</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Input Footer */}
      <footer className="fixed inset-x-0 bottom-0 z-10 border-t border-white/20 bg-white/80 backdrop-blur-md dark:border-zinc-700/80 dark:bg-zinc-900/80">
        <div className="mx-auto w-full max-w-3xl px-4 py-4">
          <div className="flex items-end gap-2 rounded-xl border border-zinc-200 bg-white p-2 dark:border-zinc-700 dark:bg-zinc-900">
            <Input
              value={researchTopics}
              placeholder="Enter research topics separated by commas (e.g., machine learning, climate change, neuroscience)"
              className="flex-1 resize-none border-none bg-transparent text-sm focus-visible:ring-0 dark:text-zinc-50"
              onChange={(e) => setResearchTopics(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <Button
              size="icon"
              className={`h-10 w-10 shrink-0 text-white ${
                isRecordingVoice
                  ? "bg-red-500 hover:bg-red-600"
                  : "bg-blue-500 hover:bg-blue-600"
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
              className="h-10 w-10 shrink-0 bg-emerald-500 text-white hover:bg-emerald-600"
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
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              {researchTopicsVoice.map((k) => (
                <span
                  key={k}
                  className="rounded bg-emerald-500/20 px-2 py-1 text-emerald-700 dark:text-emerald-300"
                >
                  {k}
                </span>
              ))}
              {voiceError && (
                <span className="rounded bg-red-500/20 px-2 py-1 text-red-600 dark:text-red-400">
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