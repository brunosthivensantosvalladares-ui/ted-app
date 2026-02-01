import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime, time, timedelta
from io import BytesIO
from fpdf import FPDF

# --- CONFIGURAÇÕES DE MARCA ---
NOME_SISTEMA = "Ted"
SLOGAN = "Seu Controle. Nossa Prioridade."
LOGO_URL = "https://i.postimg.cc/wTbmmT7r/logo-png.png" 
ORDEM_AREAS = ["Motorista", "Borracharia", "Mecânica", "Elétrica", "Chapeamento", "Limpeza"]
LISTA_TURNOS = ["Não definido", "Dia", "Noite"]
COR_AZUL, COR_VERDE = "#3282b8", "#8ac926"

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title=f"{NOME_SISTEMA} - Tudo em Dia", layout="wide", page_icon="🛠️")

# --- CSS PARA RESPONSIVIDADE E UNIDADE VISUAL ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fa; }}
    .stButton>button {{ background-color: {COR_AZUL}; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%; }}
    .stButton>button:hover {{ background-color: #276691; color: white; border: none; }}
    [data-testid="stSidebar"] {{ background-color: #ffffff; border-right: 1px solid #e0e0e0; }}
    .area-header {{ color: {COR_VERDE}; font-weight: bold; font-size: 1.1rem; border-left: 5px solid {COR_AZUL}; padding-left: 10px; margin-top: 20px; }}
    div[data-testid="stRadio"] > div {{ background-color: #f1f3f5; padding: 10px; border-radius: 10px; }}
    
    /* MENU MOBILE NO TOPO (HORIZONTAL) */
    @media (min-width: 801px) {{
        .mobile-nav {{ display: none; }}
    }}
    @media (max-width: 800px) {{
        .mobile-nav {{
            display: flex;
            flex-direction: row;
            justify-content: space-around;
            background-color: white;
            padding: 10px 5px;
            border-bottom: 2px solid {COR_AZUL};
            position: sticky;
            top: 0;
            z-index: 1000;
            margin-bottom: 10px;
        }}
        /* Forçar colunas de botões lado a lado no mobile */
        [data-testid="column"] {{
            width: fit-content !important;
            flex: 1 1 auto !important;
        }}
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE E BANCO ---
@st.cache_resource
def get_engine():
    db_url = os.environ.get("database_url", "postgresql://neondb_owner:npg_WRMhXvJVY79d@ep-lucky-sound-acy7xdyi-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require")
    return create_engine(db_url.replace("postgres://", "postgresql://", 1), pool_pre_ping=True)

def inicializar_banco():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS tarefas (id SERIAL PRIMARY KEY, data TEXT, executor TEXT, prefixo TEXT, inicio_disp TEXT, fim_disp TEXT, descricao TEXT, area TEXT, turno TEXT, realizado BOOLEAN DEFAULT FALSE, id_chamado INTEGER, origem TEXT)"))
            conn.execute(text("CREATE TABLE IF NOT EXISTS chamados (id SERIAL PRIMARY KEY, motorista TEXT, prefixo TEXT, descricao TEXT, data_solicitacao TEXT, status TEXT DEFAULT 'Pendente')"))
            try: conn.execute(text("ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS origem TEXT"))
            except: pass
            conn.commit()
    except: pass

def to_excel_native(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Manutencoes')
    return output.getvalue()

@st.cache_data(show_spinner=False)
def gerar_pdf_periodo(df_periodo, data_inicio, data_fim):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16); pdf.set_text_color(50, 130, 184)
    pdf.cell(190, 10, f"Relatorio de Manutencao - {NOME_SISTEMA}", ln=True, align="C")
    pdf.set_font("Arial", "", 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 10, f"Periodo: {data_inicio.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(5)
    for d_process in sorted(df_periodo['data'].unique(), reverse=True):
        d_formatada = pd.to_datetime(d_process).strftime('%d/%m/%Y')
        pdf.set_font("Arial", "B", 14); pdf.cell(190, 10, f"Data: {d_formatada}", ln=True)
        for area in ORDEM_AREAS:
            df_area = df_periodo[(df_periodo['data'] == d_process) & (df_periodo['area'] == area)]
            if not df_area.empty:
                pdf.set_font("Arial", "B", 11); pdf.set_fill_color(230, 230, 230)
                pdf.cell(190, 7, f" Area: {area}", ln=True, fill=True)
                for _, row in df_area.iterrows():
                    pdf.set_font("Arial", "", 8); pdf.cell(190, 6, f"{row['prefixo']} | {row['executor']} | {str(row['descricao'])[:80]}", ln=True)
                pdf.ln(3)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. LÓGICA DE LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False

if not st.session_state["logado"]:
    _, col_login, _ = st.columns([1.2, 1, 1.2])
    with col_login:
        placeholder_topo = st.empty()
        placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span style='color: {COR_AZUL};'>T</span><span style='color: {COR_VERDE};'>ed</span></h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-style: italic; color: #555; margin-top: 0;'>{SLOGAN}</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            user = st.text_input("Usuário", key="u_log").lower()
            pw = st.text_input("Senha", type="password", key="p_log")
            
            if st.button("Acessar Painel Ted", use_container_width=True):
                users = {"bruno": "master789", "admin": "12345", "motorista": "12345"}
                if user in users and users[user] == pw:
                    st.session_state["logado"], st.session_state["perfil"] = True, ("admin" if user != "motorista" else "motorista")
                    st.rerun()
                else: st.error("Usuário ou senha incorretos")
else:
    engine = get_engine(); inicializar_banco()
    
    # Navegação Híbrida
    if st.session_state["perfil"] == "motorista":
        opcoes = ["✍️ Abrir Solicitação", "📜 Status"]
        icones = ["✍️", "📜"]
    else:
        opcoes = ["📅 Agenda Principal", "📋 Cadastro Direto", "📥 Chamados Oficina", "📊 Indicadores"]
        icones = ["📅", "📋", "📥", "📊"]

    # Barra Lateral (Desktop)
    with st.sidebar:
        st.image(LOGO_URL, use_container_width=True)
        idx_ini = 0
        if "escolha_mob" in st.session_state and st.session_state["escolha_mob"] in opcoes:
            idx_ini = opcoes.index(st.session_state["escolha_mob"])
        escolha = st.radio("NAVEGAÇÃO", opcoes, index=idx_ini)
        if st.button("Sair"): st.session_state["logado"] = False; st.rerun()

    # Barra Mobile (Topo Horizontal)
    st.markdown('<div class="mobile-nav">', unsafe_allow_html=True)
    cols_mob = st.columns(len(opcoes))
    for i, opt in enumerate(opcoes):
        if cols_mob[i].button(icones[i], key=f"mob_nav_{opt}"):
            st.session_state["escolha_mob"] = opt
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- PÁGINAS MOTORISTA ---
    if escolha == "✍️ Abrir Solicitação":
        st.subheader("✍️ Nova Solicitação")
        st.info("💡 **Dica:** Informe o prefixo e detalhe o problema.")
        with st.form("f_ch", clear_on_submit=True):
            p, d = st.text_input("Prefixo"), st.text_area("Descrição")
            if st.form_submit_button("Enviar"):
                if p and d:
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO chamados (motorista, prefixo, descricao, data_solicitacao, status) VALUES ('motorista', :p, :d, :dt, 'Pendente')"), {"p": p, "d": d, "dt": str(datetime.now().date())})
                        conn.commit()
                    st.success("✅ Solicitação enviada!")

    elif escolha == "📜 Status":
        st.subheader("📜 Meus Veículos")
        df_status = pd.read_sql("SELECT prefixo, data_solicitacao as data, status, descricao FROM chamados ORDER BY id DESC", engine)
        st.dataframe(df_status, use_container_width=True, hide_index=True)

    # --- PÁGINAS ADMIN ---
    elif escolha == "📋 Cadastro Direto":
        st.subheader("📝 Agendamento Direto")
        st.info("💡 **Atenção:** Use este formulário para serviços preventivos.")
        with st.form("f_d", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: d_i = st.date_input("Data", datetime.now())
            with c2: e_i = st.text_input("Executor")
            with c3: p_i = st.text_input("Prefixo")
            with c4: a_i = st.selectbox("Área", ORDEM_AREAS)
            ds_i, t_i = st.text_area("Descrição"), st.selectbox("Turno", LISTA_TURNOS)
            if st.form_submit_button("Confirmar"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, origem) VALUES (:dt, :ex, :pr, '00:00', '00:00', :ds, :ar, :tu, 'Direto')"), {"dt": str(d_i), "ex": e_i, "pr": p_i, "ds": ds_i, "ar": a_i, "tu": t_i})
                    conn.commit()
                st.success("✅ Cadastrado!"); st.rerun()
        
        st.divider(); st.subheader("📋 Lista Geral")
        df_lista = pd.read_sql("SELECT * FROM tarefas ORDER BY data DESC, id DESC", engine)
        if not df_lista.empty:
            df_lista['data'] = pd.to_datetime(df_lista['data']).dt.date
            df_lista['Exc'] = False
            ed_l = st.data_editor(df_lista[['Exc', 'data', 'turno', 'executor', 'prefixo', 'descricao', 'area', 'id']], hide_index=True, use_container_width=True, key="ed_lista")
            if st.button("🗑️ Excluir Selecionados"):
                with engine.connect() as conn:
                    for i in ed_l[ed_l['Exc']==True]['id'].tolist(): conn.execute(text("DELETE FROM tarefas WHERE id = :id"), {"id": int(i)})
                    conn.commit(); st.warning("🗑️ Excluído!"); st.rerun()
            if st.session_state.ed_lista["edited_rows"]:
                with engine.connect() as conn:
                    for idx, changes in st.session_state.ed_lista["edited_rows"].items():
                        rid = int(df_lista.iloc[idx]['id'])
                        for col, val in changes.items():
                            if col != 'Exc': conn.execute(text(f"UPDATE tarefas SET {col} = :v WHERE id = :i"), {"v": str(val), "i": rid})
                    conn.commit(); st.rerun()

    elif escolha == "📥 Chamados Oficina":
        st.subheader("📥 Aprovação")
        st.info("💡 Preencha os campos e marque 'Aprovar' na última coluna.")
        df_p = pd.read_sql("SELECT id, data_solicitacao, prefixo, descricao FROM chamados WHERE status = 'Pendente' ORDER BY id DESC", engine)
        if not df_p.empty:
            if 'df_ap_work' not in st.session_state:
                df_p['Executor'] = "Pendente"; df_p['Area_Destino'] = "Mecânica"; df_p['Data_Programada'] = datetime.now().date(); df_p['Aprovar'] = False
                st.session_state.df_ap_work = df_p

            ed_c = st.data_editor(st.session_state.df_ap_work, hide_index=True, use_container_width=True, column_config={
                "data_solicitacao": "Aberto em",
                "Data_Programada": st.column_config.DateColumn("Data Programada"),
                "Area_Destino": st.column_config.SelectboxColumn("Área", options=ORDEM_AREAS),
                "Aprovar": st.column_config.CheckboxColumn("Aprovar?"),
                "id": None
            }, key="editor_chamados")

            if st.button("Processar Agendamentos"):
                selecionados = ed_c[ed_c['Aprovar'] == True]
                if not selecionados.empty:
                    with engine.connect() as conn:
                        for _, r in selecionados.iterrows():
                            conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, id_chamado, origem) VALUES (:dt, :ex, :pr, '00:00', '00:00', :ds, :ar, 'Não definido', :ic, 'Chamado')"), {"dt": str(r['Data_Programada']), "ex": r['Executor'], "pr": r['prefixo'], "ds": r['descricao'], "ar": r['Area_Destino'], "ic": r['id']})
                            conn.execute(text("UPDATE chamados SET status = 'Agendado' WHERE id = :id"), {"id": r['id']})
                        conn.commit(); st.success("✅ Agendados!"); del st.session_state.df_ap_work; st.rerun()

    elif escolha == "📅 Agenda Principal":
        st.subheader("📅 Agenda")
        df_a = pd.read_sql("SELECT * FROM tarefas ORDER BY data DESC", engine)
        hoje, amanha = datetime.now().date(), datetime.now().date() + timedelta(days=1)
        c_per, c_pdf, c_xls = st.columns([0.6, 0.2, 0.2])
        with c_per: p_sel = st.date_input("Filtro", [hoje, amanha], key="dt_filter")
        if not df_a.empty and len(p_sel) == 2:
            df_a['data'] = pd.to_datetime(df_a['data']).dt.date
            df_f = df_a[(df_a['data'] >= p_sel[0]) & (df_a['data'] <= p_sel[1])]
            with c_pdf: st.download_button("📥 PDF", gerar_pdf_periodo(df_f, p_sel[0], p_sel[1]), f"Relatorio_Ted.pdf")
            with c_xls: st.download_button("📊 XLS", to_excel_native(df_f), "Relatorio_Ted.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with st.form("form_agenda"):
                btn_salvar = st.form_submit_button("💾 Salvar Tudo")
                for d in sorted(df_f['data'].unique(), reverse=True):
                    st.markdown(f"#### 🗓️ {d.strftime('%d/%m/%Y')}")
                    for area in ORDEM_AREAS:
                        df_area_f = df_f[(df_f['data'] == d) & (df_f['area'] == area)]
                        if not df_area_f.empty:
                            st.markdown(f"<p class='area-header'>📍 {area}</p>", unsafe_allow_html=True)
                            st.data_editor(df_area_f[['realizado', 'executor', 'prefixo', 'inicio_disp', 'fim_disp', 'turno', 'descricao', 'id', 'id_chamado']], column_config={"realizado": st.column_config.CheckboxColumn("OK", width="small"), "inicio_disp": "Início", "fim_disp": "Fim"}, hide_index=True, use_container_width=True, key=f"ed_ted_{d}_{area}")
                if btn_salvar:
                    with engine.connect() as conn:
                        for key in st.session_state.keys():
                            if key.startswith("ed_ted_") and st.session_state[key]["edited_rows"]:
                                dt_ref, ar_ref = key.split("_")[2], key.split("_")[3]
                                df_ref_rows = df_f[(df_f['data'].astype(str) == dt_ref) & (df_f['area'] == ar_ref)]
                                for idx, changes in st.session_state[key]["edited_rows"].items():
                                    row_data = df_ref_rows.iloc[idx]; rid, id_ch = int(row_data['id']), row_data['id_chamado']
                                    for col, val in changes.items():
                                        conn.execute(text(f"UPDATE tarefas SET {col} = :v WHERE id = :i"), {"v": str(val), "i": rid})
                                        if col == 'realizado' and val is True and id_ch: conn.execute(text("UPDATE chamados SET status = 'Concluído' WHERE id = :ic"), {"ic": int(id_ch)})
                    conn.commit(); st.success("✅ Salvo!"); st.rerun()

    elif escolha == "📊 Indicadores":
        st.subheader("📊 Indicadores")
        c1, c2 = st.columns(2)
        df_ind = pd.read_sql("SELECT area, realizado FROM tarefas", engine)
        with c1: st.markdown("**Por Área**"); st.bar_chart(df_ind['area'].value_counts(), color=COR_AZUL); st.caption("🔍 Carga por setor.")
        with c2: 
            if not df_ind.empty:
                df_st = df_ind['realizado'].map({True: 'Concluído', False: 'Pendente'}).value_counts()
                st.markdown("**Eficiência**"); st.bar_chart(df_st, color=COR_VERDE); st.caption("🔍 Capacidade de entrega.")
        
        st.divider(); st.markdown("**⏳ Lead Time (Tempo de Resposta)**")
        df_lead = pd.read_sql("SELECT c.data_solicitacao, t.data as data_conclusao FROM chamados c JOIN tarefas t ON c.id = t.id_chamado WHERE t.realizado = True", engine)
        if not df_lead.empty:
            df_lead['data_solicitacao'], df_lead['data_conclusao'] = pd.to_datetime(df_lead['data_solicitacao']), pd.to_datetime(df_lead['data_conclusao'])
            df_lead['dias'] = (df_lead['data_conclusao'] - df_lead['data_solicitacao']).dt.days.apply(lambda x: max(x, 0))
            col_m1, col_m2 = st.columns([0.3, 0.7])
            with col_m1: st.metric("Média Global", f"{df_lead['dias'].mean():.1f} Dias"); st.caption("🔍 Média entre chamado e entrega.")
            with col_m2: df_ev = df_lead.groupby('data_conclusao')['dias'].mean().reset_index(); st.line_chart(df_ev.set_index('data_conclusao'), color=COR_AZUL)
