"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { DataPoint } from "@/types/plotly";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as any;

interface PlotlyVisualizationProps {
  data: DataPoint[];
}

export default function PlotlyVisualization({
  data,
}: PlotlyVisualizationProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [plotData, setPlotData] = useState<any[]>([]);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!data || !Array.isArray(data) || data.length === 0) return;

    const getClusterColor = (clusterId: number) => {
      switch (clusterId) {
        case 0:
          return "#22c55e";
        case 1:
          return "#3b82f6";
        case -1:
          return "#fbbf24";
        default:
          return "#6b7280";
      }
    };

    // Create a single scatter3d trace for all points
    const pointsTrace = {
      type: "scatter3d",
      mode: "markers",
      name: "Research Papers",
      x: data.map((d) => d.embedding[0]),
      y: data.map((d) => d.embedding[1]),
      z: data.map((d) => d.embedding[2]),
      text: data.map((d) => `${d.title}<br>Cluster: ${d.clusterId}`),
      hoverinfo: "text",
      marker: {
        size: 6,
        color: data.map((d) => getClusterColor(d.clusterId)),
        opacity: 1,
        line: {
          color: "#ffffff",
          width: 0.5,
        },
        showscale: false,
      },
    };

    // Create a surface plot using interpolation
    // First, let's create a grid for the surface
    const gridSize = 30;
    const xMin = Math.min(...data.map((d) => d.embedding[0]));
    const xMax = Math.max(...data.map((d) => d.embedding[0]));
    const yMin = Math.min(...data.map((d) => d.embedding[1]));
    const yMax = Math.max(...data.map((d) => d.embedding[1]));

    // Create grid
    const xRange = Array.from(
      { length: gridSize },
      (_, i) => xMin + ((xMax - xMin) * i) / (gridSize - 1),
    );
    const yRange = Array.from(
      { length: gridSize },
      (_, i) => yMin + ((yMax - yMin) * i) / (gridSize - 1),
    );

    // Interpolate z values using inverse distance weighting
    const zGrid = yRange.map((y) =>
      xRange.map((x) => {
        // Calculate weighted average based on distance
        let weightSum = 0;
        let valueSum = 0;

        data.forEach((point) => {
          const dx = point.embedding[0] - x;
          const dy = point.embedding[1] - y;
          const distance = Math.sqrt(dx * dx + dy * dy) + 0.1;
          const weight = 1 / (distance * distance);

          weightSum += weight;
          valueSum += weight * point.embedding[2];
        });

        return valueSum / weightSum;
      }),
    );

    // Add surface plot
    const surfaceTrace = {
      type: "surface",
      x: xRange,
      y: yRange,
      z: zGrid,
      colorscale: [
        [0, "#2c3e50"],
        [0.25, "#3498db"],
        [0.5, "#2ecc71"],
        [0.75, "#f39c12"],
        [1, "#e74c3c"],
      ],
      opacity: 0.7,
      showscale: true,
      name: "Density Surface",
      hoverinfo: "x+y+z",
      contours: {
        z: {
          show: true,
          usecolormap: true,
          highlightcolor: "#ffffff",
          project: { z: true },
        },
      },
    };

    setPlotData([pointsTrace]);
  }, [data]);

  if (!isClient) {
    return (
      <div className="w-full h-full flex items-center justify-center text-white">
        <div className="text-xl">Loading visualization...</div>
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      {plotData.length > 0 && (
        <Plot
          data={plotData}
          layout={{
            scene: {
              xaxis: {
                title: "X Dimension",
                gridcolor: "#444444",
                color: "#ffffff",
                backgroundcolor: "#1a1a1a",
              },
              yaxis: {
                title: "Y Dimension",
                gridcolor: "#444444",
                color: "#ffffff",
                backgroundcolor: "#1a1a1a",
              },
              zaxis: {
                title: "Z Dimension",
                gridcolor: "#444444",
                color: "#ffffff",
                backgroundcolor: "#1a1a1a",
              },
              bgcolor: "#0f0f0f",
              camera: {
                eye: { x: 1.5, y: 1.5, z: 1.3 },
              },
            },
            paper_bgcolor: "#111827",
            plot_bgcolor: "#0f0f0f",
            font: { color: "#ffffff" },
            showlegend: true,
            legend: {
              x: 0.02,
              y: 0.98,
              bgcolor: "rgba(0,0,0,0)",
              bordercolor: "#ffffff",
              borderwidth: 1,
              font: { color: "#ffffff" },
            },
            margin: { l: 0, r: 0, t: 50, b: 0 },
            hovermode: "closest",
          }}
          config={{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ["toImage"],
          }}
          style={{ width: "100%", height: "100%" }}
          useResizeHandler={true}
        />
      )}
    </div>
  );
}
