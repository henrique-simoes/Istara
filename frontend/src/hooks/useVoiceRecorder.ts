import { useState, useRef, useCallback } from "react";
import { chat } from "@/lib/api";

export interface VoiceRecorderHook {
  isRecording: boolean;
  isTranscribing: boolean;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<string | null>;
  cancelRecording: () => void;
}

export function useVoiceRecorder(): VoiceRecorderHook {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    setError(null);
    chunksRef.current = [];

    if (typeof window === "undefined" || !navigator.mediaDevices) {
      setError("Browser does not support audio recording.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch (err: any) {
      console.error("Error accessing microphone:", err);
      setError("Could not access microphone. Please check permissions.");
    }
  }, []);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    if (!mediaRecorderRef.current || !isRecording) return null;

    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current!;
      
      recorder.onstop = async () => {
        setIsRecording(false);
        setIsTranscribing(true);
        setError(null);

        const audioBlob = new Blob(chunksRef.current, { type: recorder.mimeType });
        const audioFile = new File([audioBlob], "voice_input.ogg", { type: recorder.mimeType });

        try {
          const result = await chat.transcribeVoice(audioFile);
          resolve(result.text);
        } catch (err: any) {
          console.error("Transcription failed:", err);
          setError("Failed to transcribe audio.");
          resolve(null);
        } finally {
          setIsTranscribing(false);
          // Stop all tracks to release microphone
          recorder.stream.getTracks().forEach(track => track.stop());
        }
      };

      recorder.stop();
    });
  }, [isRecording]);

  const cancelRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      chunksRef.current = [];
    }
  }, [isRecording]);

  return {
    isRecording,
    isTranscribing,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
