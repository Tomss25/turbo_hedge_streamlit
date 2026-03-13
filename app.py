import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="Turbo Hedging Pro | Reality Check", layout="wide")

# CSS Corretto: Risolto il problema del testo invisibile e affinato il layout
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #1E1E1E; }
    [data-testid="stSidebar"] { background-color: #1B2A47; }
    
    /* Etichette e testo normale in bianco nella sidebar */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { 
        color: #FFFFFF !important; 
    }
    
    /* Input testuali in nero su sfondo bianco per visibilità perfetta */
    [data-testid="stSidebar"] input { 
        color: #1E1E1E !important; 
        background-color: #FFFFFF !important; 
        border-radius: 6px;
        border: 1px solid #4A5568;
    }
    
    div[data-testid="metric-container"] {
        background-color: #FFFFFF; border: 1px solid #E2E8F0;
        padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    div.stButton > button:first-child {
        background-color: #1B2A47; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #2C426B; color: white; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Tool Copertura Portafoglio - Turbo Short")
st.markdown("Calcolo dell'hedge ratio reale, visualizzazione leva e stress test Monte Carlo.")

# --- SIDEBAR: INPUT METRICHE AVANZATE ---
with st.sidebar:
    st.header("⚙️ Parametri di Stress (Realtà)")
    beta_port = st.number_input("Beta di Portafoglio", value=1.00, step=0.1)
    trans_costs = st.number_input("Commissioni Bancarie (Entry/Exit) %", value=0.10, step=0.05) / 100
    slippage_exit = st.number_input("Slippage in Uscita (Spread) %", value=0.50, step=0.1) / 100
    
    st.markdown("---")
    st.subheader("Costo di Mantenimento")
    div_yield = st.number_input("Dividend Yield Implicito (%)", value=1.50, step=0.1) / 100
    spread_mm = st.number_input("Margine Market Maker (%)", value=3.00, step=0.1) / 100
    
    st.markdown("---")
    volatility = st.number_input("Volatilità Annua (Monte Carlo) %", value=18.0, step=1.0) / 100

# --- MAIN PAGE: INPUT STRUTTURA ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Parametri Portafoglio")
    portafoglio = st.number_input("Portafoglio da coprire (€)", value=200000.0, step=10000.0)
    valore_iniziale = st.number_input("Valore Iniziale Indice", value=6670.75, step=10.0)
    valore_ipotetico = st.number_input("Target/Valore Ipotetico Indice", value=6000.0, step=10.0)
    giorni = st.number_input("Orizzonte di Copertura (Giorni)", value=60, step=1)
    cambio = st.number_input("Tasso di Cambio (es. EUR/USD)", value=1.15, step=0.01)

with col2:
    st.subheader("Parametri Certificato Turbo Short")
    prezzo_iniziale_turbo = st.number_input("Prezzo Acquisto Turbo (€)", value=7.64, step=0.01)
    strike = st.number_input("Strike Attuale", value=7505.97, step=10.0)
    multiplo = st.number_input("Multiplo", value=0.01, step=0.001, format="%.4f")
    euribor = st.number_input("Tasso Risk-Free (Euribor 12M) %", value=2.456, step=0.1) / 100

st.markdown("---")

# --- MOTORE MATEMATICO ---
portafoglio_beta = portafoglio * beta_port
valore_nozionale_indice = (valore_iniziale * multiplo) / cambio

fair_value = ((strike - valore_iniziale) * multiplo) / cambio
premio = prezzo_iniziale_turbo - fair_value

# Barriera Dinamica Lineare
tasso_finanziamento_netto = euribor - div_yield - spread_mm
strike_aggiustato = strike * (1 + tasso_finanziamento_netto * (giorni / 360))
barriera_turbo_simulata = strike_aggiustato

# Dimensionamento Reale
n_turbo_teorico = portafoglio_beta / valore_nozionale_indice
n_turbo_reale = int(np.ceil(n_turbo_teorico)) 
capitale_investito = n_turbo_reale * prezzo_iniziale_turbo
costo_transazione_ingresso = capitale_investito * trans_costs

# Valutazione a Target
if valore_ipotetico >= barriera_turbo_simulata:
    prezzo_turbo_simulato = 0.0
else:
    prezzo_lordo = max(0, ((strike_aggiustato - valore_ipotetico) * multiplo) / cambio)
    prezzo_turbo_simulato = prezzo_lordo * (1 - slippage_exit) 

valore_copertura_lordo = n_turbo_reale * prezzo_turbo_simulato
costo_transazione_uscita = valore_copertura_lordo * trans_costs

# --- OUTPUT DISPLAY ---
st.subheader("📊 Metriche Operative Reali")
metric_cols = st.columns(4)
metric_cols[0].metric("Fair Value Iniziale", f"€ {fair_value:.4f}", f"Premio: € {premio:.4f}", delta_color="inverse")
metric_cols[1].metric("Strike a Scadenza", f"{strike_aggiustato:.2f}", f"Erosione: {strike_aggiustato - strike:.2f} pt")
metric_cols[2].metric("Certificati da Comprare", f"{n_turbo_reale}", "Arrotondato all'intero")
metric_cols[3].metric("Capitale Reale Richiesto", f"€ {capitale_investito:,.2f}")

# --- SCENARIO ANALYSIS STATICA ---
st.markdown("---")
st.subheader("📈 Analisi Visiva: Copertura e Rendimenti")

scenari_indice = np.linspace(valore_iniziale * 0.8, valore_iniziale * 1.15, 30)
risultati_scenari = []

for idx_val in scenari_indice:
    # Rendimento Indice
    rendimento_indice = (idx_val / valore_iniziale) - 1
    
    # Valori Assoluti
    if idx_val >= barriera_turbo_simulata:
        p_netto = 0.0
        v_hedge = 0.0
        pnl_hedge = -capitale_investito - costo_transazione_ingresso
        rendimento_turbo = -1.0 # -100% perdita totale capitale hedge
    else:
        p_lordo = ((strike_aggiustato - idx_val) * multiplo) / cambio
        p_netto = p_lordo * (1 - slippage_exit)
        v_hedge = n_turbo_reale * p_netto
        pnl_hedge = v_hedge - capitale_investito - costo_transazione_ingresso - (v_hedge * trans_costs)
        rendimento_turbo = (p_netto - prezzo_iniziale_turbo) / prezzo_iniziale_turbo
        
    pnl_port = portafoglio_beta * rendimento_indice
    risultati_scenari.append([
        idx_val, pnl_port, pnl_hedge, pnl_port + pnl_hedge, 
        rendimento_indice * 100, rendimento_turbo * 100
    ])

df_scenari = pd.DataFrame(risultati_scenari, columns=[
    'Indice', 'P&L Portafoglio', 'P&L Turbo', 'P&L Netto Hedgiato',
    'Ret_Indice_Pct', 'Ret_Turbo_Pct'
])

tab1, tab2 = st.tabs(["💰 P&L Reale (Margini in €)", "⚖️ Leva e Rendimenti (%)"])

with tab1:
    fig_pnl = go.Figure()
    # P&L Netto Hedgiato (Area)
    fig_pnl.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['P&L Netto Hedgiato'], 
                                 mode='lines', name='P&L Netto (Hedged)', 
                                 line=dict(color='#1B2A47', width=4, shape='spline'),
                                 fill='tozeroy', fillcolor='rgba(27, 42, 71, 0.1)'))
    
    # P&L Portafoglio Unhedged
    fig_pnl.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['P&L Portafoglio'], 
                                 mode='lines', name='P&L Portafoglio (Nudo)', 
                                 line=dict(dash='dash', color='#EF4444', width=2, shape='spline')))
    
    # P&L Copertura
    fig_pnl.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['P&L Turbo'], 
                                 mode='lines', name='P&L Turbo Short', 
                                 line=dict(dash='dot', color='#10B981', width=2, shape='spline')))
    
    fig_pnl.add_vline(x=barriera_turbo_simulata, line_width=2, line_dash="dash", line_color="#F59E0B", annotation_text="KNOCK-OUT")
    fig_pnl.add_hline(y=0, line_width=1, line_color="black")
    
    fig_pnl.update_layout(
        template="plotly_white", height=450, margin=dict(l=0, r=0, t=30, b=0),
        hovermode="x unified", yaxis_title="Profitto/Perdita (€)", xaxis_title="Valore Indice a Scadenza"
    )
    st.plotly_chart(fig_pnl, use_container_width=True)

