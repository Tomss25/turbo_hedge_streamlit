import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="Turbo Hedging Pro | Reality Check", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F4F7F6; color: #1E1E1E; }
    [data-testid="stSidebar"] { background-color: #1B2A47; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    div[data-testid="metric-container"] {
        background-color: #FFFFFF; border: 1px solid #E0E0E0;
        padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div.stButton > button:first-child {
        background-color: #1B2A47; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #2C426B; color: white; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Tool Copertura Portafoglio - Turbo Short")
st.markdown("Calcolo dell'hedge ratio reale, P&L netto con frizioni di mercato e stress test Monte Carlo.")

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
st.subheader("📈 Scenario Analysis (Netto Frizioni)")
scenari_indice = np.linspace(valore_iniziale * 0.8, valore_iniziale * 1.15, 20)
risultati_scenari = []

for idx_val in scenari_indice:
    if idx_val >= barriera_turbo_simulata:
        pnl_hedge = -capitale_investito - costo_transazione_ingresso
    else:
        p_lordo = ((strike_aggiustato - idx_val) * multiplo) / cambio
        p_netto = p_lordo * (1 - slippage_exit)
        v_hedge = n_turbo_reale * p_netto
        pnl_hedge = v_hedge - capitale_investito - costo_transazione_ingresso - (v_hedge * trans_costs)
        
    pnl_port = portafoglio_beta * ((idx_val / valore_iniziale) - 1)
    risultati_scenari.append([idx_val, pnl_port, pnl_hedge, pnl_port + pnl_hedge])

df_scenari = pd.DataFrame(risultati_scenari, columns=['Indice', 'P&L Portafoglio', 'P&L Turbo', 'P&L Netto Hedgiato'])

fig_scenario = go.Figure()
fig_scenario.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['P&L Netto Hedgiato'], mode='lines+markers', name='P&L Netto (Hedged)', line=dict(color='#1B2A47', width=3)))
fig_scenario.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['P&L Portafoglio'], mode='lines', name='P&L Portafoglio (Unhedged)', line=dict(dash='dash', color='#FF4B4B')))
fig_scenario.add_vline(x=barriera_turbo_simulata, line_width=2, line_dash="dash", line_color="orange", annotation_text="KNOCK-OUT")
fig_scenario.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='white', hovermode="x unified")
st.plotly_chart(fig_scenario, use_container_width=True)

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
            color = 'red' if knocked_out[i] else 'rgba(27, 42, 71, 0.1)'
            fig_mc.add_trace(go.Scatter(x=list(range(giorni)), y=S[:, i], mode='lines', line=dict(color=color, width=1), showlegend=False))
        fig_mc.add_trace(go.Scatter(x=list(range(giorni)), y=strike_path, mode='lines', line=dict(color='orange', width=3, dash='dash'), name='Barriera Dinamica'))
        fig_mc.update_layout(title="Primi 100 percorsi vs Barriera Erosiva", height=300, plot_bgcolor='white', margin=dict(l=0, r=0, t=30, b=0))
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