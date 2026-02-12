import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime, time, timedelta
from io import BytesIO
from fpdf import FPDF
import time as time_module # Importado para evitar conflito com datetime.time

# --- CONFIGURAÇÕES DE MARCA ---
NOME_SISTEMA = "Up 2 Today"
SLOGAN = "Seu Controle. Nossa Prioridade."
LOGO_URL = "https://i.postimg.cc/85HwzdmP/logo-png.png"
ORDEM_AREAS = ["Motorista", "Borracharia", "Mecânica", "Elétrica", "Chapeamento", "Limpeza"]
LISTA_TURNOS = ["Não definido", "Dia", "Noite"]

# PALETA DE CORES EXTRAÍDA FIELMENTE DO LOGOTIPO U2T
COR_AZUL = "#1b224c"  # Azul Marinho Profundo do 'U'
COR_VERDE = "#31ad64" # Verde Esmeralda do '2T'
COR_FUNDO = "#f4f7f6"

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title=f"{NOME_SISTEMA} - Tudo em Dia", layout="wide", page_icon="🛠️")

# --- CSS FINAL: SIDEBAR CINZA #DFDFDF E CORREÇÃO DE ERRO ---
st.markdown(f"""
    <style>
    /* 1. FUNDOS: App Branco e Sidebar Cinza #DFDFDF */
    html, body, [data-testid="stAppViewContainer"], .stApp {{ background-color: #FFFFFF !important; }}
    [data-testid="stSidebar"] {{ background-color: #DFDFDF !important; }}

    /* 2. TEXTOS: Garante legibilidade em cinza escuro */
    p, label, span, div, .stMarkdown, [data-testid="stText"] {{
        color: #31333F !important;
    }}

    /* 3. CENTRALIZAÇÃO DOS BOTÕES DE LOGIN/CADASTRO */
    div[data-testid="stRadio"] > div {{
        display: flex;
        justify-content: center;
        background-color: #ffffff;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }}

    /* 4. BOTÕES: Fundo Azul Marinho e Letras Brancas */
    button[kind="primary"], button[kind="secondary"], button {{
        background-color: #1b224c !important;
        border: 2px solid #31ad64 !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }}

    /* Texto branco absoluto dentro dos botões */
    button p, button span, button div {{
        color: #FFFFFF !important;
    }}

    /* 5. ÍCONES BRANCOS: Olhinho da senha e ícone do calendário */
    button svg, [data-testid="stDateInput"] svg {{
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }}

    /* 6. CALENDÁRIO: FUNDO VERDE PARA VISIBILIDADE DOS NÚMEROS */
    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [class*="Selected"],
    div[data-baseweb="calendar"] [class*="Highlighted"] {{
        background-color: #31ad64 !important;
        background: #31ad64 !important;
    }}

    /* 7. LOGOTIPO: Cores da Marca */
    .logo-u {{ color: #1b224c !important; }}
    .logo-2t {{ color: #31ad64 !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE E BANCO ---
@st.cache_resource
def get_engine():
    # Prioriza o segredo configurado no painel do Streamlit
    db_url = st.secrets.get("database_url") or os.environ.get("database_url", "postgresql://neondb_owner:npg_WRMhXvJVY79d@ep-lucky-sound-acy7xdyi-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require")
    return create_engine(db_url.replace("postgres://", "postgresql://", 1), pool_pre_ping=True)

def inicializar_banco():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS tarefas (id SERIAL PRIMARY KEY, data TEXT, executor TEXT, prefixo TEXT, inicio_disp TEXT, fim_disp TEXT, descricao TEXT, area TEXT, turno TEXT, realizado BOOLEAN DEFAULT FALSE, id_chamado INTEGER, origem TEXT, empresa_id TEXT)"))
            conn.execute(text("CREATE TABLE IF NOT EXISTS chamados (id SERIAL PRIMARY KEY, motorista TEXT, prefixo TEXT, descricao TEXT, data_solicitacao TEXT, status TEXT DEFAULT 'Pendente', empresa_id TEXT)"))
            # NOVA TABELA DE EMPRESAS PARA SAAS
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS empresa (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    data_cadastro DATE DEFAULT CURRENT_DATE,
                    status_assinatura TEXT DEFAULT 'trial',
                    data_expiracao DATE DEFAULT (CURRENT_DATE + INTERVAL '7 days')
                )
            """))
            # NOVA TABELA DE USUÁRIOS (MOTORISTAS/EQUIPE)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    login TEXT NOT NULL,
                    senha TEXT NOT NULL,
                    perfil TEXT DEFAULT 'motorista',
                    empresa_id TEXT NOT NULL,
                    UNIQUE(login, empresa_id)
                )
            """))
            try: conn.execute(text("ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS empresa_id TEXT DEFAULT 'U2T_MATRIZ'"))
            except: pass
            try: conn.execute(text("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS empresa_id TEXT DEFAULT 'U2T_MATRIZ'"))
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
    
    # --- CABEÇALHO COM MARCA U2T (AJUSTADO: LETRAS PRÓXIMAS) ---
    pdf.set_font("Arial", "B", 22)
    pdf.set_text_color(27, 34, 76) # Azul Logo
    pdf.cell(6, 10, "U", ln=0)     # Célula estreita para aproximar
    pdf.set_text_color(49, 173, 100) # Verde Logo
    pdf.cell(40, 10, "2T", ln=0)
    
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(144, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1, align="R")
    
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(27, 34, 76)
    pdf.cell(190, 10, f"RELATORIO DE MANUTENCAO - {NOME_SISTEMA.upper()}", ln=True, align="C")
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 8, f"Periodo: {data_inicio.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(5)
    
    for d_process in sorted(df_periodo['data'].unique(), reverse=True):
        d_formatada = pd.to_datetime(d_process).strftime('%d/%m/%Y')
        pdf.set_font("Arial", "B", 11); pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 8, f" DATA: {d_formatada}", ln=True, fill=True)
        
        for area in ORDEM_AREAS:
            df_area = df_periodo[(df_periodo['data'] == d_process) & (df_periodo['area'] == area)]
            if not df_area.empty:
                pdf.set_font("Arial", "B", 9); pdf.set_text_color(49, 173, 100)
                pdf.cell(190, 7, f" Setor: {area}", ln=True)
                
                # Títulos da Tabela (Restaurado para Cinza)
                pdf.set_font("Arial", "B", 8); pdf.set_text_color(50); pdf.set_fill_color(230, 230, 230)
                pdf.cell(20, 6, "Prefixo", 1, 0, 'C', True)
                pdf.cell(35, 6, "Executor", 1, 0, 'C', True)
                pdf.cell(40, 6, "Disponibilidade", 1, 0, 'C', True)
                pdf.cell(95, 6, "Descricao", 1, 1, 'C', True)
                
                # Linhas da Tabela
                pdf.set_font("Arial", "", 7); pdf.set_text_color(0)
                for _, row in df_area.iterrows():
                    pdf.cell(20, 6, str(row['prefixo']), 1, 0, 'C')
                    pdf.cell(35, 6, str(row['executor'])[:20], 1, 0, 'C')
                    pdf.cell(40, 6, f"{row['inicio_disp']} - {row['fim_disp']}", 1, 0, 'C')
                    pdf.cell(95, 6, str(row['descricao'])[:75], 1, 1, 'L')
                pdf.ln(2)
                
    return pdf.output(dest='S').encode('latin-1')

# --- 3. LÓGICA DE LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False
if "aba_login" not in st.session_state: st.session_state["aba_login"] = "Acessar"

if not st.session_state["logado"]:
    _, col_login, _ = st.columns([1.2, 1, 1.2])
    with col_login:
        placeholder_topo = st.empty()
        # Logotipo centralizado com cores travadas
        placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span class='logo-u'>U</span><span class='logo-2t'>2T</span></h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-style: italic; color: #555; margin-top: 0;'>{SLOGAN}</p>", unsafe_allow_html=True)
        
        # ALTERNÂNCIA ENTRE LOGIN E CADASTRO (Centralizado pelo CSS acima)
        aba = st.radio("Selecione uma opção", ["Acessar", "Criar Conta"], horizontal=True, label_visibility="collapsed")
        
        if aba == "Acessar":
            with st.container(border=True):
                user_input = st.text_input("E-mail ou Usuário", key="u_log").lower()
                pw_input = st.text_input("Senha", type="password", key="p_log")
                if st.button(f"Acessar Painel {NOME_SISTEMA}", use_container_width=True, type="primary"):
                    engine = get_engine()
                    inicializar_banco()
                    
                    # 1. VERIFICAÇÃO DE USUÁRIOS MASTER (ESTÁTICOS)
                    masters = {
                        "bruno": {"pw": "master789", "perfil": "admin", "empresa": "U2T_MATRIZ", "login_original": "bruno"},
                        "motorista": {"pw": "12345", "perfil": "motorista", "empresa": "U2T_MATRIZ", "login_original": "motorista_padrao"}
                    }
                    
                    logado_agora = False
                    if user_input in masters and masters[user_input]["pw"] == pw_input:
                        st.session_state.update({"logado": True, "perfil": masters[user_input]["perfil"], "empresa": masters[user_input]["empresa"], "usuario_ativo": masters[user_input]["login_original"]})
                        logado_agora = True
                    else:
                        # 2. VERIFICAÇÃO NO BANCO DE DADOS (CLIENTES SAAS - AGORA ACEITA E-MAIL OU NOME)
                        with engine.connect() as conn:
                            res = conn.execute(text("""
                                SELECT nome, email, senha, data_expiracao, status_assinatura 
                                FROM empresa 
                                WHERE LOWER(email) = :u OR LOWER(nome) = :u
                            """), {"u": user_input}).fetchone()
                            
                            if res and res[2] == pw_input:
                                hoje = datetime.now().date()
                                # TRAVA DE SEGURANÇA: DATA DE EXPIRAÇÃO
                                if res[3] < hoje and res[4] != 'ativo':
                                    st.error(f"⚠️ O período de teste da empresa '{res[0]}' expirou em {res[3].strftime('%d/%m/%Y')}. Entre em contato para ativar.")
                                else:
                                    st.session_state.update({"logado": True, "perfil": "admin", "empresa": res[0], "usuario_ativo": res[0]})
                                    logado_agora = True
                            else:
                                # 3. VERIFICAÇÃO DE USUÁRIOS DA EQUIPE (MOTORISTAS OU OUTROS ADMINS SECUNDÁRIOS)
                                u_equipe = conn.execute(text("""
                                    SELECT login, senha, perfil, empresa_id FROM usuarios WHERE LOWER(login) = :u
                                """), {"u": user_input}).fetchone()
                                if u_equipe and u_equipe[1] == pw_input:
                                    st.session_state.update({"logado": True, "perfil": u_equipe[2], "empresa": u_equipe[3], "usuario_ativo": u_equipe[0]})
                                    logado_agora = True
                    
                    if logado_agora:
                        if "opcao_selecionada" in st.session_state: del st.session_state["opcao_selecionada"]
                        with st.spinner(""):
                            for t in ["UP", "UP 2", "UP 2 T", "UP 2 TOD", "UP 2 TODAY"]:
                                placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span class='logo-u'>{t[:2]}</span><span class='logo-2t'>{t[2:]}</span></h1>", unsafe_allow_html=True)
                                time_module.sleep(0.05)
                        st.rerun()
                    else:
                        if not st.session_state.get("error_shown"): st.error("Dados incorretos ou conta inexistente.")

        else: # ABA CRIAR CONTA
            with st.container(border=True):
                st.markdown(f"<h4 style='color:{COR_AZUL}'>🚀 7 Dias Grátis</h4>", unsafe_allow_html=True)
                n_emp = st.text_input("Nome da Empresa")
                n_ema = st.text_input("E-mail Corporativo")
                n_sen = st.text_input("Senha", type="password")
                if st.button("Criar minha conta agora", use_container_width=True, type="primary"):
                    if n_emp and n_ema and n_sen:
                        try:
                            engine = get_engine()
                            inicializar_banco()
                            expira = datetime.now().date() + timedelta(days=7)
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO empresa (nome, email, senha, data_expiracao) VALUES (:n, :e, :s, :d)"), {"n": n_emp, "e": n_ema, "s": n_sen, "d": expira})
                                conn.commit()
                            st.success("✅ Conta criada! Agora faça login na aba 'Acessar'.")
                        except Exception as e:
                            st.error("Este e-mail já está cadastrado.")
                    else: st.warning("Preencha todos os campos.")

else:
    engine = get_engine(); inicializar_banco()
    emp_id = st.session_state["empresa"] # Filtro global
    
    if st.session_state["perfil"] == "motorista":
        opcoes = ["✍️ Abrir Solicitação", "📜 Status"]
    else:
        opcoes = ["📅 Agenda Principal", "📋 Cadastro Direto", "📥 Chamados Oficina", "📊 Indicadores", "👥 Minha Equipe"]

    if "opcao_selecionada" not in st.session_state or st.session_state.opcao_selecionada not in opcoes:
        st.session_state.opcao_selecionada = opcoes[0]
    
    if "radio_key" not in st.session_state:
        st.session_state.radio_key = 0

    def set_nav(target):
        st.session_state.opcao_selecionada = target
        st.session_state.radio_key += 1 

    # 1. BARRA LATERAL
    with st.sidebar:
        # LOGO DIMINUÍDO NA SIDEBAR
        _, col_img, _ = st.columns([0.15, 0.7, 0.15])
        with col_img:
            st.image(LOGO_URL, width=150)
        st.markdown(f"<p style='text-align: center; font-size: 0.8rem; color: #666; margin-top: -10px;'>{SLOGAN}</p>", unsafe_allow_html=True)
        st.divider()
        
        try:
            idx_seguro = opcoes.index(st.session_state.opcao_selecionada)
        except ValueError:
            idx_seguro = 0; st.session_state.opcao_selecionada = opcoes[0]

        escolha_sidebar = st.radio(
            "NAVEGAÇÃO", 
            opcoes, 
            index=idx_seguro,
            key=f"radio_nav_{st.session_state.radio_key}",
            on_change=lambda: st.session_state.update({"opcao_selecionada": st.session_state[f"radio_nav_{st.session_state.radio_key}"]})
        )
        
        st.divider()
        st.write(f"🏢 **Empresa:** {emp_id}")
        st.write(f"👤 **{st.session_state['perfil'].capitalize()}**")
        if st.button("Sair da Conta", type="primary"): 
            st.session_state["logado"] = False
            st.rerun()

    # 2. BOTÕES DE ABA NO TOPO
    cols = st.columns(len(opcoes))
    for i, nome in enumerate(opcoes):
        eh_ativo = nome == st.session_state.opcao_selecionada
        if cols[i].button(nome, key=f"btn_tab_{i}", use_container_width=True, 
                         type="primary" if eh_ativo else "secondary",
                         on_click=set_nav, args=(nome,)):
            pass

    st.divider()
    aba_ativa = st.session_state.opcao_selecionada

    # --- 3. CONTEÚDO DAS PÁGINAS ---
    if aba_ativa == "✍️ Abrir Solicitação":
        st.subheader("✍️ Nova Solicitação de Manutenção")
        st.info("💡 **Dica:** Informe o prefixo e detalhe o problema para que a oficina possa se programar.")
        with st.form("f_ch", clear_on_submit=True):
            p, d = st.text_input("Prefixo do Veículo"), st.text_area("Descrição do Problema")
            if st.form_submit_button("Enviar para Oficina"):
                if p and d:
                    nome_motorista = st.session_state.get("usuario_ativo", "Motorista")
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO chamados (motorista, prefixo, descricao, data_solicitacao, status, empresa_id) VALUES (:m, :p, :d, :dt, 'Pendente', :eid)"), {"m": nome_motorista, "p": p, "d": d, "dt": str(datetime.now().date()), "eid": emp_id})
                        conn.commit()
                        st.success("✅ Solicitação enviada com sucesso! Acompanhe o status na aba ao lado.")

    elif aba_ativa == "📜 Status":
        st.subheader("📜 Status dos Meus Veículos")
        st.info("Aqui você pode ver se o seu veículo já foi agendado ou concluído pela oficina.")
        df_status = pd.read_sql(text("SELECT prefixo, data_solicitacao as data, status, descricao FROM chamados WHERE empresa_id = :eid ORDER BY id DESC"), engine, params={"eid": emp_id})
        st.dataframe(df_status, use_container_width=True, hide_index=True)

    elif aba_ativa == "📅 Agenda Principal":
        st.subheader("📅 Agenda Principal")
        
        # --- PAINEL DE RESUMO RÁPIDO NO TOPO (COM PROTEÇÃO CONTRA ERROS) ---
        try:
            df_stats = pd.read_sql(text("SELECT data, realizado FROM tarefas WHERE empresa_id = :eid"), engine, params={"eid": emp_id})
            if not df_stats.empty:
                df_stats['data'] = pd.to_datetime(df_stats['data']).dt.date
                hoje_dt = datetime.now().date()
                df_hoje = df_stats[df_stats['data'] == hoje_dt]
                
                m1, m2, m3 = st.columns(3)
                with m1: st.metric("Agendados Hoje", len(df_hoje))
                with m2: st.metric("Concluídos", len(df_hoje[df_hoje['realizado'] == True]))
                with m3: st.metric("Pendentes", len(df_hoje[df_hoje['realizado'] == False]))
                st.divider()
        except:
            st.warning("⚠️ O banco de dados está iniciando. Aguarde alguns segundos.")
            st.stop()

        # INSTRUÇÃO INTUITIVA PARA LOGÍSTICA E PCM
        st.info("✍️ **Logística:** Clique nas colunas de **Início** ou **Fim** para preencher. **PCM:** Clique em **Área** ou **Executor** para definir. O salvamento é automático.")
        
        # 1. Carrega os dados
        df_a = pd.read_sql(text("SELECT * FROM tarefas WHERE empresa_id = :eid ORDER BY data DESC"), engine, params={"eid": emp_id})
        hoje_input, amanha = datetime.now().date(), datetime.now().date() + timedelta(days=1)
        
        # 2. LINHA DE FILTROS (Data, Área e Turno)
        c_per, c_area, c_turno = st.columns([0.4, 0.3, 0.3])
        with c_per: p_sel = st.date_input("Filtrar Período", [hoje_input, amanha], key="dt_filter")
        
        opcoes_area = ["Todas"] + ORDEM_AREAS
        opcoes_turno = ["Todos"] + LISTA_TURNOS
        
        with c_area: f_area = st.selectbox("Filtrar Área", opcoes_area)
        with c_turno: f_turno = st.selectbox("Filtrar Turno", opcoes_turno)
        
        c_pdf, c_xls, _ = st.columns([0.2, 0.2, 0.6])

        if not df_a.empty and len(p_sel) == 2:
            df_a['data'] = pd.to_datetime(df_a['data']).dt.date
            df_f = df_a[(df_a['data'] >= p_sel[0]) & (df_a['data'] <= p_sel[1])].copy()
            
            if f_area != "Todas": df_f = df_f[df_f['area'] == f_area]
            if f_turno != "Todos": df_f = df_f[df_f['turno'] == f_turno]
            
            ordem_turno_map = {"Não definido": 0, "Dia": 1, "Noite": 2}
            df_f['turno_idx'] = df_f['turno'].map(ordem_turno_map).fillna(0)
            
            with c_pdf: st.download_button("📥 PDF", gerar_pdf_periodo(df_f, p_sel[0], p_sel[1]), f"Relatorio_U2T_{p_sel[0]}.pdf")
            with c_xls: st.download_button("📊 Excel", to_excel_native(df_f), f"Relatorio_U2T_{p_sel[0]}.xlsx")
            
            for d in sorted(df_f['data'].unique(), reverse=True):
                st.markdown(f"#### 🗓️ {d.strftime('%d/%m/%Y')}")
                areas_para_exibir = ORDEM_AREAS if f_area == "Todas" else [f_area]
                for area in areas_para_exibir:
                    df_area_f = df_f[(df_f['data'] == d) & (df_f['area'] == area)].sort_values(by='turno_idx')
                    if not df_area_f.empty:
                        st.markdown(f"<p class='area-header'>📍 {area}</p>", unsafe_allow_html=True)
                        df_editor_base = df_area_f.set_index('id')
                        
                        edited_df = st.data_editor(
                            df_editor_base[['realizado', 'area', 'turno', 'prefixo', 'inicio_disp', 'fim_disp', 'executor', 'descricao', 'id_chamado']], 
                            column_config={
                                "realizado": st.column_config.CheckboxColumn("OK", width="small"),
                                "area": st.column_config.SelectboxColumn("Área", options=ORDEM_AREAS),
                                "turno": st.column_config.SelectboxColumn("Turno", options=LISTA_TURNOS),
                                "inicio_disp": st.column_config.TextColumn("Início (Preencher)"),
                                "fim_disp": st.column_config.TextColumn("Fim (Preencher)"),
                                "executor": st.column_config.TextColumn("Executor"),
                                "id_chamado": None
                            }, 
                            hide_index=False, use_container_width=True, key=f"ed_ted_{d}_{area}"
                        )

                        if not edited_df.equals(df_editor_base[['realizado', 'area', 'turno', 'prefixo', 'inicio_disp', 'fim_disp', 'executor', 'descricao', 'id_chamado']]):
                            with engine.connect() as conn:
                                for row_id, row in edited_df.iterrows():
                                    conn.execute(text("""
                                        UPDATE tarefas SET 
                                        realizado = :r, area = :ar, turno = :t, prefixo = :p, 
                                        inicio_disp = :i, fim_disp = :f, 
                                        executor = :ex, descricao = :ds 
                                        WHERE id = :id
                                    """), {
                                        "r": bool(row['realizado']), "ar": str(row['area']), "t": str(row['turno']), 
                                        "p": str(row['prefixo']), "i": str(row['inicio_disp']), 
                                        "f": str(row['fim_disp']), "ex": str(row['executor']), 
                                        "ds": str(row['descricao']), "id": int(row_id)
                                    })
                                    if row['realizado'] and pd.notnull(row['id_chamado']):
                                        try: conn.execute(text("UPDATE chamados SET status = 'Concluído' WHERE id = :ic"), {"ic": int(row['id_chamado'])})
                                        except: pass
                                conn.commit()
                                st.toast("Alteração salva!", icon="✅")
                                time_module.sleep(0.5); st.rerun()

    elif aba_ativa == "📋 Cadastro Direto":
        st.subheader("📝 Agendamento Direto")
        st.info("💡 **Atenção:** Use este formulário para serviços que não vieram de chamados.")
        st.warning("⚠️ **Nota:** Para reagendar ou corrigir, basta alterar diretamente na lista abaixo. O salvamento é automático.")
        with st.form("f_d", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: d_i = st.date_input("Data", datetime.now())
            with c2: e_i = st.text_input("Executor")
            with c3: p_i = st.text_input("Prefixo")
            with c4: a_i = st.selectbox("Área", ORDEM_AREAS)
            c5, c6 = st.columns(2)
            with c5: t_ini = st.text_input("Início (Ex: 08:00)", "00:00")
            with c6: t_fim = st.text_input("Fim (Ex: 10:00)", "00:00")
            ds_i, t_i = st.text_area("Descrição"), st.selectbox("Turno", LISTA_TURNOS)
            if st.form_submit_button("Confirmar Agendamento"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, origem, empresa_id) VALUES (:dt, :ex, :pr, :ti, :tf, :ds, :ar, :tu, 'Direto', :eid)"), {"dt": str(d_i), "ex": e_i, "pr": p_i, "ti": t_ini, "tf": t_fim, "ds": ds_i, "ar": a_i, "tu": t_i, "eid": emp_id})
                    conn.commit()
                    st.success("✅ Serviço cadastrado!"); st.rerun()
        st.divider(); st.subheader("📋 Lista de serviços")
        df_lista = pd.read_sql(text("SELECT * FROM tarefas WHERE empresa_id = :eid ORDER BY data DESC, id DESC"), engine, params={"eid": emp_id})
        if not df_lista.empty:
            df_lista['data'] = pd.to_datetime(df_lista['data']).dt.date
            df_lista['Exc'] = False
            ed_l = st.data_editor(df_lista[['Exc', 'data', 'turno', 'executor', 'prefixo', 'inicio_disp', 'fim_disp', 'descricao', 'area', 'id']], hide_index=True, use_container_width=True, key="ed_lista")
            if st.button("🗑️ Excluir Selecionados"):
                with engine.connect() as conn:
                    for i in ed_l[ed_l['Exc']==True]['id'].tolist(): conn.execute(text("DELETE FROM tarefas WHERE id = :id"), {"id": int(i)})
                    conn.commit(); st.warning("🗑️ Itens excluídos."); st.rerun()
            if st.session_state.ed_lista["edited_rows"]:
                with engine.connect() as conn:
                    for idx, changes in st.session_state.ed_lista["edited_rows"].items():
                        rid = int(df_lista.iloc[idx]['id'])
                        for col, val in changes.items():
                            if col != 'Exc': conn.execute(text(f"UPDATE tarefas SET {col} = :v WHERE id = :i"), {"v": str(val), "i": rid})
                    conn.commit(); st.rerun()

    elif aba_ativa == "📥 Chamados Oficina":
        c_tit, c_refresh = st.columns([0.8, 0.2])
        with c_tit: st.subheader("📥 Aprovação de Chamados")
        with c_refresh:
            if st.button("🔄 Atualizar Lista", use_container_width=True):
                if 'df_ap_work' in st.session_state: del st.session_state.df_ap_work
                st.rerun()
                
        st.info("💡 Preencha os campos e marque 'Aprovar' na última coluna para enviar à agenda.")
        df_p = pd.read_sql(text("SELECT id, data_solicitacao, motorista, prefixo, descricao FROM chamados WHERE status = 'Pendente' AND empresa_id = :eid ORDER BY id DESC"), engine, params={"eid": emp_id})
        if not df_p.empty:
            if 'df_ap_work' not in st.session_state:
                df_p['Executor'], df_p['Area_Destino'], df_p['Data_Programada'], df_p['Inicio'], df_p['Fim'], df_p['Aprovar'] = "", "Mecânica", datetime.now().date(), "00:00", "00:00", False
                st.session_state.df_ap_work = df_p
            ed_c = st.data_editor(st.session_state.df_ap_work, hide_index=True, use_container_width=True, column_config={"data_solicitacao": "Aberto em", "motorista": "Solicitante", "Data_Programada": st.column_config.DateColumn("Data Programada"), "Area_Destino": st.column_config.SelectboxColumn("Área", options=ORDEM_AREAS), "Aprovar": st.column_config.CheckboxColumn("Aprovar?"), "id": None}, key="editor_chamados")
            if st.button("Processar Agendamentos", type="primary"):
                selecionados = ed_c[ed_c['Aprovar'] == True]
                if not selecionados.empty:
                    with engine.connect() as conn:
                        for _, r in selecionados.iterrows():
                            conn.execute(text("INSERT INTO tarefas (data, executor, prefixo, inicio_disp, fim_disp, descricao, area, turno, id_chamado, origem, empresa_id) VALUES (:dt, :ex, :pr, :ti, :tf, :ds, :ar, 'Não definido', :ic, 'Chamado', :eid)"), {"dt": str(r['Data_Programada']), "ex": r['Executor'], "pr": r['prefixo'], "ti": r['Inicio'], "tf": r['Fim'], "ds": r['descricao'], "ar": r['Area_Destino'], "ic": r['id'], "eid": emp_id})
                            conn.execute(text("UPDATE chamados SET status = 'Agendado' WHERE id = :id"), {"id": r['id']})
                        conn.commit()
                    st.success("✅ Agendamentos processados!"); del st.session_state.df_ap_work; st.rerun()
        else: st.info("Nenhum chamado pendente no momento.")

    elif aba_ativa == "📊 Indicadores":
        st.subheader("📊 Painel de Performance Operacional")
        st.info("💡 **Dica:** Utilize esses dados para identificar gargalos e planejar a capacidade da oficina.")
        c1, c2 = st.columns(2)
        df_ind = pd.read_sql(text("SELECT area, realizado FROM tarefas WHERE empresa_id = :eid"), engine, params={"eid": emp_id})
        with c1:
            st.markdown("**Serviços por Área**"); st.bar_chart(df_ind['area'].value_counts(), color=COR_VERDE) 
        with c2: 
            if not df_ind.empty:
                df_st = df_ind['realizado'].map({True: 'Concluído', False: 'Pendente'}).value_counts()
                st.markdown("**Status de Conclusão**"); st.bar_chart(df_st, color=COR_AZUL) 
        st.divider(); st.markdown("**⏳ Tempo de Resposta (Lead Time)**")
        query_lead = text("SELECT c.data_solicitacao, t.data as data_conclusao FROM chamados c JOIN tarefas t ON c.id = t.id_chamado WHERE t.realizado = True AND t.empresa_id = :eid")
        df_lead = pd.read_sql(query_lead, engine, params={"eid": emp_id})
        if not df_lead.empty:
            df_lead['data_solicitacao'], df_lead['data_conclusao'] = pd.to_datetime(df_lead['data_solicitacao']), pd.to_datetime(df_lead['data_conclusao'])
            df_lead['dias'] = (df_lead['data_conclusao'] - df_lead['data_solicitacao']).dt.days.apply(lambda x: max(x, 0))
            col_m1, col_m2 = st.columns([0.3, 0.7])
            with col_m1: st.metric("Lead Time Médio", f"{df_lead['dias'].mean():.1f} Dias")
            with col_m2:
                df_ev = df_lead.groupby('data_conclusao')['dias'].mean().reset_index()
                st.line_chart(df_ev.set_index('data_conclusao'), color=COR_VERDE)

    elif aba_ativa == "👥 Minha Equipe":
        st.subheader("👥 Gestão de Equipe e Acessos")
        st.info("💡 **Dica profissional:** Para editar senhas ou cargos, altere diretamente na tabela. Para excluir, marque 'Exc' e clique no botão abaixo.")
        
        with st.expander("➕ Cadastrar Novo Integrante", expanded=True):
            with st.form("form_novo_usuario", clear_on_submit=True):
                col1, col2, col3 = st.columns([1, 1, 1]) 
                novo_u = col1.text_input("Login (Ex: pedro.motorista)")
                nova_s = col2.text_input("Senha de Acesso", type="password")
                novo_p = col3.selectbox("Cargo/Perfil", ["motorista", "admin"]) # Campo de seleção de cargo
                if st.form_submit_button("Criar Acesso"):
                    if novo_u and nova_s:
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO usuarios (login, senha, perfil, empresa_id) VALUES (:u, :s, :p, :eid)"), 
                                             {"u": novo_u.lower(), "s": nova_s, "p": novo_p, "eid": emp_id})
                                conn.commit()
                            st.success(f"✅ Acesso para '{novo_u}' ({novo_p}) criado com sucesso!")
                            time_module.sleep(1.5); st.rerun()
                        except: st.error("Erro: Este login já existe ou houve um problema com o banco.")
                    else: st.warning("Preencha todos os campos.")

        st.divider(); st.subheader("Integrantes Cadastrados")
        df_users = pd.read_sql(text("SELECT id, login, senha, perfil as cargo FROM usuarios WHERE empresa_id = :eid"), engine, params={"eid": emp_id})
        if not df_users.empty:
            df_users['Exc'] = False
            ed_users = st.data_editor(df_users[['Exc', 'login', 'senha', 'cargo', 'id']], hide_index=True, use_container_width=True, column_config={"id": None, "Exc": st.column_config.CheckboxColumn("Excluir", width="small"), "senha": st.column_config.TextColumn("Senha"), "cargo": st.column_config.SelectboxColumn("Cargo", options=["motorista", "admin"])}, key="editor_equipe")
            if st.button("🗑️ Excluir Selecionados da Equipe"):
                usuarios_para_deletar = ed_users[ed_users['Exc'] == True]['id'].tolist()
                if usuarios_para_deletar:
                    with engine.connect() as conn:
                        for u_id in usuarios_para_deletar: conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": int(u_id)})
                        conn.commit()
                    st.warning("Integrantes removidos."); time_module.sleep(1); st.rerun()
            if st.session_state.editor_equipe["edited_rows"]:
                with engine.connect() as conn:
                    for idx, changes in st.session_state.editor_equipe["edited_rows"].items():
                        user_db_id = int(df_users.iloc[idx]['id'])
                        for col, val in changes.items():
                            if col != 'Exc': conn.execute(text(f"UPDATE usuarios SET {col} = :v WHERE id = :i"), {"v": str(val), "i": user_db_id})
                    conn.commit(); st.toast("Dados da equipe atualizados!", icon="👥")
        else: st.write("Nenhum integrante cadastrado ainda.")