with tab2:
    fig_ret = go.Figure()
    
    # Rendimento Turbo Short
    fig_ret.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['Ret_Turbo_Pct'], 
                                 mode='lines', name='Rendimento Turbo (%)', 
                                 line=dict(color='#10B981', width=3, shape='spline'),
                                 fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.1)'))
    
    # Rendimento Indice
    fig_ret.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['Ret_Indice_Pct'], 
                                 mode='lines', name='Rendimento Indice (%)', 
                                 line=dict(color='#EF4444', width=3, shape='spline')))
    
    fig_ret.add_vline(x=barriera_turbo_simulata, line_width=2, line_dash="dash", line_color="#F59E0B", annotation_text="KNOCK-OUT")
    fig_ret.add_hline(y=0, line_width=1, line_color="black")
    
    fig_ret.update_layout(
        template="plotly_white", height=450, margin=dict(l=0, r=0, t=30, b=0),
        hovermode="x unified", yaxis_title="Rendimento (%)", xaxis_title="Valore Indice a Scadenza"
    )
    st.plotly_chart(fig_ret, use_container_width=True)
    st.caption("Nota: Questo grafico dimostra la convessità della leva. Il Turbo guadagna percentuali a tre cifre sui ribassi, compensando la perdita lineare del portafoglio maggiore sottostante.")

