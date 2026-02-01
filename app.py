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
# Link direto funcional para a imagem (apenas após login)
LOGO_URL = "https://i.postimg.cc/wTbmmT7r/logo-png.png" 
ORDEM_AREAS = ["Motorista", "Borracharia", "Mecânica", "Elétrica", "Chapeamento", "Limpeza"]
LISTA_TURNOS = ["Não definido", "Dia", "Noite"]

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title=f"{NOME_SISTEMA} - Tudo em Dia", layout="wide", page_icon="🛠️")

# --- AJUSTE DE PALETA (Cores extraídas do Logo) ---
COR_AZUL = "#3282b8"
COR_VERDE = "#8ac926"

# --- CSS PARA UNIDADE VISUAL ATUALIZADO ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fa; }}
    /* Botões com o azul do logo */
    .stButton>button {{ background-color: {COR_AZUL}; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%; }}
    .stButton>button:hover {{ background-color: #276691; color: white; border: none; }}
    
    [data-testid="stSidebar"] {{ background-color: #ffffff; border-right: 1px solid #e0e0e0; }}
    
    /* Cabeçalhos das áreas com o verde do logo */
    .area-header {{ 
        color: {COR_VERDE}; 
        font-weight: bold; 
        font-size: 1.1rem; 
        border-left: 5px solid {COR_AZUL}; 
        padding-left: 10px; 
        margin-top: 20px; 
    }}
    
    div[data-testid="stRadio"] > div {{ background-color: #f1f3f5; padding: 10px; border-radius: 10px; }}
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
    for d_process in sorted(df_periodo['data'].unique(), reverse=True):
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
        placeholder_topo = st.empty()
        
        # ESTADO INICIAL: Ted (T azul, ed verde)
        placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span style='color: #0066cc;'>T</span><span style='color: #28a745;'>ed</span></h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-style: italic; color: #555; margin-top: 0;'>{SLOGAN}</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            user = st.text_input("Usuário", key="u_log").lower()
            pw = st.text_input("Senha", type="password", key="p_log")
            
            if st.button("Acessar Painel Ted", use_container_width=True):
                users = {"bruno": "master789", "admin": "12345", "motorista": "12345"}
                
                if user in users and users[user] == pw:
                    import time
                    with st.spinner(""):
                        # ANIMAÇÃO DE EXPANSÃO (T -> Tudo | e -> em | d -> dia)
                        # Passo 1: T -> Tudo (Azul)
                        placeholder_topo.markdown("<h1 style='text-align: center; margin-bottom: 0;'><span style='color: #0066cc;'>Tu</span><span style='color: #28a745;'>ed</span></h1>", unsafe_allow_html=True)
                        time.sleep(0.1)
                        placeholder_topo.markdown("<h1 style='text-align: center; margin-bottom: 0;'><span style='color: #0066cc;'>Tud</span><span style='color: #28a745;'>ed</span></h1>", unsafe_allow_html=True)
                        time.sleep(0.1)
                        placeholder_topo.markdown("<h1 style='text-align: center; margin-bottom: 0;'><span style='color: #0066cc;'>Tudo</span> <span style='color: #28a745;'>ed</span></h1>", unsafe_allow_html=True)
                        time.sleep(0.3)
                        
                        # Passo 2: e -> em | d -> dia (Verde)
                        placeholder_topo.markdown("<h1 style='text-align: center; margin-bottom: 0;'><span style='color: #0066cc;'>Tudo</span> <span style='color: #28a745;'>em d</span></h1>", unsafe_allow_html=True)
                        time.sleep(0.1)
                        placeholder_topo.markdown("<h1 style='text-align: center; margin-bottom: 0;'><span style='color: #0066cc;'>Tudo</span> <span style='color: #28a745;'>em di</span></h1>", unsafe_allow_html=True)
                        time.sleep(0.1)
                        placeholder_topo.markdown("<h1 style='text-align: center; margin-bottom: 0;'><span style='color: #0066cc;'>Tudo</span> <span style='color: #28a745;'>em dia</span></h1>", unsafe_allow_html=True)
                        time.sleep(1.0)
                        
                    st.session_state["logado"], st.session_state["perfil"] = True, ("admin" if user != "motorista" else "motorista")
                    st.rerun()
                else: 
                    st.error("Usuário ou senha incorretos")
else:
    engine = get_engine()
    inicializar_banco()
    
    with st.sidebar:
        st.image(LOGO_URL, use_container_width=True)
        st.markdown(f"<p style='text-align: center; font-size: 0.8rem; color: #666; margin-top: -10px;'>{SLOGAN}</p>", unsafe_allow_html=True)
        st.divider()
        
        if st.session_state["perfil"] == "motorista":
            opcoes = ["✍️ Abrir Solicitação", "📜 Status"]
        else:
            opcoes = ["📅 Agenda Principal", "📋 Cadastro Direto", "📥 Chamados Oficina", "📊 Indicadores"]
        
        escolha = st.radio("NAVEGAÇÃO", opcoes)
        
        st.divider()
        st.write(f"👤 **{st.session_state['perfil'].capitalize()}**")
        if st.button("Sair da Conta"):
            st.session_state["logado"] = False; st.rerun()

    # --- PÁGINAS ---
    if escolha == "✍️ Abrir Solicitação":
        st.subheader("✍️ Nova Solicitação")
        with st.form("f_ch", clear_on_submit=True):
            p, d = st.text_input("Prefixo"), st.text_area("Descrição")
            if st.form_submit_button("Enviar para Oficina"):
                if p and d:
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO chamados (motorista, prefixo, descricao, data_solicitacao, status) VALUES ('motorista', :p, :d, :dt, 'Pendente')"), {"p": p, "d": d, "dt": str(datetime.now().date())})
                        conn.commit()
                    st.success("Solicitação enviada!")

    elif escolha == "📜 Status":
        st.subheader("📜 Status dos Veículos")
        st.dataframe(pd.read_sql("SELECT prefixo, data_solicitacao as data, status, descricao FROM chamados ORDER BY id DESC", engine), use_container_width=True)

    elif escolha == "📋 Cadastro Direto":
        st.subheader("📝 Agendamento Direto")
        st.info("💡 *Para reagendar serviços, basta alterar as datas na lista abaixo. Faça demais ajustes ou exclua serviços em caso de agendamentos incorretos. O salvamento é automático.*")
        with st.form("f_d", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: d_i = st.date_input("Data", datetime.now())
            with c2: e_i = st.text_input("Executor")
            with c3: p_i = st.text_input("Prefixo")
            with c4: a_i = st.selectbox("Área", ORDEM_AREAS)
            ds_i, t_i = st.text_area("Descrição"), st.selectbox("Turno", LISTA_TURNOS)
            if st.form_submit_button("Confirmar Agendamento"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, origem) VALUES (:dt, :ex, :pr, '00:00', '00:00', :ds, :ar, :tu, 'Direto')"), {"dt": str(d_i), "ex": e_i, "pr": p_i, "ds": ds_i, "ar": a_i, "tu": t_i})
                    conn.commit()
                st.rerun()
        st.divider()
        st.subheader("📋 Lista de serviços")
        df_lista = pd.read_sql("SELECT * FROM tarefas ORDER BY data DESC, id DESC", engine)
        if not df_lista.empty:
            df_lista['data'] = pd.to_datetime(df_lista['data']).dt.date
            df_lista['Exc'] = False
            ed_l = st.data_editor(df_lista[['Exc', 'data', 'turno', 'executor', 'prefixo', 'descricao', 'area', 'id']], hide_index=True, use_container_width=True, key="ed_lista")
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
                    conn.commit(); st.rerun()

    elif escolha == "📥 Chamados Oficina":
        st.subheader("📥 Aprovação de Chamados")
        df_p = pd.read_sql("SELECT * FROM chamados WHERE status != 'Agendado' AND status != 'Concluído'", engine)
        if not df_p.empty:
            if 'df_aprov' not in st.session_state:
                st.session_state.df_aprov = df_p.copy()
                st.session_state.df_aprov['Responsável'] = "Pendente"; st.session_state.df_aprov['Data'] = datetime.now().date(); st.session_state.df_aprov['OK'] = False
            ed_c = st.data_editor(st.session_state.df_aprov, hide_index=True, use_container_width=True, column_config={"id": None, "motorista": None, "status": None, "OK": st.column_config.CheckboxColumn("Aprovar?"), "Responsável": st.column_config.TextColumn("Executor"), "Área": st.column_config.SelectboxColumn("Área", options=ORDEM_AREAS)}, key="editor_chamados")
            if st.button("Processar Agendamentos"):
                selecionados = ed_c[ed_c['OK'] == True]
                with engine.connect() as conn:
                    for _, r in selecionados.iterrows():
                        conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, id_chamado, origem) VALUES (:dt, :ex, :pr, '00:00', '00:00', :ds, :ar, 'Não definido', :ic, 'Chamado')"), {"dt": str(r['Data']), "ex": r['Responsável'], "pr": r['prefixo'], "ds": r['descricao'], "ar": r['Área'], "ic": r['id']})
                        conn.execute(text("UPDATE chamados SET status = 'Agendado' WHERE id = :id"), {"id": r['id']})
                    conn.commit()
                del st.session_state.df_aprov; st.rerun()
        else: st.info("Nenhum chamado pendente.")

    elif escolha == "📅 Agenda Principal":
        st.subheader("📅 Agenda Principal")
        df_a = pd.read_sql("SELECT * FROM tarefas ORDER BY data DESC", engine)
        hoje, amanha = datetime.now().date(), datetime.now().date() + timedelta(days=1)
        c_per, c_pdf = st.columns([0.8, 0.2])
        with c_per: p_sel = st.date_input("Filtrar Período", [hoje, amanha], key="dt_filter")
        if not df_a.empty:
            df_a['data'] = pd.to_datetime(df_a['data']).dt.date
            df_f = df_a[(df_a['data'] >= p_sel[0]) & (df_a['data'] <= p_sel[1])] if len(p_sel) == 2 else df_a
            with c_pdf: st.download_button("📥 PDF", gerar_pdf_periodo(df_f, p_sel[0], p_sel[1]), "Relatorio_Ted.pdf")
            with st.form("form_agenda"):
                btn_salvar = st.form_submit_button("Salvar Alterações", use_container_width=True)
                for d in sorted(df_f['data'].unique(), reverse=True):
                    st.markdown(f"#### 🗓️ {d.strftime('%d/%m/%Y')}")
                    for area in ORDEM_AREAS:
                        df_area_f = df_f[(df_f['data'] == d) & (df_f['area'] == area)]
                        if not df_area_f.empty:
                            st.markdown(f"<p class='area-header'>📍 {area}</p>", unsafe_allow_html=True)
                            st.data_editor(df_area_f[['realizado', 'executor', 'prefixo', 'inicio_disp', 'fim_disp', 'turno', 'descricao', 'id', 'id_chamado']], column_config={"id": None, "id_chamado": None, "realizado": st.column_config.CheckboxColumn("OK"), "inicio_disp": st.column_config.TextColumn("Início"), "fim_disp": st.column_config.TextColumn("Fim")}, hide_index=True, use_container_width=True, key=f"ed_ted_{d}_{area}")
                if btn_salvar:
                    with engine.connect() as conn:
                        for key in st.session_state.keys():
                            if key.startswith("ed_ted_") and st.session_state[key]["edited_rows"]:
                                partes = key.split("_")
                                dt_k, ar_k = datetime.strptime(partes[2], '%Y-%m-%d').date(), partes[3]
                                df_ref = df_f[(df_f['data'] == dt_k) & (df_f['area'] == ar_k)]
                                for idx, changes in st.session_state[key]["edited_rows"].items():
                                    row = df_ref.iloc[idx]
                                    rid, id_ch = int(row['id']), row['id_chamado']
                                    for col, val in changes.items():
                                        conn.execute(text(f"UPDATE tarefas SET {col} = :v WHERE id = :i"), {"v": str(val), "i": rid})
                                        if col == 'realizado' and val is True and id_ch:
                                            conn.execute(text("UPDATE chamados SET status = 'Concluído' WHERE id = :ic"), {"ic": int(id_ch)})
                    conn.commit(); st.rerun()
    # --- FUNÇÃO PARA CONVERTER DATAFRAME PARA EXCEL (EM MEMÓRIA) ---
def to_excel(df):
    output = BytesIO()
    # Usamos o formatador do pandas para CSV por ser mais leve e universal
    # Se preferir .xlsx, o processo é similar com o xlsxwriter
    return df.to_csv(index=False).encode('utf-8-sig')

# --- NO LOCAL DOS BOTÕES DE DOWNLOAD ---
c_per, c_pdf, c_xls = st.columns([0.6, 0.2, 0.2])

with c_per: 
    p_sel = st.date_input("Filtrar Período", [hoje, amanha], key="dt_filter")

if not df_a_carrega.empty:
    # ... (lógica de filtro que já existe no seu código) ...
    
    with c_pdf:
        st.download_button("📥 PDF", gerar_pdf_periodo(df_f_per, p_sel[0], p_sel[1]), "Relatorio_Ted.pdf")
        
    with c_xls:
        # BOTÃO RESTAURADO
        st.download_button(
            label="📊 Excel",
            data=to_excel(df_f_per),
            file_name=f"Relatorio_Manutencao_{p_sel[0]}.csv",
            mime="text/csv")

    elif escolha == "📊 Indicadores":
        st.subheader("📊 Indicadores")
        df_ind = pd.read_sql("SELECT area, realizado FROM tarefas", engine)
        if not df_ind.empty:
            c1, c2 = st.columns(2)
            with c1: st.bar_chart(df_ind['area'].value_counts(), color="#0066cc")
            with c2:
                df_status = df_ind['realizado'].map({True: 'Concluído', False: 'Pendente'}).value_counts()
                st.bar_chart(df_status, color="#28a745")
