"use client";

import PlotlyVisualization from "@/components/plotly-visualization";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AudioLines, SendHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { DataPoint } from "@/types/plotly";

export default function ChatPage() {
  const [researchTopics, setResearchTopics] = useState("");
  const [showChart, setShowChart] = useState(false);
  const [embeddingData, setEmbeddingData] = useState<DataPoint[]>([] as any);
  const [isGraphLive, setIsGraphLive] = useState(false);
  const [sentences, setSentences] = useState<string[]>([]);

  const fetchSentences = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/v1/findIdeas");
      if (!response.ok) {
        console.error("Failed to fetch sentences");
        return;
      }
      const idea = await response.json();
      if (Array.isArray(idea)) {
        setSentences(idea);
        console.log(sentences)
      }
    } catch (error) {
      console.error("Error fetching sentences:", error);
    }
  };

  const onSend = async () => {
    if (!researchTopics.trim()) return;

    try {
      const threeDimPoints = await fetch(
        "http://localhost:8000/api/v1/get3Dpoints",
      );
      const threeDimPointsResponse = await threeDimPoints.json();

      setEmbeddingData(threeDimPointsResponse);
      setShowChart(true);
      setResearchTopics("");
      setIsGraphLive(true);

      // Fetch sentences whenever chart goes live
      fetchSentences();
    } catch (error) {
      console.error("Error fetching 3D points:", error);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isGraphLive) {
      interval = setInterval(fetchSentences, 5000); // refresh every 5s while graph is live
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isGraphLive]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-black">
      <div className="mx-auto w-screen h-screen relative">
        {showChart && (
          <div className="flex-col">
            <PlotlyVisualization data={(embeddingData as any).results} />

            {isGraphLive && sentences.length > 0 && (
              <div
                className="absolute left-1/2 -translate-x-1/2 bottom-24 w-[92%] max-w-3xl rounded-xl border border-white/20 bg-black/60 backdrop-blur p-3 text-xs text-white shadow-lg"
                aria-live="polite"
                aria-atomic="true"
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full animate-pulse bg-emerald-400" />
                  <span className="font-medium text-white/90">Live sentences</span>
                </div>
                <ul className="max-h-28 overflow-y-auto space-y-1 list-disc pl-5">
                  {sentences.map((s, i) => (
                    <li key={i} className="text-white/90">
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="text-white/80 mt-2">List of ideas</div>
          </div>
        )}
      </div>

      <footer className="fixed inset-x-0 bottom-0 z-10">
        <div className="mx-auto w-full max-w-3xl px-4 pb-6">
          <div className="flex items-end gap-2 rounded-xl border border-white/20 bg-white/60 p-2 backdrop-blur-md dark:border-zinc-700/80 dark:bg-zinc-900/60">
            <Input
              value={researchTopics}
              placeholder="Enter the topic/topics you would like to generate ideas on, separating them using commas"
              className="flex-1 resize-none border-none bg-transparent text-sm focus-visible:ring-0 dark:text-zinc-50"
              onChange={(e) => setResearchTopics(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button
              size="icon"
              className="h-10 w-10 shrink-0 bg-blue-500 text-white hover:bg-blue-600"
            >
              <AudioLines className="h-4 w-4" />
            </Button>
            <Button
              size="icon"
              className="h-10 w-10 shrink-0 bg-emerald-500 text-white hover:bg-emerald-600"
              onClick={onSend}
            >
              <SendHorizontal className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </footer>
    </div>
  );
}
