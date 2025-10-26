"use client";

import PlotlyVisualization from "@/components/plotly-visualization";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AudioLines, SendHorizontal } from "lucide-react";
import { useState } from "react";
import { DataPoint } from "@/types/plotly";
import { useDeepgramVoiceInput } from "@/hooks/useDeepgramVoice";
import { mergeUniqueTopics, parseTopics } from "@/lib/topics";
// accordion previously used; not needed for single-idea card
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
  const [embeddingData] = useState<DataPoint[]>([]);
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

  const onSend = async () => {
    const typed = researchTopics.trim() ? parseTopics(researchTopics) : [];
    const allTopics = mergeUniqueTopics(typed, researchTopicsVoice);
    if (allTopics.length === 0) return;

    // const response = await fetch("http://:8000/api/v1/extractor", {
    //   method: "POST",
    //   headers: {
    //     "Content-Type": "application/json",
    //   },
    //   body: JSON.stringify({ keywords: allTopics }),
    // });
    // if (!response.ok) {
    //   console.error("Failed to fetch data from backend");
    //   setResearchTopics("");
    //   return;
    // }
    // const data = await response.json();
    // console.log("Response from backend:", data);
    //
    // const threeDimPoints = await fetch(
    //   "http://10.0.5.250:8000/api/v1/get3Dpoints",
    // );
    // const threeDimPointsResponse = await threeDimPoints.json();
    // const points: unknown = threeDimPointsResponse;
    // const arr = Array.isArray(points)
    //   ? points
    //   : points && typeof points === "object" && "results" in points
    //     ? (points as { results: DataPoint[] }).results
    //     : [];
    // setEmbeddingData(arr as DataPoint[]);

    setShowChart(true);
    setResearchTopics("");

    const resp = await fetch("/api/dummyideas");
    const data = await resp.json();
    // handle several possible shapes: { enhanced_ideas: [{...}] } or { enhanced_ideas: {...} }
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
                <PlotlyVisualization data={embeddingData} />
              </div>
            </div>
          )}
          {/* <Accordion type="single" collapsible className="w-full"> */}
          {/*   {enhancedIdeas.map((idea, index) => ( */}
          {/*     <AccordionItem key={index} value={`item-${index}`}> */}
          {/*       <AccordionTrigger>Idea {index + 1}</AccordionTrigger> */}
          {/*       <AccordionContent> */}
          {/*         <div className="mb-2 rounded-lg border p-4"> */}
          {/*           <p className="text-sm text-zinc-700 dark:text-zinc-300"> */}
          {/*             {idea} */}
          {/*           </p> */}
          {/*         </div> */}
          {/*       </AccordionContent> */}
          {/*     </AccordionItem> */}
          {/*   ))} */}
          {/* </Accordion> */}

          <div className="space-y-4">
            {enhancedIdea ? (
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
                  <p className="whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
                    {enhancedIdea.enhanced_idea}
                  </p>
                </CardContent>
                <CardFooter>
                  <div className="flex gap-2">
                    <Button size="sm">CodeGen</Button>
                    <Button
                      size="sm"
                      onClick={() =>
                        navigator.clipboard?.writeText(
                          enhancedIdea.enhanced_idea,
                        )
                      }
                    >
                      Copy
                    </Button>
                    <Button size="sm" onClick={() => alert("Saved (stub)")}>
                      Save
                    </Button>
                  </div>
                </CardFooter>
              </Card>
            ) : (
              <div className="rounded-lg border p-4 text-sm text-zinc-600 dark:text-zinc-400">
                No idea yet — enter topics and hit Send.
              </div>
            )}
          </div>
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
              className={`h-10 w-10 shrink-0 text-white ${
                isRecordingVoice
                  ? "bg-red-500 hover:bg-red-600"
                  : "bg-blue-500 hover:bg-blue-600"
              }`}
              onClick={handleVoiceToggle}
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
            >
              <SendHorizontal className="h-4 w-4" />
            </Button>
          </div>
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
              {voiceError && <span className="text-red-500">{voiceError}</span>}
            </div>
          )}
        </div>
      </footer>
    </div>
  );
}
