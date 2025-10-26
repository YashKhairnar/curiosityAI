import PlotlyVisualization from "@/components/plotly-visualization";
import testres from "@/testres.json";

export default function Plotly() {
  return (
    <div>
      <PlotlyVisualization data={testres} />
    </div>
  );
}
