"""Os 78 ativos validados em 2026-10-28 (o yfinance entregou histórico desde 2018 para todos eles)."""
from tradingbot.catalog import Asset

US, ETF_US, B3, FII, ETF_B3, CRYPTO = "Ações EUA", "ETFs EUA", "Ações B3", "FIIs", "ETFs B3", "Cripto"

SEED: list[Asset] = [
    *(Asset(t, n, US) for t, n in [
        ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"), ("AMZN", "Amazon"),
        ("GOOGL", "Alphabet (classe A)"), ("META", "Meta Platforms"), ("TSLA", "Tesla"),
        ("JPM", "JPMorgan Chase"), ("V", "Visa"), ("KO", "Coca-Cola"), ("PEP", "PepsiCo"),
        ("XOM", "Exxon Mobil"), ("JNJ", "Johnson & Johnson"), ("WMT", "Walmart"),
        ("DIS", "Walt Disney"), ("NFLX", "Netflix"), ("AMD", "AMD"), ("INTC", "Intel"),
        ("BA", "Boeing"), ("MCD", "McDonald's"),
    ]),
    *(Asset(t, n, ETF_US) for t, n in [
        ("SPY", "SPDR S&P 500"), ("QQQ", "Invesco QQQ (Nasdaq-100)"), ("IWM", "iShares Russell 2000"),
        ("DIA", "SPDR Dow Jones"), ("GLD", "SPDR Gold (ouro)"), ("SLV", "iShares Silver (prata)"),
        ("TLT", "iShares Treasury 20+ anos"), ("EEM", "iShares Mercados Emergentes"),
        ("EFA", "iShares MSCI EAFE"), ("VNQ", "Vanguard Imobiliário"), ("XLK", "SPDR Tecnologia"),
        ("XLF", "SPDR Financeiro"), ("XLE", "SPDR Energia"), ("ARKK", "ARK Innovation"),
    ]),
    *(Asset(f"{t}.SA", n, B3) for t, n in [
        ("PETR4", "Petrobras PN"), ("VALE3", "Vale ON"), ("ITUB4", "Itaú Unibanco PN"),
        ("BBDC4", "Bradesco PN"), ("BBAS3", "Banco do Brasil ON"), ("ABEV3", "Ambev ON"),
        ("WEGE3", "WEG ON"), ("B3SA3", "B3 ON"), ("RENT3", "Localiza ON"), ("SUZB3", "Suzano ON"),
        ("RADL3", "Raia Drogasil ON"), ("LREN3", "Lojas Renner ON"), ("GGBR4", "Gerdau PN"),
        ("PRIO3", "PRIO ON"), ("EQTL3", "Equatorial ON"), ("RAIL3", "Rumo ON"), ("CSAN3", "Cosan ON"),
        ("HAPV3", "Hapvida ON"), ("MGLU3", "Magazine Luiza ON"),
    ]),
    *(Asset(f"{t}.SA", n, FII) for t, n in [
        ("HGLG11", "CSHG Logística"), ("XPLG11", "XP Log"), ("KNRI11", "Kinea Renda Imobiliária"),
        ("MXRF11", "Maxi Renda"), ("VISC11", "Vinci Shopping Centers"), ("XPML11", "XP Malls"),
        ("BTLG11", "BTG Pactual Logística"), ("HGRU11", "CSHG Renda Urbana"),
        ("KNCR11", "Kinea Rendimentos Imobiliários"), ("KNIP11", "Kinea Índices de Preços"),
        ("CPTS11", "Capitânia Securities II"), ("VGIR11", "Valora RE III"),
        ("TRXF11", "TRX Real Estate"), ("RBRR11", "RBR Rendimento High Grade"),
    ]),
    *(Asset(f"{t}.SA", n, ETF_B3) for t, n in [
        ("BOVA11", "iShares Ibovespa"), ("IVVB11", "iShares S&P 500 (em reais)"), ("SMAL11", "iShares Small Caps"),
    ]),
    *(Asset(t, n, CRYPTO) for t, n in [
        ("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"), ("SOL-USD", "Solana"), ("BNB-USD", "BNB"),
        ("XRP-USD", "XRP"), ("ADA-USD", "Cardano"), ("DOGE-USD", "Dogecoin"), ("LTC-USD", "Litecoin"),
    ]),
]
