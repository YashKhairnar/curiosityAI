"use client";

import PlotlyVisualization from "@/components/plotly-visualization";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AudioLines, SendHorizontal, Waves } from "lucide-react";
import { useState } from "react";
import embeddingsDataRaw from "@/embeddings_3d_for_threejs.json";
import { DataPoint } from "@/types/plotly";

export default function ChatPage() {
  const [researchTopics, setResearchTopics] = useState("");
  const [showChart, setShowChart] = useState(false);
  const [researchTopicsArray, setResearchTopicsArray] = useState<string[]>([]);
  const [embeddingData, setEmbeddingData] = useState<DataPoint[]>([]);
  console.log("Embedding data loaded:", embeddingData);

  const onSend = async () => {
    if (!researchTopics.trim()) return;

    // Parse comma-separated input (don't append, just use current input)
    // const newTopics = researchTopics
    //   .split(",")
    //   .map((topic) => topic.trim())
    //   .filter((topic) => topic.length > 0);
    //
    // // Remove duplicates from current input only
    // const updatedTopicsArray = Array.from(new Set(newTopics));
    // console.log("Updated topics array: ", updatedTopicsArray);
    // setResearchTopicsArray(updatedTopicsArray);
    //
    // const response = await fetch("http://10.0.5.250:8000/api/v1/extractor", {
    //   method: "POST",
    //   headers: {
    //     "Content-Type": "application/json",
    //   },
    //   body: JSON.stringify({ keywords: updatedTopicsArray }),
    // });
    // if (!response.ok) {
    //   console.error("Failed to fetch data from backend");
    //   setResearchTopics("");
    //   return;
    // }
    //
    // const data = await response.json();
    // console.log("Response from backend:", data);

    const threeDimPoints = await fetch(
      "http://10.0.5.250:8000/api/v1/get3Dpoints",
    );
    const threeDimPointsResponse = await threeDimPoints.json();
    // console.log("3D Points from backend:", threeDimPointsResponse);
    setEmbeddingData(threeDimPointsResponse);

    setShowChart(true);
    setResearchTopics("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="relative flex h-screen flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto pb-32">
        <div className="mx-auto w-full max-w-3xl px-4 py-6">
          {showChart && (
            <div className="mb-6">
              <div className="rounded-lg border p-4">
                <PlotlyVisualization data={embeddingData.results} />
              </div>
            </div>
          )}
        </div>
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
