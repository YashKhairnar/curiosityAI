"use client";

import { useCallback, useRef, useState } from "react";
import { createClient, LiveTranscriptionEvents } from "@deepgram/sdk";

type DGConnection = {
  send: (data: ArrayBuffer) => void;
  close?: () => void;
  requestClose?: () => void;
  on: (
    evt: LiveTranscriptionEvents,
    handler: (data?: unknown) => void
  ) => void;
};

export interface UseDeepgramVoiceOptions {
  apiKey?: string;
  model?: string;
  language?: string;
}

export function useDeepgramVoiceInput(options?: UseDeepgramVoiceOptions) {
  const apiKey = options?.apiKey ?? process.env.NEXT_PUBLIC_DEEPGRAM_API_KEY;
  const model = options?.model ?? "nova-3";
  const language = options?.language ?? "en-US";

  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);

  const dgConnectionRef = useRef<DGConnection | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const transcriptBufferRef = useRef<string>("");

  const start = useCallback(async () => {
    try {
      setError(null);
      transcriptBufferRef.current = "";

      if (!apiKey) {
        setError("Missing Deepgram API key (NEXT_PUBLIC_DEEPGRAM_API_KEY)");
        return;
      }

      const deepgram = createClient(apiKey);
      const connection = deepgram.listen.live({
        model,
        language,
        smart_format: true,
        punctuate: true,
        encoding: "opus",
      }) as unknown as DGConnection;

      dgConnectionRef.current = connection;

      connection.on(LiveTranscriptionEvents.Open, async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
          });
          mediaStreamRef.current = stream;

          const mimeType = MediaRecorder.isTypeSupported(
            "audio/webm;codecs=opus"
          )
            ? "audio/webm;codecs=opus"
            : "audio/webm";

          const mediaRecorder = new MediaRecorder(stream, { mimeType });
          mediaRecorderRef.current = mediaRecorder;

          mediaRecorder.addEventListener("dataavailable", async (event) => {
            if (event.data && event.data.size > 0) {
              try {
                const arrayBuffer = await event.data.arrayBuffer();
                connection.send(arrayBuffer);
              } catch {
                // ignore chunk errors
              }
            }
          });

          mediaRecorder.start(250);
          setIsRecording(true);
        } catch (micErr) {
          const message =
            micErr && typeof micErr === "object" && "message" in micErr
              ? (micErr as { message?: string }).message
              : undefined;
          setError(message || "Microphone access failed");
        }
      });

      type TranscriptEvent = {
        channel?: { alternatives?: Array<{ transcript?: string }> };
      };
      connection.on(
        LiveTranscriptionEvents.Transcript,
        (data?: unknown) => {
          const evt = data as TranscriptEvent | undefined;
          const text = evt?.channel?.alternatives?.[0]?.transcript ?? "";
          if (text) {
            transcriptBufferRef.current +=
              (transcriptBufferRef.current ? " " : "") + text;
          }
        }
      );

      connection.on(LiveTranscriptionEvents.Error, (err?: unknown) => {
        const message =
          err && typeof err === "object" && "message" in err
            ? (err as { message?: string }).message
            : undefined;
        setError(message || "Deepgram connection error");
      });

      connection.on(LiveTranscriptionEvents.Close, () => {
        // no-op
      });
    } catch (err) {
      const message =
        err && typeof err === "object" && "message" in err
          ? (err as { message?: string }).message
          : undefined;
      setError(message || "Failed to start recording");
    }
  }, [apiKey, language, model]);

  const stop = useCallback(async () => {
    try {
      const mediaRecorder = mediaRecorderRef.current;
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
    } catch {
      // ignore
    }

    try {
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    } catch {
      // ignore
    }

    try {
      const conn = dgConnectionRef.current;
      if (conn?.requestClose) conn.requestClose();
      else if (conn?.close) conn.close();
      dgConnectionRef.current = null;
    } catch {
      // ignore
    }

    setIsRecording(false);

    const text = transcriptBufferRef.current.trim();
    if (text.length > 0) {
      const voiceTopics = text
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      // set unique keywords
      setKeywords((prev) => Array.from(new Set([...prev, ...voiceTopics])));
    }

    transcriptBufferRef.current = "";
  }, []);

  const toggle = useCallback(() => {
    if (isRecording) {
      void stop();
    } else {
      void start();
    }
  }, [isRecording, start, stop]);

  return {
    isRecording,
    error,
    keywords,
    start,
    stop,
    toggle,
  } as const;
}
