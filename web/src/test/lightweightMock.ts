// Dublê do lightweight-charts para os testes: o jsdom não tem canvas. Guarda as chamadas para os testes inspecionarem.
export const calls = {
  charts: 0,
  removed: 0,
  data: [] as unknown[][],
  markers: [] as unknown[][],
  clickHandlers: [] as Array<(p: unknown) => void>,
  crosshairHandlers: [] as Array<(p: unknown) => void>,
  priceLines: [] as Array<{ price: number; title: string }>,
  removedPriceLines: 0,
};

function makeSeries() {
  return {
    setData: (d: unknown[]) => void calls.data.push(d),
    setMarkers: (m: unknown[]) => void calls.markers.push(m),
    applyOptions: () => {},
    createPriceLine: (o: { price: number; title: string }) => {
      calls.priceLines.push(o);
      return o;
    },
    removePriceLine: () => void (calls.removedPriceLines += 1),
  };
}

export function createChart() {
  calls.charts += 1;
  return {
    addLineSeries: makeSeries,
    addCandlestickSeries: makeSeries,
    addHistogramSeries: makeSeries,
    timeScale: () => ({ fitContent: () => {}, applyOptions: () => {} }),
    subscribeClick: (h: (p: unknown) => void) => void calls.clickHandlers.push(h),
    unsubscribeClick: () => {},
    subscribeCrosshairMove: (h: (p: unknown) => void) => void calls.crosshairHandlers.push(h),
    unsubscribeCrosshairMove: () => {},
    applyOptions: () => {},
    resize: () => {},
    remove: () => void (calls.removed += 1),
  };
}

export function resetCalls() {
  calls.charts = 0;
  calls.removed = 0;
  calls.data = [];
  calls.markers = [];
  calls.clickHandlers = [];
  calls.crosshairHandlers = [];
  calls.priceLines = [];
  calls.removedPriceLines = 0;
}

export const ColorType = { Solid: "solid" };
export const PriceScaleMode = { Normal: 0, Logarithmic: 1 };
export const LineStyle = { Solid: 0, Dotted: 1, Dashed: 2, LargeDashed: 3, SparseDotted: 4 };
export const CrosshairMode = { Normal: 0, Magnet: 1 };
