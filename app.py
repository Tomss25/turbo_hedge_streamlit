import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="Turbo Hedging Pro | Reality Check", layout="wide")

# CSS: Styling per Sidebar, Input e Tabelle
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #1E1E1E; }
    [data-testid="stSidebar"] { background-color: #1B2A47; }
    
    /* Titoli, etichette e testo normale in bianco nella sidebar */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { 
        color: #FFFFFF !important; 
    }
    
    /* Input testuali in nero su sfondo bianco per visibilità perfetta */
    [data-testid="stSidebar"] input { 
        color: #1E1E1E !important; background-color: #FFFFFF !important; 
        border-radius: 6px; border: 1px solid #4A5568;
    }
    
    /* Stile per i box in stile tabellare (simulazione Excel) */
    .excel-box {
        background-color: #FFFFFF; border: 1px solid #CBD5E1; 
        border-radius: 8px; padding: 20px; margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .header-tab { font-weight: bold; color: #1B2A47; border-bottom: 2px solid #1B2A47; padding-bottom: 5px; margin-bottom: 15px; }
    .output-val { font-size: 1.2rem; font-weight: bold; color: #0F172A; }
    .output-label { font-size: 0.9rem; color: #64748B; text-transform: uppercase; }
    
    div.stButton > button:first-child {
        background-color: #1B2A47; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #2C426B; color: white; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Tool Copertura Portafoglio - Turbo Short")
st.markdown("Interfaccia classica. Motore matematico reale (attualmente anestetizzato).")

# --- SIDEBAR: INPUT METRICHE AVANZATE (Il Rischio Reale - AZZERATO DI DEFAULT) ---
with st.sidebar:
    st.header("⚙️ Parametri di Stress (Realtà)")
    beta_port = st.number_input("Beta di Portafoglio", value=1.00, step=0.1)
    trans_costs = st.number_input("Commissioni (Entry/Exit) %", value=0.00, step=0.05) / 100
    slippage_exit = st.number_input("Slippage in Uscita (Spread) %", value=0.00, step=0.1) / 100
    
    st.markdown("---")
    st.subheader("Costo di Mantenimento")
    div_yield = st.number_input("Dividend Yield Implicito (%)", value=0.00, step=0.1) / 100
    spread_mm = st.number_input("Margine Market Maker (%)", value=0.00, step=0.1) / 100
    
    st.markdown("---")
    volatility = st.number_input("Volatilità Annua (Monte Carlo) %", value=18.0, step=1.0) / 100

# --- MAIN PAGE: STRUTTURA TABELLARE (EXCEL-LIKE) ---

# TABELLA 1: CARATTERISTICHE TURBO SHORT
st.markdown('<div class="excel-box"><div class="header-tab">CARATTERISTICHE TURBO SHORT</div>', unsafe_allow_html=True)
t1_c1, t1_c2, t1_c3 = st.columns([1, 1, 1])

with t1_c1:
    prezzo_iniziale_turbo = st.number_input("Prezzo Iniziale (€) 📝", value=7.64, step=0.01)
    strike = st.number_input("Strike 📝", value=7505.97, step=10.0)
with t1_c2:
    cambio = st.number_input("Tasso di Cambio 📝", value=1.15, step=0.01)
    multiplo = st.number_input("Multiplo 📝", value=0.01, step=0.001, format="%.4f")
    euribor = st.number_input("Euribor 12M (%) 📝", value=2.46, step=0.01) / 100

# Calcoli Tabella 1
valore_nozionale_iniziale_generico = 6670.75 
fair_value = ((strike - valore_nozionale_iniziale_generico) * multiplo) / cambio 
premio = prezzo_iniziale_turbo - fair_value

with t1_c3:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div class='output-label'>Fair Value (Teorico)</div><div class='output-val'>€ {fair_value:.4f}</div><br>", unsafe_allow_html=True)
    st.markdown(f"<div class='output-label'>Premio Pagato</div><div class='output-val'>€ {premio:.4f}</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)


# TABELLA 2: INDICE DA COPRIRE
st.markdown('<div class="excel-box"><div class="header-tab">INDICE DA COPRIRE</div>', unsafe_allow_html=True)
t2_c1, t2_c2, t2_c3 = st.columns([1, 1, 1])

with t2_c1:
    valore_iniziale = st.number_input("Valore Iniziale 📝", value=6670.75, step=10.0)
    valore_ipotetico = st.number_input("Valore Ipotetico 📝", value=6000.0, step=10.0)
with t2_c2:
    giorni = st.number_input("Giorni 📝", value=60, step=1)

# Ricalcolo Fair Value vero basato sull'input indice aggiornato
fair_value = ((strike - valore_iniziale) * multiplo) / cambio 
premio = prezzo_iniziale_turbo - fair_value

# Calcoli Tabella 2 (Motore Reale)
tasso_finanziamento_netto = euribor - div_yield - spread_mm
strike_aggiustato = strike * (1 + tasso_finanziamento_netto * (giorni / 360))
barriera_turbo_simulata = strike_aggiustato
leva_reale_iniziale = (valore_iniziale * multiplo / cambio) / prezzo_iniziale_turbo

if valore_ipotetico >= barriera_turbo_simulata:
    prezzo_turbo_simulato = 0.0
else:
    prezzo_lordo = max(0, ((strike_aggiustato - valore_ipotetico) * multiplo) / cambio)
    prezzo_turbo_simulato = prezzo_lordo * (1 - slippage_exit) 

with t2_c3:
    st.markdown(f"<div class='output-label'>Prezzo Turbo Short (Netto Uscita)</div><div class='output-val'>€ {prezzo_turbo_simulato:.4f}</div><br>", unsafe_allow_html=True)
    st.markdown(f"<div class='output-label'>Barriera Turbo Short (Dinamica)</div><div class='output-val'>{barriera_turbo_simulata:.2f}</div><br>", unsafe_allow_html=True)
    st.markdown(f"<div class='output-label'>Leva Turbo Short (Iniziale)</div><div class='output-val'>{leva_reale_iniziale:.2f}x</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)


# TABELLA 3: PORTAFOGLIO DA COPRIRE
st.markdown('<div class="excel-box"><div class="header-tab">PORTAFOGLIO DA COPRIRE</div>', unsafe_allow_html=True)
t3_c1, t3_c2, t3_c3 = st.columns([1, 1, 1])

with t3_c1:
    portafoglio = st.number_input("Portafoglio da coprire (€) 📝", value=200000.0, step=10000.0)

# Calcoli Tabella 3 (Motore Reale)
portafoglio_beta = portafoglio * beta_port
valore_nozionale_indice = (valore_iniziale * multiplo) / cambio

n_turbo_teorico = portafoglio_beta / valore_nozionale_indice
n_turbo_reale = int(np.ceil(n_turbo_teorico)) 
capitale_investito = n_turbo_reale * prezzo_iniziale_turbo
costo_transazione_ingresso = capitale_investito * trans_costs

valore_portafoglio_simulato = portafoglio * (valore_ipotetico / valore_iniziale)
valore_copertura_lordo = n_turbo_reale * prezzo_turbo_simulato
costo_transazione_uscita = valore_copertura_lordo * trans_costs
valore_copertura_netto = valore_copertura_lordo - costo_transazione_uscita

totale_impiegato = portafoglio + capitale_investito
pnl_portafoglio = valore_portafoglio_simulato - portafoglio
pnl_copertura = valore_copertura_netto - capitale_investito - costo_transazione_ingresso
pnl_netto_totale = pnl_portafoglio + pnl_copertura
percentuale_simulata = (pnl_netto_totale / portafoglio) * 100

with t3_c2:
    st.markdown(f"<div class='output-label'>N. Turbo Short (Arrotondato)</div><div class='output-val'>{n_turbo_reale}</div><br>", unsafe_allow_html=True)
    st.markdown(f"<div class='output-label'>Capitale Copertura</div><div class='output-val'>€ {capitale_investito:,.2f}</div><br>", unsafe_allow_html=True)
    st.markdown(f"<div class='output-label'>Valore Portafoglio Simulato</div><div class='output-val'>€ {valore_portafoglio_simulato:,.2f}</div>", unsafe_allow_html=True)

with t3_c3:
    st.markdown(f"<div class='output-label'>Totale P&L Netto (Port. + Hedge)</div><div class='output-val' style='color: {'#10B981' if pnl_netto_totale >=0 else '#EF4444'};'>€ {pnl_netto_totale:,.2f}</div><br>", unsafe_allow_html=True)
    st.markdown(f"<div class='output-label'>Valore Copertura Simulato (Netto)</div><div class='output-val'>€ {valore_copertura_netto:,.2f}</div><br>", unsafe_allow_html=True)
    st.markdown(f"<div class='output-label'>% Scostamento Rischio (Drag)</div><div class='output-val' style='color: {'#10B981' if percentuale_simulata >=0 else '#EF4444'};'>{percentuale_simulata:,.2f}%</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)


# --- GRAFICI E SIMULAZIONI ---
st.markdown("---")
tab1, tab2 = st.tabs(["📈 Analisi Visiva: Copertura e Rendimenti", "🎲 Stress Test Monte Carlo"])

with tab1:
    scenari_indice = np.linspace(valore_iniziale * 0.8, valore_iniziale * 1.15, 30)
    risultati_scenari = []

    for idx_val in scenari_indice:
        rendimento_indice = (idx_val / valore_iniziale) - 1
        if idx_val >= barriera_turbo_simulata:
            p_netto = 0.0
            v_hedge = 0.0
            pnl_hedge = -capitale_investito - costo_transazione_ingresso
            rendimento_turbo = -1.0 
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

    fig_pnl = go.Figure()
    fig_pnl.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['P&L Netto Hedgiato'], 
                                 mode='lines', name='P&L Netto (Hedged)', 
                                 line=dict(color='#1B2A47', width=4, shape='spline'),
                                 fill='tozeroy', fillcolor='rgba(27, 42, 71, 0.1)'))
    fig_pnl.add_trace(go.Scatter(x=df_scenari['Indice'], y=df_scenari['P&L Portafoglio'], 
                                 mode='lines', name='P&L Portafoglio (Nudo)', 
                                 line=dict(dash='dash', color='#EF4444', width=2, shape='spline')))
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
    st.subheader("Probabilità di Rovina")
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
                st.error(f"⚠️ Rischio di Rovina: **{prob_ko*100:.2f}%**\n\nAlta probabilità di azzeramento.")
            else:
                st.success(f"✅ Rischio Tollerabile: **{prob_ko*100:.2f}%**")
        
        with col_mc2:
            fig_mc = go.Figure()
            for i in range(min(100, paths)):
                color = '#EF4444' if knocked_out[i] else 'rgba(27, 42, 71, 0.05)'
                fig_mc.add_trace(go.Scatter(x=list(range(giorni)), y=S[:, i], mode='lines', line=dict(color=color, width=1), showlegend=False))
            fig_mc.add_trace(go.Scatter(x=list(range(giorni)), y=strike_path, mode='lines', line=dict(color='#F59E0B', width=3, dash='dash'), name='Barriera Dinamica'))
            
            fig_mc.update_layout(
                template="plotly_white", title="Primi 100 percorsi vs Barriera", 
                height=300, margin=dict(l=0, r=0, t=40, b=0)
            )
            st.plotly_chart(fig_mc, use_container_width=True)

# --- NOTA METODOLOGICA ---
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
