import { useState, useEffect, useCallback, useRef } from "react";

const BACKEND_WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/orchestrator";
const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface BrainEvent {
  type: string;
  data: Record<string, any>;
  timestamp: number;
}

export function useOrchestrator() {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<BrainEvent[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [currentGoal, setCurrentGoal] = useState<string>("");
  const [plannerStatus, setPlannerStatus] = useState<string>("Idle");
  const [activeAgent, setActiveAgent] = useState<string>("Brain");
  const [currentTool, setCurrentTool] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    console.log("Connecting to Orchestrator WebSocket...");
    ws.current = new WebSocket(BACKEND_WS_URL);

    ws.current.onopen = () => {
      console.log("Connected to Orchestrator WebSocket");
      setIsConnected(true);
      setError(null);
    };

    ws.current.onmessage = (event) => {
      try {
        const parsed: BrainEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, parsed]);

        // Update state based on event type
        switch(parsed.type) {
          case "task_started":
            setActiveTaskId(parsed.data.task_id);
            setCurrentGoal(parsed.data.command);
            setPlannerStatus("Starting...");
            setActiveAgent("Brain");
            setCurrentTool("");
            setError(null);
            break;
          case "planner_started":
            setPlannerStatus("Thinking...");
            break;
          case "planner_finished":
            setPlannerStatus("Plan generated.");
            break;
          case "tool_selected":
          case "tool_started":
            setCurrentTool(parsed.data.tool);
            setPlannerStatus(`Executing: ${parsed.data.tool}`);
            break;
          case "tool_finished":
            setPlannerStatus(parsed.data.success ? `Tool succeeded: ${parsed.data.tool}` : `Tool failed: ${parsed.data.tool}`);
            if (!parsed.data.success) {
               setError(parsed.data.result);
            }
            break;
          case "agent_switched":
            setActiveAgent(parsed.data.new_agent);
            break;
          case "observation_received":
            setPlannerStatus(`Observing: ${parsed.data.url || "Screen"}`);
            break;
          case "replanning_started":
            setPlannerStatus("Replanning due to failure...");
            break;
          case "task_completed":
            setPlannerStatus("Task Completed");
            setCurrentTool("");
            setActiveTaskId(null);
            break;
          case "task_failed":
            setPlannerStatus("Task Failed");
            setError(parsed.data.error);
            setCurrentTool("");
            setActiveTaskId(null);
            break;
        }
      } catch (e) {
        console.error("Failed to parse websocket event", e);
      }
    };

    ws.current.onclose = () => {
      console.log("Disconnected from Orchestrator WebSocket");
      setIsConnected(false);
      // Auto-reconnect after 3 seconds
      reconnectTimeout.current = setTimeout(connect, 3000);
    };

    ws.current.onerror = (e) => {
      console.error("WebSocket error:", e);
      ws.current?.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  const executeCommand = async (command: string) => {
    setError(null);
    try {
      const res = await fetch(`${BACKEND_API_URL}/api/brain/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || "Failed to execute command");
      return data;
    } catch (e: any) {
      setError(e.message);
      throw e;
    }
  };

  const clearEvents = () => setEvents([]);

  return {
    isConnected,
    events,
    activeTaskId,
    currentGoal,
    plannerStatus,
    activeAgent,
    currentTool,
    error,
    executeCommand,
    clearEvents
  };
}
