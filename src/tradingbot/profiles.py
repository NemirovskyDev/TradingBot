"""Perfis de objetivo (renda, estabilidade, crescimento, curto prazo): textos em linguagem simples e a carteira de cada um."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    tagline: str
    expect: str
    warning: str
    portfolio_id: str  # a carteira montada para este perfil (em PROFILE_PORTFOLIOS)
    related_by: tuple[str, str] | None  # (métrica, "asc"|"desc") para ordenar as metodologias clássicas parecidas
    runs_link: bool = False  # leva também às estratégias por ativo


PROFILES: tuple[Profile, ...] = (
    Profile(
        "renda-dividendos", "Renda de dividendos", "Quero receber proventos com frequência.",
        "Mistura de fundos imobiliários, ações pagadoras de dividendos do Brasil e dos EUA e ETFs de dividendos. O retorno vem dos proventos e da variação dos preços, e os proventos já estão reinvestidos nos números.",
        "Renda não é garantia: proventos podem cair ou sumir. Os ativos foram escolhidos hoje, entre pagadores que sobreviveram, e os dados de proventos do Yahoo são irregulares para algumas ações.",
        "renda-dividendos", None,
    ),
    Profile(
        "estabilidade", "Estabilidade", "Quero oscilar pouco e dormir tranquilo.",
        "Quase tudo em caixa (CDI), com fatias pequenas de fundos imobiliários, ouro e bolsa. Cai pouco nos piores momentos, mas rende perto do CDI: a segurança tem um custo no retorno.",
        "Cair pouco no passado não garante cair pouco no futuro.",
        "estabilidade", ("max_drawdown", "desc"),
    ),
    Profile(
        "crescimento", "Crescimento", "Quero fazer o dinheiro crescer, aceitando as quedas.",
        "Foco em bolsa: S&P 500, Nasdaq e Ibovespa. As metodologias que compram e vendem seguindo a tendência tentam cortar as quedas, e estão listadas junto.",
        "A bolsa pode cair 30% ou mais; olhe a maior queda antes de decidir.",
        "crescimento", ("cagr", "desc"),
    ),
    Profile(
        "swing-alto-risco", "Alto risco, curto prazo", "Quero resultado rápido e aceito risco alto.",
        "Compra e venda de ações fortes em ciclos de dias a semanas: todo mês escolhe as 8 de maior alta em 12 meses e segue os rompimentos de preço. Os dados são diários, então day trade (no mesmo dia) não é simulável aqui.",
        "A regra escolhe as ações mês a mês, sem olhar o futuro, mas o catálogo só tem empresas que existem hoje (quem faliu ficou de fora), então o resultado ainda é um pouco otimista. Risco alto não significa lucro alto: a maioria das estratégias por ativo perde para comprar e segurar.",
        "swing-alto-risco", None, True,
    ),
)
