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
# LINK DIRETO E ESTÁVEL DA LOGO
LOGO_URL = "https://raw.githubusercontent.com/brunofrois/ted-app/main/logo.png" 
LISTA_TURNOS = ["Não definido", "Dia", "Noite"]
ORDEM_AREAS = ["Motorista", "Borracharia", "Mecânica", "Elétrica", "Chapeamento", "Limpeza"]

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title=f"{NOME_SISTEMA} - Tudo em Dia", layout="wide", page_icon="🛠️")

# --- CSS PARA UNIDADE VISUAL ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fa; }}
    .stButton>button {{ background-color: #0066cc; color: white; border-radius: 8px; border: none; font-weight: bold; }}
    .stButton>button:hover {{ background-color: #004d99; border: none; }}
    [data-testid="stSidebar"] {{ background-color: #ffffff; border-right: 1px solid #e0e0e0; }}
    .area-header {{ color: #28a745; font-weight: bold; font-size: 1.1rem; border-left: 5px solid #0066cc; padding-left: 10px; margin-top: 20px; }}
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO OTIMIZADA ---
@st.cache_resource
def get_engine():
    db_url = os.environ.get("database_url", "postgresql://neondb_owner:npg_WRMhXvJVY79d@ep-lucky-sound-acy7xdyi-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require")
    return create_engine(db_url.replace("postgres://", "postgresql://", 1), pool_pre_ping=True)

# --- FUNÇÃO PARA GERAR PDF ---
@st.cache_data(show_spinner=False)
def gerar_pdf_periodo(df_periodo, data_inicio, data_fim):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(190, 10, f"Relatorio de Manutencao - {NOME_SISTEMA}", ln=True, align="C")
    pdf.ln(5)
    df_periodo = df_periodo.sort_values(by=['data', 'area'])
    for d_process in df_periodo['data'].unique():
        d_formatada = pd.to_datetime(d_process).strftime('%d/%m/%Y')
        pdf.set_font("Arial", "B", 14); pdf.cell(190, 10, f"Data: {d_formatada}", ln=True)
        for area in ORDEM_AREAS:
            df_area = df_periodo[(df_periodo['data'] == d_process) & (df_periodo['area'] == area)]
            if not df_area.empty:
                pdf.set_font("Arial", "B", 11); pdf.set_fill_color(230, 230, 230)
                pdf.cell(190, 7, f" Area: {area}", ln=True, fill=True)
                for _, row in df_area.iterrows():
                    pdf.set_font("Arial", "", 8)
                    pdf.cell(190, 6, f"{row['prefixo']} | {row['executor']} | {str(row['descricao'])[:80]}", ln=True)
                pdf.ln(3)
    return pdf.output() if isinstance(pdf.output(), (bytes, bytearray)) else bytes(pdf.output(), 'latin-1')

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

# --- 3. LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False

if not st.session_state["logado"]:
    _, col_login, _ = st.columns([1.2, 1, 1.2])
    with col_login:
        # LOGO NO LOGIN COM FALLBACK
        st.image(LOGO_URL, use_container_width=True)
        st.markdown(f"<p style='text-align: center; font-style: italic; color: #555; margin-bottom: 20px;'>{SLOGAN}</p>", unsafe_allow_html=True)
        with st.container(border=True):
            user = st.text_input("Usuário", key="u_log").lower()
            pw = st.text_input("Senha", type="password", key="p_log")
            if st.button("Acessar Painel Ted", use_container_width=True):
                users = {"bruno": "master789", "admin": "12345", "motorista": "12345"}
                if user in users and users[user] == pw:
                    st.session_state["logado"], st.session_state["perfil"] = True, ("admin" if user != "motorista" else "motorista")
                    st.rerun()
                else: st.error("Acesso negado")
else:
    engine = get_engine()
    inicializar_banco()
    
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.image(LOGO_URL, use_container_width=True)
        st.markdown(f"<p style='text-align: center; font-size: 0.85rem; color: #666; margin-top:-10px;'>{SLOGAN}</p>", unsafe_allow_html=True)
        st.divider()
        st.write(f"👤 Perfil: **{st.session_state['perfil'].capitalize()}**")
        if st.button("Sair do Sistema", use_container_width=True):
            st.session_state["logado"] = False; st.rerun()

    if st.session_state["perfil"] == "motorista":
        aba_solic, aba_hist = st.tabs(["✍️ Abrir Solicitação", "📜 Meus Chamados"])
        with aba_solic:
            st.info("💡 *Descreva o problema do veículo para a oficina.*")
            with st.form("f_ch", clear_on_submit=True):
                p, d = st.text_input("Prefixo"), st.text_area("Descrição do Defeito")
                if st.form_submit_button("Enviar para Oficina"):
                    if p and d:
                        with engine.connect() as conn:
                            conn.execute(text("INSERT INTO chamados (motorista, prefixo, descricao, data_solicitacao, status) VALUES ('motorista', :p, :d, :dt, 'Pendente')"), {"p": p, "d": d, "dt": str(datetime.now().date())})
                            conn.commit()
                        st.success("Solicitação enviada com sucesso!")
        with aba_hist:
            st.dataframe(pd.read_sql("SELECT prefixo, data_solicitacao as data, status, descricao FROM chamados ORDER BY id DESC", engine), use_container_width=True)

    else:
        aba_cad, aba_cham, aba_agen, aba_demo = st.tabs(["📋 Cadastro Direto", "📥 Chamados", "📅 Agenda Principal", "📊 Indicadores"])

        with aba_cad:
            st.subheader("📝 Novo Agendamento")
            with st.form("f_d", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns(4)
                with c1: d_i = st.date_input("Data", datetime.now())
                with c2: e_i = st.text_input("Executor")
                with c3: p_i = st.text_input("Prefixo")
                with c4: a_i = st.selectbox("Área", ORDEM_AREAS)
                ce, cd = st.columns([3, 1])
                with ce: ds_i = st.text_area("Descrição", height=136)
                with cd:
                    t_i = st.selectbox("Turno", LISTA_TURNOS)
                    if st.form_submit_button("Confirmar", use_container_width=True):
                        with engine.connect() as conn:
                            conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, origem) VALUES (:dt, :ex, :pr, '00:00', '00:00', :ds, :ar, :tu, 'Direto')"), {"dt": str(d_i), "ex": e_i, "pr": p_i, "ds": ds_i, "ar": a_i, "tu": t_i})
                            conn.commit()
                        st.rerun()
            st.divider()
            
            @st.fragment
            def secao_lista_cadastro():
                df_lista = pd.read_sql("SELECT * FROM tarefas ORDER BY data DESC, id DESC", engine)
                if not df_lista.empty:
                    if 'origem' not in df_lista.columns: df_lista['origem'] = 'Direto'
                    df_lista['origem'] = df_lista['origem'].fillna('Direto')
                    df_lista['data'] = pd.to_datetime(df_lista['data']).dt.date
                    df_lista['Exc'] = False
                    ed_l = st.data_editor(df_lista[['Exc', 'data', 'turno', 'origem', 'executor', 'prefixo', 'descricao', 'area', 'id']], hide_index=True, use_container_width=True, key="ed_lista")
                    if st.button("🗑️ Excluir Selecionados"):
                        with engine.connect() as conn:
                            for i in ed_l[ed_l['Exc']==True]['id'].tolist(): conn.execute(text("DELETE FROM tarefas WHERE id = :id"), {"id": int(i)})
                            conn.commit()
                        st.rerun()
                    if st.session_state.ed_lista["edited_rows"]:
                        with engine.connect() as conn:
                            for idx, changes in st.session_state.ed_lista["edited_rows"].items():
                                rid = int(df_lista.iloc[idx]['id'])
                                for col, val in changes.items():
                                    if col != 'Exc': conn.execute(text(f"UPDATE tarefas SET {col} = :v WHERE id = :i"), {"v": str(val), "i": rid})
                            conn.commit()
                        st.rerun()
            secao_lista_cadastro()

        with aba_cham:
            st.subheader("📥 Aprovação de Solicitações")
            @st.fragment
            def secao_aprovacao():
                df_p = pd.read_sql("SELECT * FROM chamados WHERE status != 'Agendado' AND status != 'Concluído'", engine)
                if not df_p.empty:
                    if 'df_aprov' not in st.session_state:
                        st.session_state.df_aprov = df_p.copy()
                        st.session_state.df_aprov['Responsável'] = "Pendente"; st.session_state.df_aprov['Data'] = datetime.now().date()
                        st.session_state.df_aprov['Área'] = "Mecânica"; st.session_state.df_aprov['OK'] = False
                    
                    ed_c = st.data_editor(st.session_state.df_aprov, hide_index=True, use_container_width=True, column_config={"id": None, "motorista": None, "status": None, "OK": st.column_config.CheckboxColumn("Aprovar?"), "Responsável": st.column_config.TextColumn("Executor"), "Área": st.column_config.SelectboxColumn("Área", options=ORDEM_AREAS)}, key="editor_chamados")
                    if st.button("Mover para Agenda", use_container_width=True):
                        selecionados = ed_c[ed_c['OK'] == True]
                        if not selecionados.empty:
                            with engine.connect() as conn:
                                for _, r in selecionados.iterrows():
                                    conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, id_chamado, origem) VALUES (:dt, :ex, :pr, '00:00', '00:00', :ds, :ar, 'Não definido', :ic, 'Chamado')"), {"dt": str(r['Data']), "ex": r['Responsável'], "pr": r['prefixo'], "ds": r['descricao'], "ar": r['Área'], "ic": r['id']})
                                    conn.execute(text("UPDATE chamados SET status = 'Agendado' WHERE id = :id"), {"id": r['id']})
                                conn.commit()
                            del st.session_state.df_aprov; st.rerun()
                else: st.info("Nenhum chamado pendente.")
            secao_aprovacao()

        with aba_agen:
            st.subheader("📅 Agenda Principal")
            df_a_carrega = pd.read_sql("SELECT * FROM tarefas ORDER BY data DESC", engine)
            hoje, amanha = datetime.now().date(), datetime.now().date() + timedelta(days=1)
            c_per, c_pdf = st.columns([0.8, 0.2])
            with c_per: p_sel = st.date_input("Filtrar Período", [hoje, amanha], key="dt_filter")
            
            if not df_a_carrega.empty:
                if 'origem' not in df_a_carrega.columns: df_a_carrega['origem'] = 'Direto'
                df_a_carrega['origem'] = df_a_carrega['origem'].fillna('Direto')
                df_a_carrega['data'] = pd.to_datetime(df_a_carrega['data']).dt.date
                df_f_per = df_a_carrega[(df_a_carrega['data'] >= p_sel[0]) & (df_a_carrega['data'] <= p_sel[1])] if len(p_sel) == 2 else df_a_carrega
                with c_pdf: st.write(""); st.download_button("📥 PDF", gerar_pdf_periodo(df_f_per, p_sel[0], p_sel[1]), "Relatorio_Ted.pdf")

                st.divider()
                with st.form("form_agenda"):
                    col_btn, col_info = st.columns([0.2, 0.8])
                    with col_btn: btn_salvar = st.form_submit_button("Salvar Tudo", use_container_width=True)
                    with col_info: st.info("💡 *Marque OK para concluir o serviço para o motorista.*")

                    st.markdown("""<style>[data-testid="stTable"] td:nth-child(4), [data-testid="stTable"] td:nth-child(5) {background-color: #d4edda !important; font-weight: bold;}</style>""", unsafe_allow_html=True)

                    for d in sorted(df_f_per['data'].unique(), reverse=True):
                        st.markdown(f"#### 🗓️ {d.strftime('%d/%m/%Y')}")
                        for area in ORDEM_AREAS:
                            df_area_f = df_f_per[(df_f_per['data'] == d) & (df_f_per['area'] == area)]
                            if not df_area_f.empty:
                                st.markdown(f"<p class='area-header'>📍 {area}</p>", unsafe_allow_html=True)
                                st.data_editor(
                                    df_area_f[['realizado', 'origem', 'executor', 'prefixo', 'inicio_disp', 'fim_disp', 'turno', 'descricao', 'id', 'id_chamado']],
                                    column_config={
                                        "id": None, "id_chamado": None, 
                                        "origem": st.column_config.TextColumn("Origem", disabled=True), 
                                        "realizado": st.column_config.CheckboxColumn("OK"), 
                                        "inicio_disp": st.column_config.TextColumn("Início"), 
                                        "fim_disp": st.column_config.TextColumn("Fim")
                                    }, 
                                    hide_index=True, use_container_width=True, key=f"ed_ted_{d}_{area}")

                if btn_salvar:
                    with engine.connect() as conn:
                        for key in st.session_state.keys():
                            if key.startswith("ed_ted_") and st.session_state[key]["edited_rows"]:
                                partes = key.split("_")
                                dt_k, ar_k = datetime.strptime(partes[2], '%Y-%m-%d').date(), partes[3]
                                df_referencia = df_f_per[(df_f_per['data'] == dt_k) & (df_f_per['area'] == ar_k)]
                                for idx, changes in st.session_state[key]["edited_rows"].items():
                                    row_data = df_referencia.iloc[idx]
                                    rid, id_chamado_vinculado = int(row_data['id']), row_data['id_chamado']
                                    for col, val in changes.items():
                                        conn.execute(text(f"UPDATE tarefas SET {col} = :v WHERE id = :i"), {"v": str(val), "i": rid})
                                        if col == 'realizado' and val is True and id_chamado_vinculado:
                                            conn.execute(text("UPDATE chamados SET status = 'Concluído' WHERE id = :ic"), {"ic": int(id_chamado_vinculado)})
                        conn.commit()
                    st.rerun()

        with aba_demo:
            st.subheader("📊 Indicadores de Manutenção")
            df_ind = pd.read_sql("SELECT area, realizado FROM tarefas", engine)
            if not df_ind.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Volume por Área**")
                    st.bar_chart(df_ind['area'].value_counts(), color="#0066cc")
                with c2:
                    st.markdown("**Serviços Concluídos x Pendentes**")
                    df_status = df_ind['realizado'].map({True: 'Concluído', False: 'Pendente'}).value_counts()
                    st.bar_chart(df_status, color="#28a745")