# --- MONTE CARLO SIMULATION ---
st.markdown("---")
st.subheader("🎲 Stress Test Monte Carlo: Probabilità di Rovina")
if st.button("Esegui 2000 Percorsi (Path-Dependent)"):
    np.random.seed(42)
    dt = 1/252
    paths = 2000
    S = np.zeros((giorni, paths))
    S[0] = valore_iniziale
    
    drift = tasso_finanziamento_netto - 0.5 * volatility**2
    for t in range(1, giorni):
        Z = np.random.standard_normal(paths)
        S[t] = S[t-1] * np.exp(drift * dt + volatility * np.sqrt(dt) * Z)
    
    strike_path = np.array([strike * (1 + tasso_finanziamento_netto * (t / 360)) for t in range(giorni)])
    knocked_out = np.any(S >= strike_path[:, np.newaxis], axis=0)
    prob_ko = np.sum(knocked_out) / paths
    
    col_mc1, col_mc2 = st.columns([1, 2])
    with col_mc1:
        if prob_ko > 0.15:
            st.error(f"⚠️ Rischio di Rovina: **{prob_ko*100:.2f}%**\n\nAlta probabilità di azzeramento prima dei {giorni} giorni.")
        else:
            st.success(f"✅ Rischio Tollerabile: **{prob_ko*100:.2f}%**")
    
    with col_mc2:
        fig_mc = go.Figure()
        for i in range(min(100, paths)):
            color = '#EF4444' if knocked_out[i] else 'rgba(27, 42, 71, 0.05)'
            fig_mc.add_trace(go.Scatter(x=list(range(giorni)), y=S[:, i], mode='lines', line=dict(color=color, width=1), showlegend=False))
        fig_mc.add_trace(go.Scatter(x=list(range(giorni)), y=strike_path, mode='lines', line=dict(color='#F59E0B', width=3, dash='dash'), name='Barriera Dinamica'))
        
        fig_mc.update_layout(
            template="plotly_white", title="Primi 100 percorsi vs Barriera Erosiva", 
            height=300, margin=dict(l=0, r=0, t=40, b=0)
        )
        st.plotly_chart(fig_mc, use_container_width=True)

# --- NOTA METODOLOGICA ---
st.markdown("---")
with st.expander("📚 Nota Metodologica Rigorosa"):
    st.markdown(r"""
    ### 1. Pricing al Tempo Zero
    $$FV_0 = \frac{(K_0 - S_0) \times M}{FX}$$
    ### 2. Aggiustamento Lineare della Barriera (Cost of Carry)
    $$K_t = K_0 \times \left(1 + R_{\text{netto}} \times \frac{t}{360}\right)$$
    ### 3. Hedging Ratio 
    $$N_{\text{reale}} = \lceil \frac{P \times \beta}{S_0 \times (M / FX)} \rceil$$
    ### 4. Rischio di Rovina (First Passage Time)
    $$P(KO) = P(\exists t \in [0, T] : S_t \ge K_t)$$
    """)
