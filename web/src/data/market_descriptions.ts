export interface MarketDescription {
  symbol: string;
  slug: string;
  name: string;
  region: string;
  composition: string;
}

export const marketDescriptions: MarketDescription[] = [
  {
    symbol: "^DJI",
    slug: "dji",
    name: "Dow Jones Industrial",
    region: "美國",
    composition:
      "30 檔大型工業藍籌股，如 Apple、Boeing、Coca-Cola。代表美國傳產與大型企業表現。"
  },
  {
    symbol: "^GSPC",
    slug: "gspc",
    name: "S&P 500",
    region: "美國",
    composition:
      "前 500 大公司，涵蓋科技、金融、醫療、能源等。是美國整體經濟健康指標。"
  },
  {
    symbol: "^IXIC",
    slug: "ixic",
    name: "NASDAQ Composite",
    region: "美國",
    composition:
      "科技股集中（如 Apple、Microsoft、NVIDIA、Amazon）。代表成長型產業與創新驅動市場。"
  },
  {
    symbol: "^FTSE",
    slug: "ftse",
    name: "FTSE 100",
    region: "英國",
    composition:
      "倫敦交易所最大 100 檔公司，含能源、金融、礦業。是歐洲與新興市場連動性高的指數。"
  },
  {
    symbol: "^STOXX",
    slug: "stoxx",
    name: "STOXX Europe 600",
    region: "歐洲",
    composition:
      "涵蓋歐洲 17 國的 600 檔股票，是歐洲最廣泛的綜合性指標。"
  },
  {
    symbol: "^N225",
    slug: "n225",
    name: "Nikkei 225",
    region: "日本",
    composition:
      "225 檔大型企業（Toyota、Sony、SoftBank）。代表日本製造與出口產業景氣。"
  },
  {
    symbol: "^HSI",
    slug: "hsi",
    name: "Hang Seng Index",
    region: "香港",
    composition:
      "約 80 檔大型上市企業，包含中資科技與地產股。可視為中國資金風向鏡。"
  },
  {
    symbol: "^TWII",
    slug: "twii",
    name: "TWSE Weighted Index",
    region: "台灣",
    composition:
      "所有上市公司市值加權平均，半導體占比高（TSMC、聯發科）。反映亞洲科技供應鏈表現。"
  }
];

export const marketDescriptionsBySymbol = Object.fromEntries(
  marketDescriptions.map((item) => [item.symbol, item])
) as Record<string, MarketDescription>;

export const marketDescriptionsBySlug = Object.fromEntries(
  marketDescriptions.map((item) => [item.slug, item])
) as Record<string, MarketDescription>;
